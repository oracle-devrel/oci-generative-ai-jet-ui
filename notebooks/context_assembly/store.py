"""Oracle 26ai typed tables with tenant VPD and scoped application reads."""
from __future__ import annotations
import json,os,re,uuid,math
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
import oracledb
from dotenv import load_dotenv
oracledb.defaults.program = "devrel-developerhub-context-assembly-for-agent-memory"
oracledb.defaults.fetch_lobs = False
from config import SCOPE,TABLES,AS_OF,QUESTION,dumps,digest,row,TOOLS,BUDGET
from baseline_seed import seed_schema,seed_two_layer,seed_infrastructure
from research_corpus import DOCUMENTS,CHUNKS
from retrieval import understand_query,build_lexical_query

ROOT=Path(__file__).parent
BASE_TABLES=list(dict.fromkeys([*TABLES.values(),"KNOWLEDGE_BASE_DOCUMENT","DELETION_EVENTS"]))
class ReplayUnavailable(RuntimeError):pass

def load_environment():
    explicit=os.getenv("CONTEXT_ENV_FILE") or os.getenv("CA6_ENV_FILE")
    load_dotenv(explicit or ROOT/'.env',override=False)
    load_dotenv(os.getenv('CONTEXT_DB_ENV_FILE') or ROOT.parents[1]/'.env',override=False)
def load_config():
    load_environment()
    if any(not os.getenv(k) for k in ('DB_USER','DB_PASSWORD','DB_DSN')):raise RuntimeError('Set DB_USER, DB_PASSWORD, DB_DSN in an ignored .env.')
    return {k:os.environ[k] for k in ('DB_USER','DB_PASSWORD','DB_DSN')}
def json_value(v):return json.loads(v) if isinstance(v,str) else json.loads(dumps(v or {}))
def calibrated(raw):return 1/(1+math.exp(-max(-700,min(700,float(raw)))))

