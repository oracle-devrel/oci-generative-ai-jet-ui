"""Optional live model experiments; records provider results without assuming success."""
import asyncio,json,re,os
from copy import deepcopy
from pathlib import Path
from config import SCOPE,QUESTION,QUESTION_1,BUDGET,dumps
from store import OracleStore
from manager import MemoryManager
from assembly import select,render,count_tokens,check_compression,BudgetError,ref
from replay import replay_base_window
from live_model import run_live,generate_compression
async def main():
    store=OracleStore();manager=MemoryManager(store);out={}
    try:
        _,rows=store.snapshot(question=QUESTION_1)
        candidates,_=select(rows,SCOPE)
        source=next(r for r in candidates if r['kind']=='kb')
        comp=await generate_compression(source,manager)
        check_compression(comp,source,SCOPE,__import__('config').AS_OF)
        rejected=deepcopy(source);rejected['content_hash']='changed'
        try:check_compression(comp,rejected,SCOPE,__import__('config').AS_OF)
        except ValueError:pass
        else:raise AssertionError('Mismatched compression accepted')
        summary_cost=render(source,'summary',comp)['tokens'];full_cost=render(source)['tokens']
        if summary_cost>=full_cost:raise RuntimeError('Model compression did not reduce this memory; choose a longer source.')
        baseline=manager.build_window(question=QUESTION_1,intent='comparison')
        available=baseline['manifest']['allocation']['evidence']['base']/.6
        share=(summary_cost+full_cost)/2/available
        policy=deepcopy(BUDGET);policy['shares']['comparison']={'evidence':share,'durable_facts':.95-share,'recalled_history':.025,'volatile_tail':.025}
        compressed=manager.build_window(question=QUESTION_1,intent='comparison',policy=policy,compressions={tuple(ref(source)):comp})
        assert any(b['tier']=='summary' and b['ref']==ref(source) for b in compressed['memories'])
        out['compression']={'source_ref':ref(source),'compression_ref':ref(comp),'full_tokens':full_cost,'summary_tokens':summary_cost,'replay':replay_base_window(store,compressed),'mismatched_source_rejected':True}
        parent=source['meta']['parent_ref']
        cascade=store.erase_derived([parent],commit=False)
        assert ['compression',comp['id']] in cascade['affected_refs'] and cascade['deleted_compressions']>0
        assert store.source_available(ref(comp))
        out['compression']['parent_document_cascade_checked']=True
        out['compression']['cascade_test_rolled_back']=True
        Path('results/compressed_window.json').write_text(json.dumps(json.loads(dumps(compressed)),indent=2)+'\n')
        for name,question,intent in [('fact_check',QUESTION,'fact_check'),('comparison',QUESTION_1,'comparison')]:
            window=manager.build_window(question=question,intent=intent,model=os.environ['OPENAI_MODEL'])
            result=await run_live(window,manager)
            answer=result.get('answer') or ''
            citations=re.findall(r'\bB[0-9a-f]{10}\b',answer)
            result['evaluation']={'corrected_value_present':('0.78' in answer) if name=='fact_check' else None,'memory_citations_present':bool(citations),'citation_ids':citations,'note':'Presence checks; comparative claims and citation support need editorial review.'}
            out[name]=result
        # A narrow evidence slice cannot hold the newly relevant retention paragraph.
        # The canonical correction remains required; only optional evidence is omitted.
        followup='How long does AgentCore retain raw session events? Fetch the retention policy and cite the result.'
        fetch_policy=deepcopy(BUDGET)
        fetch_policy['shares']['fact_check']={'durable_facts':.65,'evidence':0,'recalled_history':.1,'volatile_tail':.25}
        window=manager.build_window(question=followup,policy=fetch_policy,model=os.environ['OPENAI_MODEL'])
        assert not any(b['slice']=='evidence' for b in window['memories'])
        out['missing_detail']=await run_live(window,manager)
        Path('results/model_verification.json').write_text(json.dumps(json.loads(dumps(out)),indent=2)+'\n')
        print(json.dumps(out,indent=2))
    finally:store.close()
def revalidate_stored_compression(store,record):
    """Reconstruct with retained model text after backend changes; makes no model call."""
    from manager import MemoryManager
    from assembly import render,ref
    for result in record.values():
        evaluation=result.get('evaluation', {})
        if 'block_citations_present' in evaluation:
            evaluation['memory_citations_present']=evaluation.pop('block_citations_present')
    model=record['compression'];comp=next(r for r in store.compression_rows() if ref(r)==model['compression_ref'])
    _,rows=store.snapshot(question=QUESTION_1);source=next(r for r in rows if ref(r)==model['source_ref'])
    manager=MemoryManager(store);baseline=manager.build_window(question=QUESTION_1,intent='comparison')
    available=baseline['manifest']['allocation']['evidence']['base']/.6
    share=(render(source,'summary',comp)['tokens']+render(source)['tokens'])/2/available
    policy=deepcopy(BUDGET);policy['shares']['comparison']={'evidence':share,'durable_facts':.95-share,'recalled_history':.025,'volatile_tail':.025}
    window=manager.build_window(question=QUESTION_1,intent='comparison',policy=policy,compressions={tuple(ref(source)):comp})
    assert any(b['tier']=='summary' and b['ref']==ref(source) for b in window['memories'])
    record['compression']['replay']=replay_base_window(store,window)
    record['compression']['retained_text_revalidated']=True
    Path('results/compressed_window.json').write_text(json.dumps(json.loads(dumps(window)),indent=2)+'\n')
    Path('results/model_verification.json').write_text(json.dumps(json.loads(dumps(record)),indent=2)+'\n')
    return record
if __name__=='__main__':asyncio.run(main())
