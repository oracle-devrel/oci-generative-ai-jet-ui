"""Oracle memory examples: scoped retrieval, context selection, and promotion.

The schema uses typed, scoped memory. All fixtures are synthetic. No generative model
or refund action is invoked: the output is an evidence package and memory rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import time
import urllib.request
import uuid

from dotenv import load_dotenv
import oracledb
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

oracledb.defaults.program = "devrel-developerhub-using-jev-and-oracle-ai-database-to-govern-agent-memory"

ROOT = Path(__file__).resolve().parent
oracledb.defaults.fetch_lobs = False
PROGRAM_IDENTIFIER = 'devrel-developerhub-using-jev-and-oracle-ai-database-to-govern-agent-memory'
POLICY_VERSION = 'memory-demo-v1'
QUESTION_VERSION = 'jev-memory-v1'
INPUT_PRICE_PER_MILLION = 0.042  # Estimate using the published rate; not an invoice.
# Oracle's augmented all-MiniLM-L12-v2: tokenization is inside the ONNX graph, so
# VECTOR_EMBEDDING(model USING 'text' AS DATA) takes plain text and returns 384 dimensions.
EMBEDDING_MODEL = 'ALL_MINILM_L12_V2'
EMBEDDING_MODEL_URL = ('https://objectstorage.us-ashburn-1.oraclecloud.com'
                       '/n/adwc4pm/b/OML-Resources/o/all_MiniLM_L12_v2.onnx')
EMBEDDING_METADATA = {'function': 'embedding', 'embeddingOutput': 'embedding',
                      'input': {'input': ['DATA']}}
TABLES = ('JEV_GUIDELINE_MEMORY', 'JEV_PERSONA_MEMORY', 'JEV_ENTITY_MEMORY',
          'JEV_CONVERSATION_MEMORY', 'JEV_SUMMARIZATION_MEMORY', 'JEV_ASSESSMENT_MEMORY')
SCOPE = """
 (user_id IS NULL OR user_id = :user_id)
 AND (agent_id IS NULL OR agent_id = :agent_id)
 AND (thread_id IS NULL OR thread_id = :thread_id)
 AND deleted_at IS NULL AND valid_from <= SYS_EXTRACT_UTC(SYSTIMESTAMP)
 AND (valid_until IS NULL OR valid_until > SYS_EXTRACT_UTC(SYSTIMESTAMP))