class OracleStore:
    mode='oracle'
    def __init__(self,config=None):
        c=config or load_config();self.pool=oracledb.create_pool(user=c['DB_USER'],password=c['DB_PASSWORD'],dsn=c['DB_DSN'],min=1,max=2,increment=1)
    def close(self):self.pool.close()
    @contextmanager
    def connection(self,scope=SCOPE):
        with self.pool.acquire() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("ALTER SESSION SET TIME_ZONE='UTC'")
                    cur.callproc('set_memory_ctx.set_tenant',[scope['tenant_id']])
                yield conn
            finally:
                conn.rollback()
                try:
                    with conn.cursor() as cur:cur.callproc('set_memory_ctx.set_tenant',[None])
                except Exception:self.pool.drop(conn);raise
    def setup(self):
        with self.pool.acquire() as conn,conn.cursor() as cur:
            cur.execute("select privilege from session_privs where privilege='EXEMPT ACCESS POLICY'")
            if cur.fetchone() or conn.username.upper()=='SYS':raise RuntimeError('Use a non-SYS owner without EXEMPT ACCESS POLICY.')
            cur.execute('select object_name from user_objects');existing={v[0] for v in cur}
            for ddl in json.loads((ROOT/'schema_statements.json').read_text()):
                name=re.match(r'CREATE (?:UNIQUE |VECTOR )?(?:TABLE|INDEX)\s+(\w+)',ddl,re.I)[1].upper()
                if name not in existing:cur.execute(ddl);existing.add(name)
                if re.match('CREATE TABLE',ddl,re.I):
                    expected={m[0].upper() for m in re.findall(r'^\s*(\w+)\s+(VARCHAR2|NUMBER|TIMESTAMP|JSON|CLOB|VECTOR)',ddl,re.M)}
                    cur.execute('select column_name from user_tab_columns where table_name=:t',t=name)
                    actual={v[0] for v in cur}
                    if expected!=actual:raise RuntimeError(f'{name} differs from the original full schema; reconcile the schema before running this notebook.')
            # Preserve the previous context/package when already present.
            if 'SET_MEMORY_CTX' not in existing:
                cur.execute('CREATE PACKAGE set_memory_ctx AS PROCEDURE set_tenant(p_tenant_id VARCHAR2); END;')
                cur.execute("CREATE PACKAGE BODY set_memory_ctx AS PROCEDURE set_tenant(p_tenant_id VARCHAR2) IS BEGIN DBMS_SESSION.SET_CONTEXT('memory_ctx','tenant_id',p_tenant_id); END; END;")
                try:cur.execute('CREATE CONTEXT memory_ctx USING set_memory_ctx')
                except oracledb.DatabaseError as e:
                    if e.args[0].code!=955:raise
                cur.callproc('set_memory_ctx.set_tenant',['acme'])
                cur.execute("select sys_context('memory_ctx','tenant_id') from dual")
                if cur.fetchone()[0]!='acme':raise RuntimeError('Existing memory_ctx is not bound to set_memory_ctx.')
                cur.callproc('set_memory_ctx.set_tenant',[None])
            if 'MEMORY_TENANT_POLICY' not in existing:
                cur.execute("CREATE FUNCTION memory_tenant_policy(s VARCHAR2,t VARCHAR2) RETURN VARCHAR2 AS BEGIN RETURN 'tenant_id=SYS_CONTEXT(''memory_ctx'',''tenant_id'')'; END;")
            extra={
              'CONTEXT_SOURCE_REF':'''CREATE TABLE context_source_ref (id VARCHAR2(64) PRIMARY KEY,tenant_id VARCHAR2(64) NOT NULL,user_id VARCHAR2(64),agent_id VARCHAR2(64),thread_id VARCHAR2(64),derived_kind VARCHAR2(64) NOT NULL,derived_id VARCHAR2(64) NOT NULL,source_kind VARCHAR2(64) NOT NULL,source_id VARCHAR2(64) NOT NULL,source_version NUMBER,created_at TIMESTAMP NOT NULL)''',
              'CONTEXT_COMPRESSION':'''CREATE TABLE context_compression (id VARCHAR2(64) PRIMARY KEY,tenant_id VARCHAR2(64) NOT NULL,user_id VARCHAR2(64),agent_id VARCHAR2(64),thread_id VARCHAR2(64),version NUMBER NOT NULL,content CLOB NOT NULL,source_hash VARCHAR2(64) NOT NULL,model_id VARCHAR2(128) NOT NULL,prompt_version VARCHAR2(64) NOT NULL,origin VARCHAR2(32) NOT NULL,metadata JSON,valid_from TIMESTAMP NOT NULL,valid_until TIMESTAMP,deleted_at TIMESTAMP,created_at TIMESTAMP NOT NULL)'''}
            for name,ddl in extra.items():
                if name not in existing:cur.execute(ddl)
            cur.execute('select object_name,policy_name from user_policies');policies=set(cur.fetchall())
            for table in BASE_TABLES+['CONTEXT_SOURCE_REF']:
                if not any(t==table for t,p in policies):
                    cur.execute("""BEGIN DBMS_RLS.ADD_POLICY(object_schema=>USER,object_name=>:t,policy_name=>'context_tenant',policy_function=>'memory_tenant_policy',statement_types=>'SELECT,INSERT,UPDATE,DELETE',update_check=>TRUE); END;""",t=table)
            cur.execute("select model_name from user_mining_models where model_name in ('ALL_MINILM_L12_V2','BGE_RERANKER')")
            if {r[0] for r in cur}!={'ALL_MINILM_L12_V2','BGE_RERANKER'}:raise RuntimeError('Load the embedding and reranker models using model_setup.py before seeding.')
        return {'base_tables':10,'additional_tables':['CONTEXT_COMPRESSION','CONTEXT_SOURCE_REF'],'existing_tables_altered':False}
    def seed_original(self):
        with self.connection() as conn,conn.cursor() as cur:seed_schema(conn,cur);seed_two_layer(conn,cur);seed_infrastructure(conn,cur)
        self.seed_corpus('tenant_acme','agent:research_v1')
        return {'schema_seed':'original Stripe payloads','two_layer_seed':'original Helios payloads','hybrid_seed':{'tenant':'tenant_acme','documents':len(DOCUMENTS),'chunks':len(CHUNKS)}}
    def seed_corpus(self,tenant,agent):
        scope=dict(SCOPE,tenant_id=tenant,agent_id=agent)
        with self.connection(scope) as conn,conn.cursor() as cur:
            ids={};counter={}
            for collection,key,title,uri,stype in DOCUMENTS:
                did='corpus_'+digest(tenant+'|'+key)[:24];ids[key]=did
                cur.execute('select count(*) from knowledge_base_document where id=:id',id=did)
                if cur.fetchone()[0]:continue
                cur.execute("""INSERT INTO knowledge_base_document(id,tenant_id,agent_id,collection,title,source_uri,source_type,metadata,ingested_at,ingested_by,version,valid_from,created_at) VALUES(:id,:t,:a,:col,:title,:uri,:typ,JSON(:meta),:at,'ingest:pipeline',1,:at,:at)""",id=did,t=tenant,a=agent,col=collection,title=title,uri=uri,typ=stype,meta=dumps({'doc_key':key}),at=datetime(2026,7,1))
            for key,section,text in CHUNKS:
                ix=counter.get(key,0);counter[key]=ix+1;cid='corpus_'+digest(tenant+'|'+key+'|'+str(ix))[:24]
                cur.execute('select count(*) from knowledge_base_chunk where id=:id',id=cid)
                if cur.fetchone()[0]:continue
                cur.execute("""INSERT INTO knowledge_base_chunk(id,tenant_id,document_id,chunk_index,content,embedding,metadata,created_at) VALUES(:id,:t,:doc,:ix,:text,VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :text AS DATA),JSON(:meta),:at)""",id=cid,t=tenant,doc=ids[key],ix=ix,text=text,meta=dumps({'section_type':section}),at=datetime(2026,7,1))
            conn.commit()
    def insert(self,table,values,scope=SCOPE,embedded=None):
        assert table in BASE_TABLES+['CONTEXT_SOURCE_REF']
        with self.connection(scope) as conn,conn.cursor() as cur:
            pk='event_id' if table=='CONVERSATION_MEMORY' else 'id'
            cur.execute(f'SELECT COUNT(*) FROM {table} WHERE {pk}=:id',id=values[pk])
            if cur.fetchone()[0]:return
            cur.execute(f"select column_name from user_tab_columns where table_name=:t and data_type='JSON'",t=table);jcols={x[0].lower() for x in cur}
            expr=[];bind={}
            for k,v in values.items():
                if k in jcols:expr.append('JSON(:'+k+')');bind[k]=dumps(v)
                else:expr.append(':'+k);bind[k]=v
            cols=list(values)
            if embedded:
                cols.append('embedding');expr.append('VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :'+embedded+' AS DATA)')
            cur.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(expr)})",bind);conn.commit()
    def add_source(self,derived,source,scope=SCOPE):
        self.insert('CONTEXT_SOURCE_REF',{'id':digest(dumps([derived,source,scope]))[:48],**scope,'derived_kind':derived[0],'derived_id':derived[1],'source_kind':source[0],'source_id':source[1],'source_version':source[2],'created_at':AS_OF},scope)
    def upgrade_seed_terminology(self):
        """Version additional tutorial rows at the fixed evaluation time; retain their history."""
        expand_schema=next(sch for name,_,sch in TOOLS if name=='expand')
        with self.connection() as conn,conn.cursor() as cur:
            cur.execute("SELECT id,version,tool_schema FROM toolbox_memory WHERE tool_name='expand' AND agent_id=:agent AND id LIKE 'context_tool_expand%' AND valid_until IS NULL AND deleted_at IS NULL FOR UPDATE",agent=SCOPE['agent_id'])
            for old,version,stored_schema in cur.fetchall():
                if json_value(stored_schema)==expand_schema:continue
                new='context_tool_expand_v'+str(int(version)+1)
                cur.execute('UPDATE toolbox_memory SET valid_until=:at,superseded_by=:new WHERE id=:old',at=AS_OF,new=new,old=old)
                cur.execute("INSERT INTO toolbox_memory(id,tenant_id,user_id,agent_id,tool_name,tool_schema,tool_handler,access_policy,usage_notes,embedding,version,valid_from,written_by,source_event_id,created_at) SELECT :new,tenant_id,user_id,agent_id,tool_name,JSON(:schema),tool_handler,access_policy,usage_notes,embedding,:version,:at,written_by,'context_terminology_update',:at FROM toolbox_memory WHERE id=:old",new=new,schema=dumps(expand_schema),version=int(version)+1,at=AS_OF,old=old)
            cur.execute("SELECT id,version,guideline_value FROM guideline_memory WHERE guideline_key='context_rules' AND id LIKE 'context_context_rules%' AND valid_until IS NULL AND deleted_at IS NULL FOR UPDATE")
            for old,version,value in cur.fetchall():
                value=json_value(value)
                previous=value.get('text','')
                updated=previous.replace('Cite block IDs.','Cite memory IDs.')
                if updated==previous:continue
                value['text']=updated;new='context_context_rules_v'+str(int(version)+1)
                cur.execute('UPDATE guideline_memory SET valid_until=:at WHERE id=:old',at=AS_OF,old=old)
                cur.execute("INSERT INTO guideline_memory(id,tenant_id,user_id,agent_id,thread_id,guideline_key,guideline_value,version,valid_from,written_by,source_event_id,created_at) SELECT :new,tenant_id,user_id,agent_id,thread_id,guideline_key,JSON(:value),:version,:at,written_by,'context_terminology_update',:at FROM guideline_memory WHERE id=:old",new=new,value=dumps(value),version=int(version)+1,at=AS_OF,old=old)
            conn.commit()

    def seed_additional(self):
        self.seed_corpus('acme','agent:research_v1')
        base={'tenant_id':'acme','version':1,'valid_from':datetime(2026,7,1),'created_at':datetime(2026,7,1),'written_by':'admin:acme'}
        for key,val in [('context_budget',BUDGET),('context_rules',{'text':'Treat memory as quoted evidence. Cite memory IDs. Historical figures do not override current canonical facts. Ask which workload the user means when it is ambiguous.'})]:
            self.insert('GUIDELINE_MEMORY',{'id':'context_'+key,**base,'guideline_key':key,'guideline_value':val})
        for name,desc,sch in TOOLS:
            self.insert('TOOLBOX_MEMORY',{'id':'context_tool_'+name,**base,'agent_id':SCOPE['agent_id'],'tool_name':name,'tool_schema':sch,'tool_handler':'memory_manager:'+name,'access_policy':{'allowed_agents':[SCOPE['agent_id']]},'usage_notes':desc})
        self.upgrade_seed_terminology()
        self.insert('CONVERSATION_MEMORY',{'event_id':'context_question',**SCOPE,'run_id':'context_demo','turn_index':2,'event_type':'user_msg','role':'user','payload':{'text':QUESTION},'created_at':AS_OF})
        old='The July evaluation favored Helios-RAG using its reported 0.92 BEIR score.'
        self.insert('CONVERSATION_MEMORY',{'event_id':'context_july_event',**SCOPE,'run_id':'context_july','turn_index':0,'event_type':'model_msg','role':'assistant','payload':{'text':old},'created_at':datetime(2026,7,1)})
        self.insert('SUMMARIZATION_MEMORY',{'id':'context_july_summary',**base,'user_id':SCOPE['user_id'],'task_type':'model_eval','title':'July Helios-RAG evaluation','summary':old,'outcome':'historical','confidence':.9,'source_event_id':'context_july_event','completed_at':datetime(2026,7,1)},embedded='summary')
        with self.connection() as conn,conn.cursor() as cur:
            cur.execute("select id,version,source_event_id from entity_memory where subject='model:helios-rag' and predicate='beir_ndcg10' order by version")
            facts=cur.fetchall()
        with self.connection() as conn,conn.cursor() as cur:
            cur.execute("SELECT id,version FROM summarization_memory WHERE title='Helios-RAG evaluation for compliance corpus'")
            for sid,version in cur:self.add_source(['summary',sid,int(version)],['entity',facts[-1][0],int(facts[-1][1])])
        for id,v,e in facts:self.add_source(['entity',id,int(v)],['conversation',e,None])
        self.add_source(['summary','context_july_summary',1],['entity',facts[0][0],int(facts[0][1])])
        for name,scope,content,extra in [('context_other_user',dict(SCOPE,user_id='user:bob@acme.com'),'PRIVATE_USER_SENTINEL',{}),('context_globex',dict(SCOPE,tenant_id='globex'),'GLOBEX_PRIVATE_SENTINEL',{}),('context_future',SCOPE,'FUTURE_SENTINEL',{'valid_from':datetime(2027,1,1)}),('context_deleted',SCOPE,'DELETED_SENTINEL',{'deleted_at':datetime(2026,9,1)})]:
            self.insert('ENTITY_MEMORY',{'id':name,**base,**scope,'subject':name,'predicate':'test_scope','content':content,'content_hash':digest(content),'confidence':1,'source_event_id':'context_scope_test',**extra},scope,embedded='content')
        self.insert('CONVERSATION_MEMORY',{'event_id':'context_other_thread',**dict(SCOPE,thread_id='private_thread'),'run_id':'context_demo','turn_index':1,'event_type':'user_msg','payload':{'text':'PRIVATE_THREAD_SENTINEL'},'created_at':AS_OF})
        return {'additional':'context budget, four tools, July summary, provenance, isolation rows','corpus_copy':{'from':'tenant_acme','to':'acme','documents':len(DOCUMENTS),'chunks':len(CHUNKS)},'original_rows_replaced':False}
    @staticmethod
    def capture_scn(cur):
        cur.execute('SELECT DBMS_FLASHBACK.GET_SYSTEM_CHANGE_NUMBER FROM dual');return int(cur.fetchone()[0])
    def raw(self,cur,table,scn,scope=SCOPE):
        cur.execute('SELECT column_name FROM user_tab_columns WHERE table_name=:t',t=table)
        columns={v[0].lower() for v in cur}
        params={'scn':scn};predicates=[]
        for k in ('user_id','agent_id','thread_id'):
            if k in columns:predicates.append(f'({k} IS NULL OR {k}=:{k})');params[k]=scope[k]
        cur.execute(f'SELECT * FROM {table} AS OF SCN :scn'+(' WHERE '+' AND '.join(predicates) if predicates else ''),params)
        cols=[d[0].lower() for d in cur.description];return [dict(zip(cols,v)) for v in cur]
    def question_event(self,question,scope=SCOPE):
        if question==QUESTION:return 'context_question'
        eid='context_q_'+digest(dumps([scope,question]))[:32]
        self.insert('CONVERSATION_MEMORY',{'event_id':eid,**scope,'run_id':'context_inputs','turn_index':99,'event_type':'context_question','role':'user','payload':{'text':question},'created_at':AS_OF},scope)
        return eid
    def read_question(self,reference,scn,scope=SCOPE):
        if not self.source_available(reference,scope):raise ReplayUnavailable('Question source is unavailable.')
        with self.connection(scope) as conn,conn.cursor() as cur:
            cur.execute('SELECT payload FROM conversation_memory AS OF SCN :scn WHERE event_id=:id',scn=scn,id=reference[1]);value=cur.fetchone()
            if not value:raise ReplayUnavailable('Question source is outside retained undo.')
            return json_value(value[0])['text']
    def snapshot(self,scope=SCOPE,question=QUESTION):
        self.question_event(question,scope)
        with self.connection(scope) as conn,conn.cursor() as cur:scn=self.capture_scn(cur)
        return scn,self.replay_rows(scn,scope,question)
    def replay_rows(self,scn,scope=SCOPE,question=QUESTION,recorded_scores=None):
        from assembly import scope_matches,ref,live
        rows=[]
        try:
            with self.connection(scope) as conn,conn.cursor() as cur:
                raw={k:self.raw(cur,t,scn,scope) for k,t in TABLES.items() if k!='compression'}
                if recorded_scores is None:
                    cur.execute((ROOT/'entity_query.sql').read_text(),query=question,scn=scn,at=AS_OF,**{k:scope[k] for k in ('user_id','agent_id','thread_id')})
                    cols=[x[0].lower() for x in cur.description];raw['entity']=[dict(zip(cols,v)) for v in cur]
                docs={d['id']:d for d in self.raw(cur,'KNOWLEDGE_BASE_DOCUMENT',scn,scope)}
                links=self.raw(cur,'CONTEXT_SOURCE_REF',scn,scope)
                question_id='context_question' if question==QUESTION else 'context_q_'+digest(dumps([scope,question]))[:32]
                for kind,items in raw.items():
                    for d in items:
                        if kind=='kb':
                            parent=docs.get(d['document_id'])
                            if not parent:continue
                            values={**d,**{k:parent.get(k) for k in ('user_id','agent_id','thread_id','valid_from','valid_until')}}
                            if parent['deleted_at']:values['deleted_at']=parent['deleted_at']
                        else:values=d
                        r=row(kind,d.get('id') or d['event_id'],'',**{k:values.get(k) for k in SCOPE},version=d.get('version'),valid_from=values.get('valid_from',d['created_at']),valid_until=values.get('valid_until'),deleted_at=values.get('deleted_at'),source_event_id=d.get('source_event_id'),confidence=float(d['confidence']) if d.get('confidence') is not None else .5)
                        if not scope_matches(r,scope):continue
                        meta={};content='';slice_name='durable_facts'
                        if kind=='guideline':
                            val=json_value(d['guideline_value']);meta={'key':d['guideline_key']};content=val.get('text',dumps(val)) if isinstance(val,dict) else dumps(val);slice_name='guidelines'
                        elif kind=='persona':content=d['persona_key']+': '+dumps(json_value(d['persona_value']));slice_name='persona'
                        elif kind=='tool':
                            access=json_value(d.get('access_policy'));meta={'name':d['tool_name'],'inputSchema':json_value(d['tool_schema']),'allowed_agents':access.get('allowed_agents',[]),'handler':d.get('tool_handler')};content=d.get('usage_notes') or '';slice_name='tools'
                            if meta['handler']!='memory_manager:'+meta['name'] or scope['agent_id'] not in meta['allowed_agents']:continue
                        elif kind=='entity':content=d['content'] or '';r['claim_key']=dumps([d['subject'],d['predicate'],json_value(d.get('content_json')).get('conditions',{})]);meta={'subject':d['subject'],'predicate':d['predicate'],'content_json':json_value(d.get('content_json'))}
                        elif kind=='workflow':content=(d.get('description') or '')+' '+dumps(json_value(d.get('steps')));r['claim_key']='workflow|'+d['workflow_name'];meta={'title':d['workflow_name']}
                        elif kind=='summary':content=d.get('summary') or '';slice_name='recalled_history';meta={'title':d['title']}
                        elif kind=='conversation':
                            if d['event_type'] not in ('user_msg','model_msg','context_question'):continue
                            if (d['event_type']=='context_question' or d['event_id']=='context_question') and d['event_id']!=question_id:continue
                            payload=json_value(d['payload']);content=payload.get('text','');slice_name='question' if d['event_id']==question_id else ('volatile_tail' if d['thread_id']==scope['thread_id'] else 'recalled_history');meta={'event_type':d['event_type'],'turn_index':d['turn_index']}
                            if slice_name=='question' and content!=question:raise ReplayUnavailable('Stored question differs from requested input.')
                        elif kind=='kb':content=d['content'];slice_name='evidence';meta={'title':parent['title'],'collection':parent['collection'],'document_id':parent['id'],'document_version':int(parent['version']),'section_type':json_value(d.get('metadata')).get('section_type'),'parent_ref':['document',parent['id'],int(parent['version'])]}
                        if d.get('rerank_raw') is not None:meta['rerank_raw']=float(d['rerank_raw'])
                        r.update(content=content,content_hash=digest(' '.join(content.split())),slice=slice_name,meta=meta)
                        meta['source_refs']=[[x['source_kind'],x['source_id'],int(x['source_version']) if x['source_version'] is not None else None] for x in links if x['derived_kind']==kind and x['derived_id']==r['id']]
                        if kind=='entity' and meta['content_json'].get('source_document_id'):meta['source_refs'].append(['document',meta['content_json']['source_document_id'],1])
                        event_id=d.get('source_event_id')
                        if event_id and any(e['event_id']==event_id for e in raw['conversation']):
                            event_ref=['conversation',event_id,None]
                            if event_ref not in meta['source_refs']:meta['source_refs'].append(event_ref)
                        rows.append(r)
                if recorded_scores=='unscored':return rows
                if recorded_scores is not None:
                    scored={tuple(x['ref']):x['rerank'] for x in recorded_scores}
                    return [dict(r,rerank=scored[tuple(ref(r))]) for r in rows if tuple(ref(r)) in scored]
                # Measure actual cross-encoder scores for non-KB retrieved types.
                for r in rows:
                    if r['kind'] in ('entity','workflow','summary','conversation') and r['slice']!='question':
                        if 'rerank_raw' in r['meta']:raw_score=r['meta']['rerank_raw']
                        else:
                            cur.execute('SELECT PREDICTION(BGE_RERANKER USING :q AS FIRST_INPUT,:c AS SECOND_INPUT) FROM dual',q=question,c=r['content']);raw_score=float(cur.fetchone()[0])
                        r['rerank']=calibrated(raw_score);r['meta']['rerank_raw']=raw_score
                hits=self.hybrid(scope,question,scn,cur=cur)
                scores={x['id']:x for x in hits}
                retained=[]
                for r in rows:
                    if r['kind']=='kb':
                        if r['id'] not in scores:continue
                        r['rerank']=calibrated(scores[r['id']]['rerank_raw']);r['meta'].update({k:v for k,v in scores[r['id']].items() if k in ('rrf_score','rerank_raw')})
                    retained.append(r)
                return retained
        except oracledb.DatabaseError as e:raise ReplayUnavailable('Oracle snapshot read failed: '+e.args[0].full_code) from e
    def hybrid(self,scope=SCOPE,question=QUESTION,scn=None,cur=None,evaluation_time=AS_OF):
        if cur is None:
            with self.connection(scope) as conn,conn.cursor() as cursor:return self.hybrid(scope,question,scn or self.capture_scn(cursor),cursor,evaluation_time)
        plan=understand_query(question);lex=build_lexical_query(plan)
        collections=['benchmarks','benchmarks'] if 'helios' in question.lower() or 'beir' in question.lower() else (['product-docs','product-docs'] if 'stripe' in question.lower() else plan['collections'])
        cur.execute((ROOT/'hybrid_query.sql').read_text(),scn=scn,query=question,lex_query=lex,user_id=scope['user_id'],agent_id=scope['agent_id'],at=evaluation_time,collection1=collections[0],collection2=collections[1])
        names=['id','content','metadata','document_id','title','source_uri','document_version','rrf_score','rerank_raw'];return [dict(zip(names,v)) for v in cur]
    def current_rows(self,scope=SCOPE):
        with self.connection(scope) as conn,conn.cursor() as cur:scn=self.capture_scn(cur)
        return self.replay_rows(scn,scope,recorded_scores='unscored')
    def toolbox_rows(self,scope=SCOPE):
        from assembly import scope_matches,live
        with self.connection(scope) as conn,conn.cursor() as cur:
            rows=self.raw(cur,'TOOLBOX_MEMORY',self.capture_scn(cur),scope);result=[]
            for d in rows:
                access=json_value(d.get('access_policy'));meta={'name':d['tool_name'],'inputSchema':json_value(d['tool_schema']),'allowed_agents':access.get('allowed_agents',[]),'handler':d.get('tool_handler')}
                r=row('tool',d['id'],d.get('usage_notes') or '',**{k:d.get(k) for k in SCOPE},version=int(d['version']),valid_from=d['valid_from'],valid_until=d['valid_until'],deleted_at=d['deleted_at'],slice='tools',meta=meta)
                if scope_matches(r,scope) and live(r,datetime.utcnow()) and meta['handler']=='memory_manager:'+meta['name'] and scope['agent_id'] in meta['allowed_agents']:result.append(r)
            return result
    def source_available(self,reference,scope=SCOPE):
        kind,id,version=reference;table=TABLES.get(kind) or ('KNOWLEDGE_BASE_DOCUMENT' if kind=='document' else None)
        if not table:return False
        with self.connection(scope) as conn,conn.cursor() as cur:
            cur.execute(f'SELECT * FROM {table} WHERE '+('event_id' if kind=='conversation' else 'id')+'=:id',id=id)
            cols=[c[0].lower() for c in cur.description];v=cur.fetchone()
            if not v:return False
            d=dict(zip(cols,v))
            if d.get('deleted_at') or (version is not None and d.get('version')!=version):return False
            if any(d.get(k) is not None and d[k]!=scope[k] for k in ('user_id','agent_id','thread_id')):return False
            if kind=='kb':
                cur.execute('SELECT * FROM knowledge_base_document WHERE id=:id',id=d['document_id']);cols=[c[0].lower() for c in cur.description];v=cur.fetchone()
                if not v:return False
                parent=dict(zip(cols,v));return not parent['deleted_at'] and all(parent.get(k) is None or parent[k]==scope[k] for k in ('user_id','agent_id'))
            cur.execute('SELECT scope FROM deletion_events WHERE tenant_id=:t AND (user_id IS NULL OR user_id=:u)',t=scope['tenant_id'],u=scope['user_id'])
            for v in cur:
                if v[0] in ('all','tenant','user'):return False
            return True
    def put(self,item):
        if item['kind']!='compression':raise ValueError('Only derived compressions use put; canonical tables are typed.')
        meta=item['meta'];self.insert('CONTEXT_COMPRESSION',{'id':item['id'],**{k:item[k] for k in SCOPE},'version':item['version'],'content':item['content'],'source_hash':meta['source_hash'],'model_id':meta['model'],'prompt_version':meta['prompt_version'],'origin':meta['origin'],'metadata':meta,'valid_from':item['valid_from'],'valid_until':item['valid_until'],'deleted_at':item['deleted_at'],'created_at':AS_OF},{k:item[k] for k in SCOPE})
        for source in meta['source_refs']+meta.get('source_ancestors',[]):self.add_source(['compression',item['id'],item['version']],source,{k:item[k] for k in SCOPE})
    def compression_rows(self,scope=SCOPE):
        from assembly import scope_matches
        with self.connection(scope) as conn,conn.cursor() as cur:
            cur.execute('SELECT * FROM context_compression');cols=[x[0].lower() for x in cur.description];result=[]
            for v in cur:
                d=dict(zip(cols,v));r=row('compression',d['id'],d['content'],**{k:d[k] for k in SCOPE},version=int(d['version']),valid_from=d['valid_from'],valid_until=d['valid_until'],deleted_at=d['deleted_at'],meta=json_value(d['metadata']))
                if scope_matches(r,scope):result.append(r)
            return result
    def erase_derived(self, erased_refs, scope=SCOPE,commit=True):
        """Call within the trusted deletion workflow using refs captured before erasure.
        Extends the earlier cascade for the two new tables; no canonical table is changed.
        """
        with self.connection(scope) as conn,conn.cursor() as cur:
            cur.execute('SELECT id,derived_kind,derived_id,source_kind,source_id FROM context_source_ref')
            links=cur.fetchall();affected={(r[0],r[1]) for r in erased_refs}
            while True:
                expanded=affected|{(k,id) for _,k,id,sk,sid in links if (sk,sid) in affected}
                if expanded==affected:break
                affected=expanded
            deleted=0
            for kind,id in affected:
                if kind=='compression':
                    cur.execute('DELETE FROM context_compression WHERE id=:id',id=id);deleted+=cur.rowcount
            for id,k,d,sk,sd in links:
                if (k,d) in affected or (sk,sd) in affected:cur.execute('DELETE FROM context_source_ref WHERE id=:id',id=id)
            if commit:conn.commit()
            else:conn.rollback()
            return {'affected_refs':sorted([list(x) for x in affected]),'new_tables_only':True,'deleted_compressions':deleted,'committed':commit}
    def save_event(self,event_type,payload,scope=SCOPE):
        eid='context_'+uuid.uuid4().hex;self.insert('CONVERSATION_MEMORY',{'event_id':eid,**{k:v for k,v in scope.items() if k!='agent_id'},'run_id':'context_demo','turn_index':0,'event_type':event_type,'role':'system','payload':payload,'created_at':datetime.utcnow()},scope);return eid
    def load_manifest(self,event_id,scope=SCOPE):
        with self.connection(scope) as conn,conn.cursor() as cur:
            cur.execute("SELECT payload FROM conversation_memory WHERE event_id=:id AND event_type='context_manifest' AND user_id=:u AND thread_id=:th",id=event_id,u=scope['user_id'],th=scope['thread_id'])
            v=cur.fetchone()
            if not v:raise PermissionError('Window manifest is unavailable in this scope.')
            manifest=json_value(v[0])
            if manifest['scope']!=scope:raise PermissionError('Window scope differs from host scope.')
            return manifest
    def save_manifest(self,manifest,scope=SCOPE):return self.save_event('context_manifest',manifest,scope)
    def isolation_proof(self):
        counts={}
        for tenant in ('acme','globex','tenant_acme'):
            with self.connection(dict(SCOPE,tenant_id=tenant)) as conn,conn.cursor() as cur:
                for table in BASE_TABLES+['CONTEXT_SOURCE_REF']:
                    cur.execute(f'SELECT DISTINCT tenant_id FROM {table}');assert {r[0] for r in cur}.issubset({tenant})
                cur.execute('SELECT COUNT(*) FROM entity_memory');counts[tenant]=cur.fetchone()[0]
                scn=self.capture_scn(cur);cur.execute('SELECT DISTINCT tenant_id FROM entity_memory AS OF SCN :s',s=scn);assert {r[0] for r in cur}.issubset({tenant})
        with self.pool.acquire() as conn,conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM entity_memory');counts['no_context']=cur.fetchone()[0];assert counts['no_context']==0
        return counts
