"""Replay retained source bytes and recorded ranking, subject to present authorization."""
from datetime import datetime
from assembly import RENDERER_VERSION,SELECTION_VERSION,assemble,ref,code_hash
from store import ReplayUnavailable

def replay_base_window(store,window):
    m=window['manifest'];scope=m['scope']
    if m['round']!=0:raise ReplayUnavailable('Tool-round replay also needs the retained provider transcript.')
    if m['renderer_version']!=RENDERER_VERSION or m['selection_version']!=SELECTION_VERSION:raise ReplayUnavailable('Recorded code version unavailable.')
    if m['code_hash']!=code_hash():raise ReplayUnavailable('Recorded assembler code differs from the installed code.')
    for dep in m['dependencies']:
        if not store.source_available(dep,scope):raise ReplayUnavailable('Source dependency was deleted or is no longer authorized.')
    derived={tuple(ref(r)):r for r in store.compression_rows(scope)};comps={}
    for b in m['memories']:
        if b['compression_ref']:
            comp=derived.get(tuple(b['compression_ref']))
            if not comp or comp['deleted_at']:raise ReplayUnavailable('Stored compression unavailable.')
            comps[tuple(b['ref'])]=comp
    question=store.read_question(m['question_ref'],m['scn'],scope)
    rows=store.replay_rows(m['scn'],scope,question,recorded_scores=m['candidate_scores'])
    w=assemble(rows,scope,policy=window['policy'],at=datetime.fromisoformat(m['evaluation_time']),intent=m['intent'],scn=m['scn'],model=m['model'],compressions=comps,mode=m['mode'],admit_current=m['admit_current'],required_refs=m['required_refs'])
    if w['manifest']['request_hash']!=m['request_hash']:raise ReplayUnavailable('Reconstructed request hash differs.')
    return {'hash_matches':True,'request_hash':m['request_hash'],'scn':m['scn'],'scores':'recorded','authorization':'current'}