"""


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def rows(cursor):
    names = [d[0].lower() for d in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def promotion_policy(answers):
    """Illustrative thresholds, deliberately separate from relevance/confidence."""
    try:
        values = [answers[k]['noul'] for k in ('supported','scope_fits','conflict')]
        if not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1 for v in values):
            return 'review_invalid_assessment'
    except (KeyError,TypeError):
        return 'review_invalid_assessment'
    if answers['supported']['noul'] < 0.90:
        return 'reject_unsupported'
    if answers['scope_fits']['noul'] < 0.90:
        return 'reject_scope'
    if answers['conflict']['noul'] > 0.10:
        return 'review_conflict'
    return 'promote'


def route_policy(answer):
    confidence=answer.get('confidence',0)
    if not isinstance(confidence,(int,float)) or not math.isfinite(confidence) or not 0.60<=confidence<=1:
        return 'clarify'
    allowed = {'prior_resolution', 'current_policy', 'clarify'}
    return answer['choice'] if answer['choice'] in allowed else 'clarify'


def select_context(candidates, answers, mandatory, budget_bytes=2200):
    """Exact UTF-8 byte budget; a model-specific tokenizer is deliberately omitted."""
    evidence = [dict(item, use='mandatory') for item in mandatory]
    used = sum(len(json.dumps(x, ensure_ascii=False).encode()) for x in evidence)
    if used > budget_bytes:
        raise ValueError('Mandatory evidence exceeds context budget; stop or escalate.')
    decisions = []
    seen = set()
    for candidate in sorted(candidates, key=lambda x: answers[f"{x['key']}_relevance"]['score'], reverse=True):
        key = candidate['key']
        kind = answers[f'{key}_use']
        relevance = answers[f'{key}_relevance']['score']
        decision = 'exclude'
        if kind['confidence'] >= 0.60 and kind['choice'] in {'applicable', 'history'} and relevance >= 1.0:
            item = {k: candidate[k] for k in ('id', 'version', 'source_event_id', 'content')}
            item['use'] = kind['choice']
            size = len(json.dumps(item, ensure_ascii=False).encode())
            content_hash = digest(candidate['content'])
            if content_hash in seen:
                decision = 'duplicate'
            elif used + size > budget_bytes:
                decision = 'budget_excluded'
            else:
                evidence.append(item)
                used += size
                seen.add(content_hash)
                decision = kind['choice']
        decisions.append({'id': candidate['id'], 'use': decision, 'relevance': relevance})
    return {'evidence': evidence, 'decisions': decisions, 'used_bytes': used, 'budget_bytes': budget_bytes}


@dataclass(frozen=True)
class Scope:
    tenant_id: str
    user_id: str = 'user:jane'
    agent_id: str = 'agent:support_v1'
    thread_id: str = 'thread:current'

    def binds(self):
        return {k: getattr(self, k) for k in ('user_id', 'agent_id', 'thread_id')}


class MemoryDemo:
    def __init__(self, *, user, password, dsn, program=PROGRAM_IDENTIFIER):
        # DB credentials come from the caller (the notebook reads DB_USER, DB_PASSWORD, and
        # DB_DSN from the repository .env); the TypeSafe settings come from the environment.
        if not os.getenv('TYPESAFE_API_KEY'):
            raise ValueError('Set TYPESAFE_API_KEY in the repository .env or the environment.')
        self.model = os.getenv('JEV_MODEL', 'jev-1.13.0')
        self.embedding_model = EMBEDDING_MODEL
        self.conn = oracledb.connect(user=user, password=password, dsn=dsn, program=program)
        self.conn.call_timeout = 30000
        self.cur = self.conn.cursor()
        self.cur.execute("ALTER SESSION SET TIME_ZONE = 'UTC'")
        self.client = TypeSafeClient(api_key=os.environ['TYPESAFE_API_KEY'], model=self.model, timeout=30)
        self.run_id = uuid.uuid4().hex[:12]
        self.scope = Scope('acme_' + self.run_id)
        self.globex = 'globex_' + self.run_id
        self.calls = []
        self.results = {'run_id': self.run_id, 'oracle_version': self.conn.version,
                        'requested_model': self.model, 'started_at': datetime.now(timezone.utc).isoformat()}

    def set_tenant(self, tenant):
        self.cur.callproc('set_jev_memory_ctx.set_tenant', [tenant])

    def close(self):
        self.client.close()
        self.conn.close()

    def ensure_embedding_model(self, name=EMBEDDING_MODEL, url=EMBEDDING_MODEL_URL):
        """Load the ONNX model into this schema unless it is already there.

        The BLOB overload of LOAD_ONNX_MODEL streams the file from the client, so no
        directory object or database-host filesystem access is needed; the user only
        needs CREATE MINING MODEL.
        """
        self.cur.execute('SELECT COUNT(*) FROM user_mining_models WHERE model_name = :m', m=name.upper())
        loaded = self.cur.fetchone()[0] == 1
        if not loaded:
            with urllib.request.urlopen(url, timeout=600) as response:
                model_bytes = response.read()
            # A ~130 MB upload can outlast the 30-second query timeout; lift it for this call only.
            timeout, self.conn.call_timeout = self.conn.call_timeout, 0
            try:
                blob = self.conn.createlob(oracledb.DB_TYPE_BLOB)
                blob.write(model_bytes)
                self.cur.execute('BEGIN DBMS_VECTOR.LOAD_ONNX_MODEL(:name, :data, JSON(:meta)); END;',
                                 name=name, data=blob, meta=json.dumps(EMBEDDING_METADATA))
            finally:
                self.conn.call_timeout = timeout
        self.cur.execute(f"SELECT VECTOR_DIMENSION_COUNT(VECTOR_EMBEDDING({name} USING 'refund policy' AS DATA)) FROM dual")
        dimensions = self.cur.fetchone()[0]
        if dimensions != 384:
            raise ValueError(f'{name} returned {dimensions} dimensions; the memory tables expect 384.')
        return {'model': name, 'status': 'already loaded' if loaded else f'loaded from {url}',
                'dimensions': dimensions}

    def setup(self):
        # Every object carries a jev_ prefix so this demo can share DB_USER's schema with the
        # other memory notebooks, which use set_memory_ctx, memory_ctx, and unprefixed tables.
        self.cur.execute('''CREATE OR REPLACE PACKAGE set_jev_memory_ctx AS
            PROCEDURE set_tenant(p_tenant_id VARCHAR2); END set_jev_memory_ctx;''')
        self.cur.execute('''CREATE OR REPLACE PACKAGE BODY set_jev_memory_ctx AS
            PROCEDURE set_tenant(p_tenant_id VARCHAR2) IS BEGIN
              DBMS_SESSION.SET_CONTEXT('jev_memory_ctx', 'tenant_id', p_tenant_id);
            END; END set_jev_memory_ctx;''')
        self.cur.execute('CREATE OR REPLACE CONTEXT jev_memory_ctx USING set_jev_memory_ctx')
        self.cur.execute('SELECT table_name FROM user_tables')
        existing = {r[0] for r in self.cur}
        schema = (ROOT / 'schema.sql').read_text()
        # The file has explicit separators; PL/SQL is never split on semicolons.
        schema = '\n'.join(line for line in schema.splitlines() if not line.startswith('-- Statement separator'))
        for statement in schema.split('-- @statement'):
            match = re.search(r'CREATE TABLE (\w+)', statement)
            if match and match[1].upper() not in existing:
                self.cur.execute(statement.strip())
        if 'JEV_ASSESSMENT_MEMORY' not in existing:
            self.cur.execute('''CREATE TABLE jev_assessment_memory (
                id VARCHAR2(64) PRIMARY KEY, tenant_id VARCHAR2(64) NOT NULL,
                user_id VARCHAR2(64), agent_id VARCHAR2(64), thread_id VARCHAR2(64),
                run_id VARCHAR2(64) NOT NULL, stage VARCHAR2(64) NOT NULL,
                policy_version VARCHAR2(64) NOT NULL, question_version VARCHAR2(64) NOT NULL,
                record_json JSON NOT NULL, created_at TIMESTAMP NOT NULL)''')
        self.cur.execute('''CREATE OR REPLACE FUNCTION jev_memory_tenant_policy(
            schema_in VARCHAR2, table_in VARCHAR2) RETURN VARCHAR2 AS BEGIN
            RETURN q'[tenant_id = SYS_CONTEXT('jev_memory_ctx','tenant_id')]'; END;''')
        self.cur.execute('SELECT object_name FROM user_policies')
        protected = {r[0] for r in self.cur}
        for table in TABLES:
            if table not in protected:
                self.cur.execute('''BEGIN DBMS_RLS.ADD_POLICY(
                    object_schema => USER, object_name => :tab,
                    policy_name => :pol, policy_function => 'jev_memory_tenant_policy',
                    statement_types => 'SELECT,INSERT,UPDATE,DELETE', update_check => TRUE); END;''',
                    tab=table, pol=table + '_TENANT_POL')
        self.cur.execute('SELECT index_name FROM user_indexes')
        indexes = {r[0] for r in self.cur}
        if 'IDX_JEV_ENTITY_TEXT' not in indexes:
            self.cur.execute("CREATE INDEX idx_jev_entity_text ON jev_entity_memory(content) INDEXTYPE IS CTXSYS.CONTEXT PARAMETERS ('SYNC (ON COMMIT)')")
        if 'IDX_JEV_ENTITY_ACTIVE_HASH' not in indexes:
            self.cur.execute('''CREATE UNIQUE INDEX idx_jev_entity_active_hash ON jev_entity_memory (
                CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN tenant_id END,
                CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN user_id END,
                CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN agent_id END,
                CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN thread_id END,
                CASE WHEN valid_until IS NULL AND deleted_at IS NULL THEN content_hash END)''')
        self.conn.commit()
        self.set_tenant(self.scope.tenant_id)

    def event(self, label, text, role='tool', tenant=None):
        event_id = self.run_id + '_' + label
        self.cur.execute('''INSERT INTO jev_conversation_memory
            (event_id,tenant_id,user_id,agent_id,thread_id,run_id,turn_index,event_type,role,payload,created_at)
            VALUES (:id,:tenant,:usr,:agent,:thread,:run,1,'tool_result',:role,JSON(:payload),SYS_EXTRACT_UTC(SYSTIMESTAMP))''',
            id=event_id, tenant=tenant or self.scope.tenant_id, usr=self.scope.user_id,
            agent=self.scope.agent_id, thread=self.scope.thread_id, run=self.run_id,
            role=role, payload=json.dumps({'text': text, 'fixture': True}))
        return event_id

    def insert_entity(self, label, content, source, *, tenant=None, user='user:jane',
                      version=1, old_id=None, expired=False, deleted=False, future=False):
        entity_id = self.run_id + '_' + label
        self.cur.execute(f'''INSERT INTO jev_entity_memory
            (id,tenant_id,user_id,agent_id,subject,predicate,content,content_hash,content_json,
             embedding,confidence,written_by,source_event_id,version,valid_from,valid_until,deleted_at,created_at)
            VALUES (:id,:tenant,:usr,:agent,'customer:acme','support_observation',:content,:hash,
             JSON(:metadata),VECTOR_EMBEDDING({self.embedding_model} USING :embed AS DATA),
             0.99,'promotion_job',:src,:ver,
             SYS_EXTRACT_UTC(SYSTIMESTAMP) + NUMTODSINTERVAL(:future_days,'DAY'),
             CASE WHEN :expired=1 THEN SYS_EXTRACT_UTC(SYSTIMESTAMP)-INTERVAL '1' DAY END,
             CASE WHEN :deleted=1 THEN SYS_EXTRACT_UTC(SYSTIMESTAMP) END,
             SYS_EXTRACT_UTC(SYSTIMESTAMP))''',
            id=entity_id, tenant=tenant or self.scope.tenant_id, usr=user, agent=self.scope.agent_id,
            content=content, hash=digest(content), metadata=json.dumps({'entity_type':'support_observation'}),
            embed=content, src=source, ver=version, future_days=1 if future else 0,
            expired=int(expired), deleted=int(deleted))
        if old_id:
            self.cur.execute('''UPDATE jev_entity_memory SET valid_until=SYS_EXTRACT_UTC(SYSTIMESTAMP),
                superseded_by=:new_id WHERE id=:old_id AND valid_until IS NULL AND deleted_at IS NULL''',
                new_id=entity_id, old_id=old_id)
            if self.cur.rowcount != 1:
                raise ValueError('Supersession target changed; transaction must roll back.')
        return entity_id

    def seed(self):
        # All canonical seed facts are reviewed fixtures, not agent-generated claims.
        self.source_text = ('On 2026-08-22, manager Ada approved a one-time refund for customer Acme, '
                            'transaction TX-100 only, despite its being 45 days old. '
                            'This approval does not authorize any other transaction or future refunds.')
        self.source_id = self.event('approval', self.source_text)
        self.ids = {}
        self.ids['exception'] = self.insert_entity('exception',
            'Acme received a one-time refund for TX-100 at 45 days. Approval was limited to TX-100 and grants no future entitlement.', self.source_id)
        self.ids['irrelevant'] = self.insert_entity('irrelevant',
            'Acme requested a blue dashboard theme for its account.', self.event('theme','Acme requested a blue dashboard theme.'))
        old = self.insert_entity('old', 'Acme refunds can be processed through the legacy mailbox.',
                                 self.event('old_source','The legacy refund mailbox was active last year.'))
        self.ids['old'] = old
        self.ids['current_process'] = self.insert_entity('current_process',
            'Acme refund requests must use the support portal; the legacy mailbox is retired.',
            self.event('new_source','The support portal replaced the legacy refund mailbox.'), version=2, old_id=old)
        for label, kwargs in [('expired', {'expired':True}), ('deleted', {'deleted':True}),
                              ('future', {'future':True}), ('other_user', {'user':'user:someone_else'})]:
            self.ids[label] = self.insert_entity(label, f'Refund entitlement secret fixture {label}.',
                                                self.event(label+'_source', 'Excluded fixture.'), **kwargs)
        self.guideline = 'Refunds within 30 days follow standard policy. Older purchases require a new approval for the specific transaction. Prior exceptions confer no future entitlement.'
        g_source = self.event('policy_source', self.guideline)
        self.cur.execute('''INSERT INTO jev_guideline_memory
            (id,tenant_id,guideline_key,guideline_value,version,valid_from,written_by,source_event_id,created_at)
            VALUES (:id,:tenant,'refund_policy',JSON(:payload),1,SYS_EXTRACT_UTC(SYSTIMESTAMP),'admin:fixture',:src,SYS_EXTRACT_UTC(SYSTIMESTAMP))''',
            id=self.run_id+'_policy', tenant=self.scope.tenant_id, payload=json.dumps({'text':self.guideline}), src=g_source)
        self.cur.execute('''INSERT INTO jev_persona_memory
            (id,tenant_id,user_id,persona_key,persona_value,written_by,source_event_id,valid_from,created_at)
            VALUES (:id,:tenant,:usr,'response_format',JSON(:payload),'user',:src,SYS_EXTRACT_UTC(SYSTIMESTAMP),SYS_EXTRACT_UTC(SYSTIMESTAMP))''',
            id=self.run_id+'_persona', tenant=self.scope.tenant_id, usr=self.scope.user_id,
            payload=json.dumps({'text':'Use concise explanations with source references.'}), src=self.event('preference','Use concise explanations with source references.'))
        self.set_tenant(self.globex)
        self.ids['globex'] = self.insert_entity('globex','Globex refund secret: all purchases reimbursed.',
            self.event('globex_source','Globex confidential policy.',tenant=self.globex),tenant=self.globex)
        self.conn.commit()
        self.set_tenant(self.scope.tenant_id)
        self.results['fixtures'] = self.ids
        return {'tenant': self.scope.tenant_id, 'entity_fixtures': len(self.ids), 'embedding_dimensions':384}

    def assess(self, stage, state, questions):
        started = time.perf_counter()
        response = self.client.system_one(state=state, questions=questions)
        elapsed = (time.perf_counter()-started)*1000
        return self.record_assessment(stage, state, questions, response, elapsed)

    def record_assessment(self, stage, state, questions, response, elapsed):
        """Persist an already-received response; this method makes no API call."""
        result = response.model_dump(mode='json')
        call = {'stage':stage, 'elapsed_ms':round(elapsed,2), 'question_count':len(questions),
                'model':result['model'], 'usage':result['usage'], 'answers':result['answers'],
                'state_hash':digest(json.dumps(state,sort_keys=True)),
                'question_version':QUESTION_VERSION, 'policy_version':POLICY_VERSION}
        call['estimated_usd'] = result['usage']['input_tokens'] * INPUT_PRICE_PER_MILLION / 1_000_000
        self.calls.append(call)
        # Store supplied evidence and rubric as well as the returned distribution.
        record = {**call, 'state':state, 'questions':{k:v.model_dump(mode='json') for k,v in questions.items()}}
        self.cur.execute('''INSERT INTO jev_assessment_memory
            (id,tenant_id,user_id,agent_id,thread_id,run_id,stage,policy_version,question_version,record_json,created_at)
            VALUES (:id,:tenant,:usr,:agent,:thread,:run,:stage,:policy,:question,JSON(:record),SYS_EXTRACT_UTC(SYSTIMESTAMP))''',
            id=uuid.uuid4().hex,tenant=self.scope.tenant_id,usr=self.scope.user_id,
            agent=self.scope.agent_id,thread=self.scope.thread_id,run=self.run_id,stage=stage,
            policy=POLICY_VERSION,question=QUESTION_VERSION,record=json.dumps(record))
        self.conn.commit()
        return result['answers']

    def mandatory_context(self):
        self.cur.execute(f'''SELECT id, version, source_event_id,
            JSON_VALUE(guideline_value,'$.text') content FROM jev_guideline_memory WHERE {SCOPE}''', self.scope.binds())
        guidelines=rows(self.cur)
        if not guidelines:
            raise ValueError('Required guideline missing; stop.')
        self.cur.execute(f'''SELECT id, source_event_id, JSON_VALUE(persona_value,'$.text') content
            FROM jev_persona_memory WHERE {SCOPE}''', self.scope.binds())
        return guidelines + rows(self.cur)

    def hybrid_retrieve(self, query, lexical, pool=6):
        # Each pool is scoped and current before ranking. Exact vector scan is sufficient
        # for this tiny corpus; no ANN accuracy or throughput claims are made.
        binds={**self.scope.binds(), 'query':query, 'lexical':lexical, 'pool':pool}
        self.cur.execute(f'''WITH vector_pool AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY VECTOR_DISTANCE(embedding,
                VECTOR_EMBEDDING({self.embedding_model} USING :query AS DATA), COSINE), id) rnk
            FROM jev_entity_memory WHERE {SCOPE}
        ), lexical_pool AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY SCORE(1) DESC,id) rnk
            FROM jev_entity_memory WHERE {SCOPE} AND CONTAINS(content,:lexical,1)>0
        ), contributions AS (
            SELECT id, 1/(60+rnk) contribution, rnk vector_rank, CAST(NULL AS NUMBER) lexical_rank
            FROM vector_pool WHERE rnk <= :pool
            UNION ALL
            SELECT id, 1/(60+rnk), CAST(NULL AS NUMBER), rnk FROM lexical_pool WHERE rnk <= :pool
        ), fused AS (
            SELECT id,SUM(contribution) rrf,MIN(vector_rank) vector_rank,MIN(lexical_rank) lexical_rank
            FROM contributions GROUP BY id
        ) SELECT e.id,e.version,e.source_event_id,e.content,f.rrf,f.vector_rank,f.lexical_rank
          FROM fused f JOIN jev_entity_memory e ON e.id=f.id ORDER BY f.rrf DESC,e.id''',binds)
        return [dict(r,key=f'c{i}') for i,r in enumerate(rows(self.cur))]

    def retrieval_example(self):
        requests=[('Can you do what you did last time? I need a refund for TX-200, bought 45 days ago.', 'prior_resolution'),
                  ('What is the current refund policy?', 'current_policy'),
                  ('Can you help me with that thing?', 'clarify')]
        results=[]
        for message, expected in requests:
            answers=self.assess('routing',{'request':message}, {'route':Choice(
                instructions='Which evidence route does `request` need? Choose clarification when the subject cannot be identified.',
                criteria={'prior_resolution':'The user refers to a previous resolution or asks to repeat it.',
                          'current_policy':'The user asks about applicable refund rules without reference to a prior resolution.',
                          'clarify':'The subject or requested action is not identifiable.'})})
            results.append({'request':message,'expected':expected,'actual':route_policy(answers['route']),
                            'answer':answers['route']})
        self.request=requests[0][0]
        self.mandatory=self.mandatory_context()  # Always required, regardless of route.
        self.candidates = (self.hybrid_retrieve('Acme previous refund exception transaction approval', 'refund OR approval')
                           if results[0]['actual']=='prior_resolution' else [])
        result={'routes':results,'mandatory':self.mandatory,'candidates':self.candidates}
        self.results['retrieval']=result
        return result

    def selection_example(self):
        questions={}
        for row in self.candidates:
            key=row['key']
            questions[key+'_use']=Choice(
                instructions=f'How may `candidates.{key}.content` be used for `request`, given `guidelines`? Historical exceptions do not authorize a new transaction.',
                criteria={'applicable':'Directly applicable current evidence for this task.',
                          'history':'Relevant history only; must preserve its original transaction or scope limitation.',
                          'irrelevant':'Does not help this request.',
                          'insufficient':'Not enough evidence to determine how this applies.'})
            questions[key+'_relevance']=Score(
                instructions=f'How directly does `candidates.{key}.content` help answer `request`?',
                criteria=['Unrelated to the request.','Provides useful background.','Directly addresses the request.'])
        if not questions:
            result={'evidence':self.mandatory,'decisions':[],'status':'No optional candidates; clarify or use mandatory evidence.'}
        else:
            state={'request':self.request,'guidelines':self.guideline,
                   'candidates':{c['key']:c for c in self.candidates}}
            answers=self.assess('selection',state,questions)
            result=select_context(self.candidates,answers,self.mandatory)
            result['answers']=answers
        self.results['selection']=result
        return result

    def source(self, source_id):
        self.cur.execute('''SELECT event_id, JSON_VALUE(payload,'$.text') content FROM jev_conversation_memory
            WHERE event_id=:id AND (user_id IS NULL OR user_id=:usr)
              AND (agent_id IS NULL OR agent_id=:agent)''',
            id=source_id,usr=self.scope.user_id,agent=self.scope.agent_id)
        values=rows(self.cur)
        return values[0] if values else None

    @staticmethod
    def promotion_questions():
        return {
            'supported':Noul(instructions='Is every factual claim in `candidate` explicitly supported by `source.content`? Do not infer future rights from a past event.'),
            'scope_fits':Noul(instructions='Does `candidate` preserve all limitations in `source.content`, including the customer, transaction, and one-time nature?'),
            'conflict':Noul(instructions='Does `candidate` contradict `guideline` or the current facts in `existing`? A scoped historical exception does not contradict the requirement for new approval.')}

    def prepare_promotion(self, candidate, source_id):
        """Fetch evidence or return an exact-check rejection before calling Jev."""
        source=self.source(source_id)
        if not source:
            return {'candidate':candidate,'decision':'reject_missing_source','jev_called':False}
        self.cur.execute(f'SELECT id FROM jev_entity_memory WHERE {SCOPE} AND content_hash=:hash',
                         {**self.scope.binds(),'hash':digest(candidate)})
        if self.cur.fetchone():
            return {'candidate':candidate,'decision':'duplicate','jev_called':False}
        current=self.hybrid_retrieve(candidate,'refund OR approval')
        mandatory_snapshot=self.mandatory_context()
        state={'candidate':candidate,'source':source,'guideline':mandatory_snapshot,
               'existing':[{k:r[k] for k in ('id','version','content')} for r in current]}
        return {'state':state,'source':source,'current':current,'mandatory_snapshot':mandatory_snapshot}

    def promote(self, label, candidate, source_id):
        prepared=self.prepare_promotion(candidate,source_id)
        if 'decision' in prepared:
            return prepared
        state=prepared['state']
        answers=self.assess('promotion_'+label,state,self.promotion_questions())
        decision=promotion_policy(answers)
        result={'candidate':candidate,'decision':decision,'answers':answers,'jev_called':True}
        if decision=='promote':
            result['id']=self.commit_promotion(label,candidate,prepared['source'],prepared['current'],prepared['mandatory_snapshot'])
        return result

    def commit_promotion(self,label,candidate,source,current,mandatory_snapshot):
        try:
            # Lock and recheck the specific evidence used in the assessment.
            self.cur.execute('SELECT event_id FROM jev_conversation_memory WHERE event_id=:id FOR UPDATE',id=source['event_id'])
            if not self.cur.fetchone() or self.source(source['event_id'])!=source:
                raise ValueError('Source changed during assessment.')
            for record in current:
                self.cur.execute('SELECT version,valid_until,deleted_at FROM jev_entity_memory WHERE id=:id FOR UPDATE',id=record['id'])
                live=self.cur.fetchone()
                if not live or live!=(record['version'],None,None):
                    raise ValueError('Canonical evidence changed during assessment.')
            self.cur.execute('SELECT id FROM jev_guideline_memory FOR UPDATE')
            self.cur.fetchall()
            if self.mandatory_context()!=mandatory_snapshot:
                raise ValueError('Mandatory context changed during assessment.')
            entity_id=self.insert_entity('promoted_'+label,candidate,source['event_id'])
            self.event('promote_'+label,json.dumps({'decision':'promote','entity_id':entity_id,
                'source_event_id':source['event_id'],'policy_version':POLICY_VERSION,
                'question_version':QUESTION_VERSION,'model':self.calls[-1]['model']}))
            self.conn.commit()
            return entity_id
        except Exception:
            self.conn.rollback()
            raise

    def promotion_example(self):
        narrow='On 2026-08-22, Ada approved a one-time refund for Acme transaction TX-100, which was 45 days old; this does not authorize future refunds.'
        cases=[('broad','Acme is always eligible for refunds after the standard window.',self.source_id),
               ('invented','Ada approved a refund for Acme transaction TX-200.',self.source_id),
               ('narrow',narrow,self.source_id),
               ('duplicate',narrow,self.source_id),
               ('missing','Acme has unlimited refunds.',self.run_id+'_missing')]
        result=[dict(label=label,**self.promote(label,candidate,source)) for label,candidate,source in cases]
        self.results['promotion']=result
        return result

    def database_checks(self):
        checks={}
        self.set_tenant(self.scope.tenant_id)
        self.cur.execute('SELECT DISTINCT tenant_id FROM jev_entity_memory')  # Deliberately no WHERE.
        checks['unfiltered_select_tenant_isolated']=[r[0] for r in self.cur]==[self.scope.tenant_id]
        self.set_tenant(None)
        self.cur.execute('SELECT COUNT(*) FROM jev_entity_memory')
        checks['missing_context_fails_closed']=self.cur.fetchone()[0]==0
        self.set_tenant(self.scope.tenant_id)
        try:
            self.cur.execute('''INSERT INTO jev_assessment_memory
                (id,tenant_id,run_id,stage,policy_version,question_version,record_json,created_at)
                VALUES (:id,:tenant,:run,'forbidden','v1','v1',JSON('{}'),SYSTIMESTAMP)''',
                id=uuid.uuid4().hex,tenant=self.globex,run=self.run_id)
            checks['cross_tenant_insert_blocked']=False
        except oracledb.DatabaseError as exc:
            checks['cross_tenant_insert_blocked']=exc.args[0].code==28115
        finally:
            self.conn.rollback()
        retrieved=self.hybrid_retrieve('refund','refund OR approval')
        excluded={self.ids[k] for k in ('old','expired','deleted','future','other_user','globex')}
        checks['scope_and_lifecycle_before_ranking']=not (excluded & {r['id'] for r in retrieved})
        checks['both_hybrid_pools_used']=any(r['vector_rank'] and r['lexical_rank'] for r in retrieved)
        self.cur.execute('SELECT version,superseded_by,valid_until FROM jev_entity_memory WHERE id=:id',id=self.ids['old'])
        v,next_id,until=self.cur.fetchone()
        checks['supersession_preserves_history']=v==1 and next_id==self.ids['current_process'] and until is not None
        # Derived embedding can be discarded and rebuilt from canonical content alone.
        self.cur.execute('UPDATE jev_entity_memory SET embedding=NULL WHERE id=:id',id=self.ids['exception'])
        self.cur.execute(f'''UPDATE jev_entity_memory SET embedding=VECTOR_EMBEDDING({self.embedding_model}
            USING DBMS_LOB.SUBSTR(content,4000,1) AS DATA) WHERE id=:id''',id=self.ids['exception'])
        self.cur.execute(f'''SELECT VECTOR_DISTANCE(embedding,VECTOR_EMBEDDING({self.embedding_model}
            USING DBMS_LOB.SUBSTR(content,4000,1) AS DATA),COSINE) FROM jev_entity_memory WHERE id=:id''',id=self.ids['exception'])
        checks['embedding_rebuilt_from_canonical']=abs(self.cur.fetchone()[0])<1e-5
        self.conn.rollback()
        # Simulate canonical supersession after assessment but before promotion.
        snapshot=self.hybrid_retrieve('refund','refund OR approval')
        self.cur.execute('UPDATE jev_entity_memory SET valid_until=SYS_EXTRACT_UTC(SYSTIMESTAMP) WHERE id=:id',id=self.ids['exception'])
        try:
            self.commit_promotion('stale_probe','Must never be stored.',self.source(self.source_id),snapshot,self.mandatory_context())
            checks['stale_evidence_blocks_promotion']=False
        except ValueError as exc:
            checks['stale_evidence_blocks_promotion']='Canonical evidence changed' in str(exc)
        self.cur.execute('SELECT COUNT(*) FROM jev_entity_memory WHERE id=:id',id=self.run_id+'_promoted_stale_probe')
        checks['failed_promotion_leaves_no_memory']=self.cur.fetchone()[0]==0
        checks['cross_tenant_source_hidden']=self.source(self.run_id+'_globex_source') is None
        self.results['database_checks']=checks
        return checks

    def cleanup(self):
        """Delete this run's fixture tenants from every memory table; rows from other runs stay."""
        deleted = {}
        for tenant in (self.scope.tenant_id, self.globex):
            self.set_tenant(tenant)  # VPD only exposes the current tenant's rows.
            for table in TABLES:
                self.cur.execute(f'DELETE FROM {table} WHERE tenant_id = :tenant', tenant=tenant)
                deleted[table.lower()] = deleted.get(table.lower(), 0) + self.cur.rowcount
        self.conn.commit()
        self.set_tenant(self.scope.tenant_id)
        return deleted

    def benchmark(self, repeats=3):
        state={'candidate':'Ada approved TX-100 only; no future refunds are authorized.',
               'source':{'content':self.source_text},'guideline':self.guideline,'existing':[]}
        questions=self.promotion_questions()
        start=len(self.calls)
        trials=[]
        for trial in range(repeats):
            # Alternate order to reduce connection warm-up/order effects.
            modes=('batch','separate') if trial%2==0 else ('separate','batch')
            collected={}
            for mode in modes:
                before=len(self.calls)
                if mode=='batch':
                    answers=self.assess('benchmark_batch',state,questions)
                else:
                    answers={}
                    for key,question in questions.items():
                        answers.update(self.assess('benchmark_separate',state,{key:question}))
                calls=self.calls[before:]
                collected[mode]={'elapsed_ms':sum(c['elapsed_ms'] for c in calls),
                                 'input_tokens':sum(c['usage']['input_tokens'] for c in calls),
                                 'estimated_usd':sum(c['estimated_usd'] for c in calls),
                                 'decision':promotion_policy(answers),'answers':answers}
            trials.append(collected)
        result={'repeats':repeats,'calls':len(self.calls)-start,'trials':trials,
                'batch_median_ms':statistics.median(t['batch']['elapsed_ms'] for t in trials),
                'separate_median_ms':statistics.median(t['separate']['elapsed_ms'] for t in trials),
                'batch_input_tokens':sum(t['batch']['input_tokens'] for t in trials),
                'separate_input_tokens':sum(t['separate']['input_tokens'] for t in trials),
                'policy_agreement':all(t['batch']['decision']==t['separate']['decision'] for t in trials)}
        self.results['benchmark']=result
        return result

    def save(self):
        self.results['calls']=self.calls
        self.results['totals']={'api_calls':len(self.calls),'input_tokens':sum(c['usage']['input_tokens'] for c in self.calls),
                                'estimated_usd':sum(c['estimated_usd'] for c in self.calls)}
        (ROOT/'results').mkdir(exist_ok=True)
        path=ROOT/'results'/f'run-{self.run_id}.json'
        path.write_text(json.dumps(self.results,indent=2))
        return path


def main():
    load_dotenv()
    demo=MemoryDemo(user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'],
                    dsn=os.getenv('DB_DSN', 'localhost:1521/FREEPDB1'))
    try:
        demo.setup()
        print('Seed:',demo.seed())
        for name in ('database_checks','retrieval_example','selection_example','promotion_example','benchmark'):
            print(name,json.dumps(getattr(demo,name)(),indent=2))
        print('Saved:',demo.save())
    finally:
        demo.close()


if __name__=='__main__':
    main()
