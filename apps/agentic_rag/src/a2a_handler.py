'''
A2A Protocol Handler

This module implements the core A2A (Agent2Agent) protocol handler that processes
JSON-RPC 2.0 requests and routes them to appropriate methods.
'''
import asyncio
import logging
import os
import yaml
from .a2a_models import A2AResponse, A2AError, DocumentUploadParams, AgentCard
from .task_manager import TaskManager
from .agent_registry import AgentRegistry
from .specialized_agent_cards import get_all_specialized_agent_cards, get_agent_card_by_id
from .reasoning.rag_ensemble import RAGReasoningEnsemble
from .reasoning_agent_cards import get_all_reasoning_agent_cards, get_reasoning_agent_card_by_id
logger = logging.getLogger(__name__)


class A2AHandler:
    '''Handler for A2A protocol requests'''

    def __init__(self, rag_agent, vector_store, event_logger=None):
        '''Initialize A2A handler with RAG agent and dependencies'''
        self.rag_agent = rag_agent
        self.vector_store = vector_store
        self.event_logger = event_logger
        self.task_manager = TaskManager()
        self.agent_registry = AgentRegistry()
        self.agent_endpoints = self._load_agent_endpoints()
        self._specialized_agents = {}
        self._reasoning_ensemble = None
        self.methods = {
            'document.query': self.handle_document_query,
            'document.upload': self.handle_document_upload,
            'agent.discover': self.handle_agent_discover,
            'agent.register': self.handle_agent_register,
            'agent.card': self.handle_agent_card,
            'agent.query': self.handle_agent_query,
            'task.create': self.handle_task_create,
            'task.status': self.handle_task_status,
            'task.cancel': self.handle_task_cancel,
            'health.check': self.handle_health_check,
            'reasoning.execute': self.handle_reasoning_execute,
            'reasoning.strategy': self.handle_reasoning_strategy,
            'reasoning.list': self.handle_reasoning_list,
        }
        self._self_registered = False
        self._specialized_agents_registered = False

    def _load_agent_endpoints(self):
        '''Load agent endpoint URLs from config'''
        default_url = os.getenv('A2A_BASE_URL', 'http://localhost:8000')
        try:
            from pathlib import Path
            config_paths = [
                Path("config.yaml"),
                Path(os.path.dirname(__file__)) / ".." / "config.yaml",
            ]
            for config_path in config_paths:
                if config_path.exists():
                    with open(config_path, "r") as f:
                        config = yaml.safe_load(f)
                    if config:
                        return {
                            'planner_url': config.get('PLANNER_URL', default_url),
                            'researcher_url': config.get('RESEARCHER_URL', default_url),
                            'reasoner_url': config.get('REASONER_URL', default_url),
                            'synthesizer_url': config.get('SYNTHESIZER_URL', default_url),
                        }
        except Exception as e:
            logger.warning(f'Failed to load agent endpoints from config: {e}')
        return {
            'planner_url': default_url,
            'researcher_url': default_url,
            'reasoner_url': default_url,
            'synthesizer_url': default_url,
        }

    def _load_specialized_agent_model(self):
        '''Load specialized agent model from config'''
        try:
            from pathlib import Path
            config_paths = [
                Path("config.yaml"),
                Path(os.path.dirname(__file__)) / ".." / "config.yaml",
            ]
            for config_path in config_paths:
                if config_path.exists():
                    with open(config_path, "r") as f:
                        config = yaml.safe_load(f)
                    if config:
                        return config.get('SPECIALIZED_AGENT_MODEL', 'qwen3.5:9b')
        except Exception as e:
            logger.warning(f'Failed to load specialized agent model from config: {e}')
        return 'qwen3.5:9b'

    def _get_reasoning_ensemble(self):
        '''Lazy initialize reasoning ensemble.'''
        if self._reasoning_ensemble is None:
            model = self._load_specialized_agent_model()
            self._reasoning_ensemble = RAGReasoningEnsemble(
                model_name=model,
                vector_store=self.vector_store,
                event_logger=self.event_logger,
            )
        return self._reasoning_ensemble

    def _register_self(self):
        '''Register this agent in the agent registry'''
        if self._self_registered:
            return
        try:
            from .agent_card import get_agent_card
            card_data = get_agent_card()
            agent_card = AgentCard(**card_data)
            self.agent_registry.register_agent(agent_card)
            self._self_registered = True
            logger.info('Registered self in agent registry')
        except Exception as e:
            logger.error(f'Failed to register self: {e}')

    def _register_specialized_agents(self):
        '''Register all specialized Chain of Thought agents'''
        if self._specialized_agents_registered:
            return
        try:
            # Register specialized CoT agents
            all_cards = get_all_specialized_agent_cards(self.agent_endpoints)
            for agent_id, card_data in all_cards.items():
                agent_card = AgentCard(**card_data)
                self.agent_registry.register_agent(agent_card)
                self._specialized_agents[agent_id] = card_data
                logger.info(f'Registered specialized agent: {agent_id}')

            # Register reasoning agents
            base_url = self.agent_endpoints.get('planner_url', os.getenv('A2A_BASE_URL', 'http://localhost:8000'))
            reasoning_cards = get_all_reasoning_agent_cards(base_url)
            for agent_id, card_data in reasoning_cards.items():
                agent_card = AgentCard(**card_data)
                self.agent_registry.register_agent(agent_card)
                logger.info(f'Registered reasoning agent: {agent_id}')

            self._specialized_agents_registered = True
        except Exception as e:
            logger.error(f'Failed to register specialized agents: {e}')

    async def handle_request(self, request):
        '''Handle incoming A2A request'''
        logger.info(f'Handling A2A request: {request.method}')
        if request.method not in self.methods:
            return A2AResponse(
                error=A2AError(code=-32601, message='Method not found').model_dump(),
                id=request.id,
            )
        try:
            result = await self.methods[request.method](request.params)
            return A2AResponse(result=result, id=request.id)
        except Exception as e:
            logger.error(f'Error handling request {request.method}: {e}')
            return A2AResponse(
                error=A2AError(code=-32603, message=str(e)).model_dump(),
                id=request.id,
            )

    async def handle_document_query(self, params):
        '''Handle document query requests'''
        import time
        start_time = time.time()
        try:
            query = params.get('query', '')
            collection = params.get('collection', None)
            use_cot = params.get('use_cot', False)
            max_results = params.get('max_results', 3)

            if not query:
                return {'error': 'Query is required'}

            result = await self.rag_agent.query(
                query,
                collection=collection,
                use_cot=use_cot,
                max_results=max_results,
            )
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f'Document query completed in {duration_ms:.0f}ms')

            if isinstance(result, dict):
                result['duration_ms'] = duration_ms
                return result

            return {
                'answer': str(result),
                'duration_ms': duration_ms,
            }
        except Exception as e:
            logger.error(f'Error in document query: {e}')
            return {'error': str(e)}

    async def handle_document_upload(self, params):
        '''Handle document upload requests'''
        try:
            upload_params = DocumentUploadParams(**params)
            document_type = upload_params.document_type
            content = upload_params.content
            metadata = upload_params.metadata

            result = await self.rag_agent.process_document(
                document_type=document_type,
                content=content,
                metadata=metadata,
            )
            return result if isinstance(result, dict) else {
                'status': 'success',
                'message': str(result),
            }
        except Exception as e:
            logger.error(f'Error in document upload: {e}')
            return {'error': str(e)}

    def _call_ollama_api(self, model, prompt, system_prompt=None):
        '''Call Ollama API directly for inference'''
        import requests
        ollama_host = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')
        url = f'{ollama_host}/api/generate'
        payload = {
            'model': model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': 0.7,
                'num_predict': 512,
            },
        }
        if system_prompt:
            payload['system'] = system_prompt
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json().get('response', '')
        except Exception as e:
            logger.error(f'Ollama API call failed: {e}')
            return f'Error calling Ollama API: {e}'

    def _get_specialized_agent_card(self, agent_id):
        '''Get the agent card for a specialized agent'''
        if agent_id in self._specialized_agents:
            return self._specialized_agents[agent_id]
        card = get_agent_card_by_id(agent_id, self.agent_endpoints)
        if card:
            self._specialized_agents[agent_id] = card
        return card

    async def handle_agent_query(self, params):
        '''Handle agent query requests - routes to specialized agents using Ollama API'''
        import time
        start_time = time.time()
        try:
            agent_id = params.get('agent_id', '')
            query = params.get('query', '')
            step = params.get('step', '')
            context = params.get('context', [])
            reasoning_steps = params.get('reasoning_steps', [])

            if not agent_id or not query:
                return {'error': 'agent_id and query are required'}

            # Ensure specialized agents are registered
            if not self._specialized_agents_registered:
                self._register_specialized_agents()

            agent_card = self._get_specialized_agent_card(agent_id)
            if not agent_card:
                return {'error': f'Agent {agent_id} not found'}

            # Build system prompt from agent card metadata
            metadata = agent_card.get('metadata', {})
            role = metadata.get('role', 'Assistant')
            personality = metadata.get('personality', 'helpful')
            system_prompt = f'You are {role}. Your personality is {personality}. Respond concisely and helpfully.'

            # Build the user prompt based on agent type
            if step:
                user_prompt = f'Query: {query}\nStep to process: {step}'
            elif reasoning_steps:
                user_prompt = f'Query: {query}\nReasoning steps to synthesize:\n' + '\n'.join(
                    f'- {s}' for s in reasoning_steps
                )
            else:
                user_prompt = query

            if context:
                context_str = '\n'.join(str(c) for c in context)
                user_prompt += f'\n\nContext:\n{context_str}'

            # Call Ollama API
            model = self._load_specialized_agent_model()
            loop = asyncio.get_event_loop()
            response_text = await loop.run_in_executor(
                None, lambda: self._call_ollama_api(model, user_prompt, system_prompt)
            )

            duration_ms = (time.time() - start_time) * 1000
            logger.info(f'Agent query to {agent_id} completed in {duration_ms:.0f}ms')

            if self.event_logger:
                self.event_logger.log_a2a_event(
                    agent_id=agent_id,
                    agent_name=agent_card.get('name', agent_id),
                    method='agent.query',
                    user_prompt=query,
                    response=response_text[:500],
                    metadata={'step': step},
                    duration_ms=duration_ms,
                    status='success',
                )

            # Build response with agent-type-specific keys for frontend compatibility
            result_data = {
                'response': response_text,
                'agent_id': agent_id,
                'duration_ms': duration_ms,
            }
            # Map response into the keys the Gradio frontend expects per agent role
            if 'planner' in agent_id:
                result_data['plan'] = response_text
                result_data['steps'] = [s.strip() for s in response_text.split('\n') if s.strip()]
            elif 'researcher' in agent_id:
                # Query vector store for actual findings
                try:
                    search_query = step if step else query
                    # OraDBVectorStore has no generic .query(); default to the PDF collection
                    vs_results = (
                        self.vector_store.query_pdf_collection(search_query, n_results=3)
                        if self.vector_store else []
                    )
                    findings = []
                    for doc in vs_results:
                        findings.append({
                            'content': doc.get('content', ''),
                            'metadata': doc.get('metadata', {}),
                            'score': doc.get('score', 0),
                        })
                    result_data['findings'] = findings
                except Exception as vs_err:
                    logger.warning(f'Vector search in researcher failed: {vs_err}')
                    result_data['findings'] = []
            elif 'reasoner' in agent_id:
                result_data['conclusion'] = response_text
            elif 'synthesizer' in agent_id:
                result_data['answer'] = response_text
            return result_data
        except Exception as e:
            logger.error(f'Error in agent query: {e}')
            return {'error': str(e)}

    async def handle_agent_discover(self, params):
        '''Handle agent discovery requests'''
        try:
            if not self._self_registered:
                self._register_self()
            if not self._specialized_agents_registered:
                self._register_specialized_agents()

            capability = params.get('capability', None)
            agent_id = params.get('agent_id', None)

            if agent_id:
                agent = self.agent_registry.get_agent(agent_id)
                if agent:
                    return {'agents': [agent.model_dump()]}
                return {'agents': []}

            agents = self.agent_registry.discover_agents(capability=capability)
            return {'agents': [a.model_dump() for a in agents]}
        except Exception as e:
            logger.error(f'Error in agent discover: {e}')
            return {'error': str(e)}

    async def handle_agent_register(self, params):
        '''Handle agent registration requests'''
        try:
            agent_card = AgentCard(**params)
            success = self.agent_registry.register_agent(agent_card)
            return {
                'status': 'registered' if success else 'failed',
                'agent_id': agent_card.agent_id,
            }
        except Exception as e:
            logger.error(f'Error in agent register: {e}')
            return {'error': str(e)}

    async def handle_agent_card(self, params):
        '''Handle agent card requests'''
        from .agent_card import get_agent_card
        return get_agent_card()

    async def handle_reasoning_execute(self, params):
        '''Handle reasoning.execute requests - run ensemble with voting.'''
        import time
        start_time = time.time()
        query = params.get('query', '')
        strategies = params.get('strategies', ['cot'])
        use_rag = params.get('use_rag', True)
        collection = params.get('collection', 'PDF')
        config = params.get('config', {})
        if not query:
            return {'error': 'Query is required'}
        try:
            ensemble = self._get_reasoning_ensemble()
            result = await ensemble.run(
                query=query,
                strategies=strategies,
                use_rag=use_rag,
                collection=collection,
                config=config,
            )
            duration_ms = (time.time() - start_time) * 1000
            winner_strategy = result.winner.get('strategy', 'unknown')
            winner_response = result.winner.get('response', '')
            logger.info(f'Final Answer [{winner_strategy}] ({duration_ms:.0f}ms): {winner_response[:500]}')
            if self.event_logger:
                self.event_logger.log_a2a_event(
                    agent_id='reasoning_ensemble_v1',
                    agent_name='Reasoning Ensemble',
                    method='reasoning.execute',
                    user_prompt=query,
                    response=winner_response,
                    metadata={
                        'strategies': strategies,
                        'winner': winner_strategy,
                        'use_rag': use_rag,
                    },
                    duration_ms=duration_ms,
                    status='success',
                )
            return {
                'winner': result.winner,
                'all_responses': result.all_responses,
                'execution_trace': [
                    {
                        'timestamp': e.timestamp,
                        'type': e.event_type,
                        'message': e.message,
                    }
                    for e in result.execution_trace
                ],
                'rag_context': result.rag_context,
                'total_duration_ms': result.total_duration_ms,
                'voting_details': result.voting_details,
            }
        except Exception as e:
            logger.error(f'Error in reasoning execute: {e}')
            return {'error': str(e)}

    async def handle_reasoning_strategy(self, params):
        '''Handle reasoning.strategy requests - run single strategy.'''
        query = params.get('query', '')
        strategy = params.get('strategy', 'cot')
        config = params.get('config', {})
        if not query:
            return {'error': 'Query is required'}
        try:
            ensemble = self._get_reasoning_ensemble()
            result = await ensemble.run(
                query=query,
                strategies=[strategy],
                use_rag=False,
                config={strategy: config} if config else None,
            )
            return {
                'strategy': strategy,
                'response': result.winner['response'],
                'duration_ms': result.total_duration_ms,
            }
        except Exception as e:
            logger.error(f'Error in reasoning strategy: {e}')
            return {'error': str(e)}

    async def handle_reasoning_list(self, params):
        '''Handle reasoning.list requests - list available strategies.'''
        ensemble = self._get_reasoning_ensemble()
        strategies = ensemble.available_strategies
        return {
            'strategies': strategies,
            'count': len(strategies),
            'details': [
                {
                    'key': s,
                    'card': get_reasoning_agent_card_by_id(f'reasoning_{s}_v1'),
                }
                for s in strategies
            ],
        }

    async def handle_task_create(self, params):
        '''Handle task creation requests'''
        try:
            task_type = params.get('task_type', '')
            task_params = params.get('params', {})
            task_id = await self.task_manager.create_task(task_type, task_params)
            return {
                'task_id': task_id,
                'status': 'pending',
                'message': f'Task {task_id} created successfully',
            }
        except Exception as e:
            logger.error(f'Error creating task: {e}')
            return {'error': str(e)}

    async def handle_task_status(self, params):
        '''Handle task status requests'''
        try:
            task_id = params.get('task_id', '')
            if not task_id:
                return {'error': 'task_id is required'}
            task_info = self.task_manager.get_task_status(task_id)
            if not task_info:
                return {'error': f'Task {task_id} not found'}
            return {
                'task_id': task_info.task_id,
                'status': task_info.status.value,
                'result': task_info.result,
                'error': task_info.error,
                'progress': task_info.progress,
            }
        except Exception as e:
            logger.error(f'Error checking task status: {e}')
            return {'error': str(e)}

    async def handle_task_cancel(self, params):
        '''Handle task cancellation requests'''
        try:
            task_id = params.get('task_id', '')
            if not task_id:
                return {'error': 'task_id is required'}
            success = self.task_manager.cancel_task(task_id)
            return {
                'task_id': task_id,
                'cancelled': success,
                'message': f'Task {task_id} {"cancelled" if success else "could not be cancelled"}',
            }
        except Exception as e:
            logger.error(f'Error cancelling task: {e}')
            return {'error': str(e)}

    async def handle_health_check(self, params):
        '''Handle health check requests'''
        return {
            'status': 'healthy',
            'timestamp': asyncio.get_event_loop().time(),
            'version': '1.0.0',
            'capabilities': list(self.methods.keys()),
        }
