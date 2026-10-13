"""FastMCP stdio server. One process belongs to one trusted host scope.
Remote deployments must authenticate requests before constructing the manager.
"""
import os
from pydantic import PrivateAttr
from jsonschema.exceptions import ValidationError as ArgumentValidationError
from fastmcp import FastMCP
from fastmcp.server.providers import Provider
from fastmcp.server.dependencies import get_context
from fastmcp.tools import Tool,ToolResult
from fastmcp.tools.base import InputRequiredToolResult
from mcp.types import InputRequiredResult,ElicitRequest,ElicitRequestFormParams
from config import SCOPE
from manager import MemoryManager
from store import OracleStore

FORM={'type':'object','properties':{'workload':{'type':'string','enum':['research','support']}},'required':['workload']}
class RegistryTool(Tool):
    _manager:MemoryManager=PrivateAttr()
    def __init__(self,entry,manager):
        super().__init__(name=entry['meta']['name'],description=entry['content'],parameters=entry['meta']['inputSchema'])
        self._manager=manager
    async def run(self,arguments):
        try:
            return await self._dispatch(arguments)
        except ArgumentValidationError:
            return self._rejection('invalid_arguments','Arguments do not match the active tool schema.')
        except PermissionError as error:
            return self._rejection('access_denied',str(error))
    @staticmethod
    def _rejection(code,message):
        error={'status':'rejected','code':code,'message':message}
        return ToolResult(content=error,structured_content=error,is_error=True)
    async def _dispatch(self,arguments):
        manager=self._manager
        manager.authorize(self.name,arguments)
        if self.name!='clarify':return ToolResult(content=manager.invoke(self.name,arguments))
        ctx=get_context()
        if ctx.input_responses:
            answer=ctx.input_responses['workload']
            result={'status':answer.action,'content':answer.content if answer.action=='accept' else None}
        else:
            # Handshake clients have a server-initiated elicitation channel.
            if ctx.request_context.protocol_version < '2026-07-28':
                caps=ctx.session.client_params.capabilities.elicitation
                if caps is None or caps.form is None:result={'status':'needs_user','question':arguments['question']}
                else:
                    answer=await ctx.elicit(arguments['question'],['research','support'])
                    result={'status':answer.action,'content':{'workload':answer.data} if answer.action=='accept' else None}
            else:
                # Stateless 2026-07-28 clients supply input on a subsequent leg.
                caps=ctx.session.client_params.capabilities.elicitation if ctx.session.client_params else None
                if caps is None or caps.form is None:result={'status':'needs_user','question':arguments['question']}
                else:return InputRequiredToolResult(InputRequiredResult(inputRequests={'workload':ElicitRequest(params=ElicitRequestFormParams(message=arguments['question'],requested_schema=FORM))}))
        eid=manager.store.save_event('tool_result',result,manager.scope)
        result['event_refs']=[['conversation',eid,None]]
        return ToolResult(content=result)
class ToolboxProvider(Provider):
    def __init__(self,manager):super().__init__();self.manager=manager
    async def _list_tools(self):return [RegistryTool(r,self.manager) for r in self.manager.active_toolbox()]
def make_server(manager):return FastMCP('context-assembly-memory',providers=[ToolboxProvider(manager)],strict_input_validation=True)
def main():
    scope={k:os.getenv('CONTEXT_'+k.upper(),v) for k,v in SCOPE.items()}
    store=OracleStore();manager=MemoryManager(store,scope)
    window_event=os.getenv('CONTEXT_WINDOW_EVENT')
    if window_event:
        manifest=store.load_manifest(window_event,scope)
        manager.issue_window({'manifest':manifest,'memories':manifest['memories']})
    else:manager.build_window()
    try:make_server(manager).run(transport='stdio',show_banner=False)
    finally:store.close()
if __name__=='__main__':main()
