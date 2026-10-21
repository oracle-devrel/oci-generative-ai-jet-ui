"""FastMCP Client stdio round trips with real Oracle reads."""
import os,sys,json
from pathlib import Path
from contextlib import asynccontextmanager
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.client.elicitation import ElicitResult
@asynccontextmanager
async def session(mode='oracle',elicitation_action='accept',scope=None,connect_mode='legacy',window=None):
    if mode!='oracle':raise ValueError('The example requires Oracle; no fixture mode is provided.')
    env=dict(os.environ)
    if window:env["CONTEXT_WINDOW_EVENT"]=window["manifest_event_id"]
    if scope:env.update({'CONTEXT_'+k.upper():v for k,v in scope.items()})
    async def handler(message,response_type,params,context):
        # Legacy ctx.elicit(list[str]) uses a value field; the guard uses workload.
        key='workload' if 'workload' in params.requested_schema['properties'] else 'value'
        return ElicitResult(action=elicitation_action,content={key:'research'} if elicitation_action=='accept' else None)
    transport=StdioTransport(command=sys.executable,args=[str(Path(__file__).with_name('mcp_server.py'))],env=env,keep_alive=False)
    async with Client(transport,elicitation_handler=handler if elicitation_action else None,mode=connect_mode,cache=False,timeout=120) as client:yield client
def unpack(result):
    if result.is_error:raise RuntimeError('MCP tool failed: '+str(result.content))
    if result.structured_content:return result.structured_content
    return json.loads(next(c.text for c in result.content if c.type=='text'))
async def smoke(action='accept',connect_mode='legacy'):
    async with session(elicitation_action=action,connect_mode=connect_mode) as client:
        tools=await client.list_tools()
        names=sorted(t.name for t in tools)
        expand=next(t for t in tools if t.name=='expand')
        assert set(expand.input_schema['properties'])=={'memory_id'}
        assert expand.input_schema['required']==['memory_id']
        found=unpack(await client.call_tool('lookup_entity',{'subject':'model:helios-rag','predicate':'beir_ndcg10'}))
        assert found['items'][0]['version']==2 and '0.78' in found['items'][0]['content']
        denied=await client.call_tool('lookup_entity',{'subject':'model:helios-rag','predicate':'beir_ndcg10','tenant_id':'globex'},raise_on_error=False);assert denied.is_error and denied.structured_content["code"]=="invalid_arguments"
        guessed=await client.call_tool('expand',{'memory_id':'guessed'},raise_on_error=False);assert guessed.is_error and guessed.structured_content["code"]=="access_denied"
        answer=unpack(await client.call_tool('clarify',{'question':'Which workload do you mean?'}))
        assert answer['status']==(action or 'needs_user'),answer
        return {'tools':names,'lookup_version':2,'tenant_override_rejected':True,'guessed_handle_rejected':True,'elicitation':answer['status'],'connection':connect_mode}
