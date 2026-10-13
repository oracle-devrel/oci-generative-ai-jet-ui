"""Integration checks exercise Oracle, assembly, replay, and FastMCP."""
import asyncio,json
from datetime import datetime,timedelta
from pathlib import Path
from xml.etree import ElementTree
from copy import deepcopy
from config import SCOPE,AS_OF,QUESTION,QUESTION_1,dumps,BUDGET
from store import OracleStore,ReplayUnavailable
from manager import MemoryManager
from assembly import ref,render,count_tokens,BudgetError,assemble,select
from replay import replay_base_window
from mcp_client import smoke,session,unpack

def database_checks(store):
    manager=MemoryManager(store);w=manager.build_window();m=w['manifest']
    inventories=[]
    for tenant in ('tenant_acme','acme'):
        with store.connection(dict(SCOPE,tenant_id=tenant)) as conn,conn.cursor() as cur:
            cur.execute("SELECT JSON_VALUE(d.metadata,'$.doc_key'),c.chunk_index,c.content FROM knowledge_base_chunk c JOIN knowledge_base_document d ON d.id=c.document_id WHERE d.collection IN ('ingested-papers','vendor-docs') ORDER BY 1,2")
            inventories.append(cur.fetchall())
    assert inventories[0]==inventories[1] and len(inventories[0])==137
    rows=store.current_rows();fact=next(r for r in rows if r['kind']=='entity' and r['meta'].get('subject')=='model:helios-rag' and r['version']==2)
    assert ref(fact) in m['required_refs']
    assert next(b for b in w['memories'] if b['ref']==ref(fact))['tier']=='full'
    assert '0.78' in dumps(w['request'])
    # Prompt records expose citation semantics while database references remain in the manifest.
    records = {b['id']: ElementTree.fromstring(b['text']) for b in w['memories']}
    for memory in w['memories']:
        record = records[memory['id']]
        assert record.tag == 'memory'
        assert record.attrib == {'id': memory['id'], 'type': memory['type'], 'status': memory['status']}
        assert record.find('content') is not None
    july = next(b for b in w['memories'] if b['ref'][1] == 'context_july_summary')
    july_record = records[july['id']]
    assert july_record.attrib['status'] == 'historical'
    assert '0.92' in july_record.find('content').text
    annotation = july_record.find('annotation')
    assert '0.78' in annotation.text
    assert records[annotation.attrib['current_fact_id']].attrib['status'] == 'current'
    assert w['request']['input'][0]['role'] == 'developer'
    assert '[B331ec01f36]' in w['request']['input'][0]['content']
    assert '<memory_context>' in w['request']['input'][1]['content']

    assert all(s not in dumps(w['request']) for s in ['GLOBEX_PRIVATE_SENTINEL','PRIVATE_USER_SENTINEL','PRIVATE_THREAD_SENTINEL','FUTURE_SENTINEL','DELETED_SENTINEL'])
    assert any(r['kind']=='persona' and r['version'] is None for r in rows)
    assert all(r['version'] is None for r in rows if r['kind']=='kb')
    comparison=manager.build_window(question=QUESTION_1,intent='comparison')
    assert any('Letta' in b['text'] for b in comparison['memories'])
    assert any('Amazon' in b['text'] or 'AgentCore' in b['text'] for b in comparison['memories'])
    replay=replay_base_window(store,w)
    assert replay['hash_matches']
    # AS OF reads recover changed bytes, but deletion of an annotation-only source blocks replay.
    old=next(r for r in rows if r['kind']=='entity' and r['meta'].get('subject')=='model:helios-rag' and r['version']==1)
    assert ref(old) in m['dependencies'] and ref(old) not in [b['ref'] for b in w['memories']]
    with store.connection() as conn,conn.cursor() as cur:
        cur.execute('UPDATE entity_memory SET deleted_at=:at WHERE id=:id',at=AS_OF,id=old['id']);conn.commit()
    try:
        try:replay_base_window(store,w)
        except ReplayUnavailable:pass
        else:raise AssertionError('Deleted annotation dependency replayed')
        historical=store.replay_rows(m['scn'],SCOPE,QUESTION,recorded_scores=m['candidate_scores'])
        assert next(r for r in historical if r['id']==old['id'])['deleted_at'] is None
    finally:
        with store.connection() as conn,conn.cursor() as cur:cur.execute('UPDATE entity_memory SET deleted_at=NULL WHERE id=:id',id=old['id']);conn.commit()
    # Actual stored embedding follows corrected source text.
    with store.connection() as conn,conn.cursor() as cur:
        cur.execute('SELECT VECTOR_DISTANCE(embedding,VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :new AS DATA),COSINE),VECTOR_DISTANCE(embedding,VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :old AS DATA),COSINE) FROM entity_memory WHERE id=:id',new=fact['content'],old=old['content'],id=fact['id']);distances=[float(x) for x in cur.fetchone()];assert distances[0]<distances[1]
        # VPD rejects a write whose tenant disagrees with trusted context.
        try:cur.execute("INSERT INTO deletion_events(tenant_id,scope,deleted_at,reason) VALUES('globex','tenant',SYSTIMESTAMP,'isolation-test')")
        except Exception as e:assert e.args[0].code==28115
        else:raise AssertionError('VPD accepted cross-tenant write')
        conn.rollback()
    manager.issue_window(w)
    expand_id=next(r['id'] for r in manager.active_toolbox() if r['meta']['name']=='expand')
    validhandle=w['memories'][0]['id'];assert manager.invoke('expand',{'memory_id':validhandle})['status']=='found'
    # A versioned tool row can be retired after discovery; the manager rechecks it.
    assert any(r['meta']['name']=='expand' for r in manager.active_toolbox())
    with store.connection() as conn,conn.cursor() as cur:cur.execute('UPDATE toolbox_memory SET valid_until=:at WHERE id=:id',at=datetime.utcnow(),id=expand_id);conn.commit()
    try:
        try:manager.invoke('expand',{'memory_id':validhandle})
        except PermissionError:pass
        else:raise AssertionError('Retired tool remained callable')
    finally:
        with store.connection() as conn,conn.cursor() as cur:cur.execute('UPDATE toolbox_memory SET valid_until=NULL WHERE id=:id',id=expand_id);conn.commit()
    try:
        with store.connection(dict(SCOPE,tenant_id='globex')):raise RuntimeError('context cleanup check')
    except RuntimeError:pass
    with store.pool.acquire() as conn,conn.cursor() as cur:
        cur.execute("SELECT SYS_CONTEXT('memory_ctx','tenant_id') FROM dual");assert cur.fetchone()[0] is None
    # Tools use present validity, independently of the recorded assembly evaluation time.
    clock_row={'id':'context_clock_test',**SCOPE,'subject':'model:helios-rag','predicate':'beir_ndcg10','content':'Temporal authorization check.','content_hash':'clock-test','confidence':1,'source_event_id':'context_clock_test','version':99,'valid_from':datetime.utcnow()-timedelta(seconds=1),'created_at':datetime.utcnow(),'written_by':'admin:acme'}
    store.insert('ENTITY_MEMORY',clock_row)
    try:assert manager.invoke('lookup_entity',{'subject':'model:helios-rag','predicate':'beir_ndcg10'})['items'][0]['version']==99
    finally:
        with store.connection() as conn,conn.cursor() as cur:cur.execute("DELETE FROM entity_memory WHERE id='context_clock_test'");conn.commit()
    # A temporary, manually authored derived row verifies a non-default tenant write.
    from config import row
    globex=dict(SCOPE,tenant_id='globex')
    test_comp=row('compression','context_globex_compression_check','Manual integration check.',**globex,meta={'source_refs':[['entity','context_globex',1]],'source_ancestors':[],'source_hash':'test-only','model':'manual-integration-test','origin':'test','prompt_version':'scope-check'})
    store.put(test_comp)
    try:
        assert any(r['id']==test_comp['id'] for r in store.compression_rows(globex))
        assert not any(r['id']==test_comp['id'] for r in store.compression_rows(SCOPE))
    finally:
        with store.connection(globex) as conn,conn.cursor() as cur:
            cur.execute('DELETE FROM context_compression WHERE id=:id',id=test_comp['id'])
            cur.execute("DELETE FROM context_source_ref WHERE derived_kind='compression' AND derived_id=:id",id=test_comp['id']);conn.commit()
    # Fixed slices and cumulative tool results fail explicitly when over budget.
    too_small=deepcopy(BUDGET);too_small['usable_context']=100
    try:manager.build_window(policy=too_small)
    except BudgetError:pass
    else:raise AssertionError('Oversized fixed slices accepted')
    from assembly import LoopBudget
    loop_policy=deepcopy(BUDGET);loop_policy['max_rounds']=1
    loop=LoopBudget(loop_policy);loop.add(fact)
    try:loop.add(fact)
    except BudgetError:pass
    else:raise AssertionError('Tool-round limit ignored')
    # Guideline updates retire the old version and insert the new one atomically.
    first=manager.write_guideline(guideline_key='context_version_test',guideline_value={'n':1},written_by='admin:acme',source_event_id='context_version_test')
    try:
        second=manager.write_guideline(guideline_key='context_version_test',guideline_value={'n':2},written_by='admin:acme',source_event_id='context_version_test')
        with store.connection() as conn,conn.cursor() as cur:
            cur.execute("SELECT version,valid_until FROM guideline_memory WHERE guideline_key='context_version_test' ORDER BY version")
            versions=cur.fetchall();assert int(versions[1][0])==int(versions[0][0])+1 and versions[0][1] is not None and versions[1][1] is None
    finally:
        with store.connection() as conn,conn.cursor() as cur:cur.execute("DELETE FROM guideline_memory WHERE guideline_key='context_version_test' AND source_event_id='context_version_test'");conn.commit()
    # Controlled admission ablation: the default rejects the same impossible canonical budget.
    policy=deepcopy(BUDGET);policy['shares']['fact_check']={'durable_facts':0,'evidence':0,'recalled_history':1,'volatile_tail':0};policy['overflow_order']=['durable_facts','recalled_history','volatile_tail','evidence']
    scn,candidates=store.snapshot();
    try:assemble(candidates,SCOPE,policy=policy,scn=scn)
    except BudgetError:pass
    else:raise AssertionError('Required canonical fact silently dropped')
    ablation=manager.build_window(policy=policy,admit_current=False)
    ablation['manifest']['experiment']='disable_current_admission_and_zero_durable_budget'
    Path('results').mkdir(exist_ok=True)
    Path('results/admission_ablation.json').write_text(json.dumps(json.loads(dumps(ablation)),indent=2)+'\n')
    assert ref(fact) not in [b['ref'] for b in ablation['memories']]
    # Same real candidates, different budget creates pointers; no synthetic retrieval score.
    pointer_policy=deepcopy(BUDGET)
    pointer_policy['shares']['comparison']={'durable_facts':.665,'evidence':.035,'recalled_history':.1,'volatile_tail':.2}
    pointer=manager.build_window(question=QUESTION_1,intent='comparison',policy=pointer_policy)
    assert any(b['tier']=='pointer' for b in pointer['memories'])
    with store.connection() as conn:db_version=conn.version
    return {'database_version':db_version,'isolation':store.isolation_proof(),'request_hash':m['request_hash'],'local_text_tokens':m['local_text_tokens'],'corrected_fact_required':True,'full_research_corpus_preserved':True,'guideline_version_update':True,'fixed_and_loop_budget_failures':True,'historical_dependency_deletion_blocks_replay':True,'flashback_recovers_pre_deletion_bytes':True,'embedding_distance_current_vs_old':distances,'active_tool_rechecked':True,'tool_authorization_uses_present_time':True,'derived_write_nondefault_tenant':True,'valid_pointer_expands':True,'required_fact_budget_failure':True,'controlled_ablation_omits_current':True,'comparison_includes_both_sources':True,'replay':replay},w,comparison
async def protocol_checks(window=None):
    results=[]
    for mode in ('legacy','2026-07-28'):
        for action in ('accept','decline','cancel',None):results.append(await smoke(action,mode))
    async with session() as client:
        result=unpack(await client.call_tool('search_memory',{'query':'How long does AgentCore retain raw session events?'}))
        assert result['retrieval']=='vector+OracleText+RRF+BGE_RERANKER'
        assert any('retention' in x['content'].lower() or 'expiry' in x['content'].lower() for x in result['items'])
        results.append({'genuinely_missing_detail':'AgentCore retention fetched from a Helios-only window','items':len(result['items'])})
    if window:
        async with session(window=window) as client:
            memory_id=window['memories'][0]['id']
            expanded=unpack(await client.call_tool('expand',{'memory_id':memory_id}))
            assert expanded['status']=='found'
            old_name=await client.call_tool('expand',{'block_id':memory_id},raise_on_error=False)
            assert old_name.is_error and old_name.structured_content['code']=='invalid_arguments'
            results.append({'memory_id_expands':True,'old_parameter_rejected':True})
    return results
async def main():
    store=OracleStore()
    try:
        result,w,c=database_checks(store);result['fastmcp']=await protocol_checks(w)
        Path('results').mkdir(exist_ok=True)
        for name,value in [('verification.json',result),('fact_check_window.json',w),('comparison_window.json',c)]:Path('results',name).write_text(json.dumps(json.loads(dumps(value)),indent=2)+'\n')
        print(json.dumps(result,indent=2))
    finally:store.close()
if __name__=='__main__':asyncio.run(main())
