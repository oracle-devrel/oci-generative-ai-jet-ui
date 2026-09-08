"""
OpenAI-compatible API layer for Open WebUI integration.

This module provides /v1/models and /v1/chat/completions endpoints
that are compatible with the OpenAI API specification, allowing
Open WebUI and other OpenAI-compatible clients to consume our
reasoning and RAG capabilities.

Now uses ReasoningInterceptor directly (like CLI arena mode) for
full multi-step streaming output from reasoning agents with real-time
chunk-by-chunk streaming.
"""
import json
import time
import uuid
import asyncio
import re
import os
import queue
import threading
from pathlib import Path
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

try:
    from agent_reasoning import ReasoningInterceptor
    INTERCEPTOR_AVAILABLE = True
except ImportError:
    INTERCEPTOR_AVAILABLE = False

from .openai_models import (  # noqa: E402
    ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChoice,
    ChatMessage, ModelList, ModelInfo, UsageInfo, get_model_list, get_model_config
)
from .web_processor import WebProcessor, is_url  # noqa: E402

router = APIRouter(prefix='/v1', tags=['OpenAI Compatible'])

_vector_store = None
_reasoning_ensemble = None
_local_agent = None
_config = {}
_interceptor = None
_event_logger = None
_file_handler = None
_a2a_handler = None


def init_openai_compat(vector_store, reasoning_ensemble, local_agent=None,
                       config=None, event_logger=None, file_handler=None,
                       a2a_handler=None):
    """
    Initialize the OpenAI-compatible API with required dependencies.

    Args:
        vector_store: OraDBVectorStore instance
        reasoning_ensemble: RAGReasoningEnsemble instance (optional)
        local_agent: LocalRAGAgent instance for fallback (optional)
        config: Configuration dict (optional)
        event_logger: OraDBEventLogger instance for database logging (optional)
        file_handler: FileHandler instance for @file processing (optional)
        a2a_handler: A2AHandler instance for A2A protocol routing (optional)
    """
    global _vector_store, _reasoning_ensemble, _local_agent, _config
    global _event_logger, _file_handler, _a2a_handler, _interceptor

    _vector_store = vector_store
    _reasoning_ensemble = reasoning_ensemble
    _local_agent = local_agent
    _config = config if config else {}
    _event_logger = event_logger
    _file_handler = file_handler
    _a2a_handler = a2a_handler

    if INTERCEPTOR_AVAILABLE:
        _interceptor = ReasoningInterceptor(host=os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434'))
        print('✅ ReasoningInterceptor initialized for direct agent streaming', flush=True)


def strip_ansi_codes(text):
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def log_a2a_event(method, status, details, **kwargs):
    """
    Log A2A-style events to stdout (visible in server logs).
    Mimics the logging format used in gradio_app.py.
    Forces flush to ensure logs appear immediately in buffered server contexts.
    """
    timestamp = datetime.now().strftime('%H:%M:%S')
    if status == 'success':
        icon = '✅'
    elif status == 'error':
        icon = '❌'
    else:
        icon = '🔄'
    print(f'[{timestamp}] {icon} [{method}] {status}: {details}', flush=True)
    for key, value in kwargs.items():
        print(f'    {key}: {value}', flush=True)


async def unified_rag_search(query, top_k=5):
    """
    Search across all collections (PDF, Web, Repository) and return unified results.

    Args:
        query: Search query
        top_k: Maximum number of results to return

    Returns:
        List of document chunks with metadata, sorted by relevance
    """
    if not _vector_store:
        return []

    all_results = []

    try:
        # Query all collections in parallel using thread pool
        loop = asyncio.get_event_loop()

        pdf_results = await loop.run_in_executor(
            None, lambda: _vector_store.query_pdf_collection(query, top_k)
        )
        for r in pdf_results:
            r['collection'] = 'PDF'
        all_results.extend(pdf_results)
    except Exception as e:
        logger.warning(f'PDF collection query failed: {e}')

    try:
        loop = asyncio.get_event_loop()
        web_results = await loop.run_in_executor(
            None, lambda: _vector_store.query_web_collection(query, top_k)
        )
        for r in web_results:
            r['collection'] = 'Web'
        all_results.extend(web_results)
    except Exception as e:
        logger.warning(f'Web collection query failed: {e}')

    try:
        loop = asyncio.get_event_loop()
        repo_results = await loop.run_in_executor(
            None, lambda: _vector_store.query_repo_collection(query, top_k)
        )
        for r in repo_results:
            r['collection'] = 'Repository'
        all_results.extend(repo_results)
    except Exception as e:
        logger.warning(f'Repo collection query failed: {e}')

    # Sort by score descending and return top_k
    all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
    return all_results[:top_k]


def build_rag_context(results):
    """Build context string from RAG results."""
    if not results:
        return ''
    context_parts = [
        'Here is relevant context from the knowledge base:\n']
    for i, result in enumerate(results, 1):
        content = result.get('content', result.get('text', ''))
        source = result.get('metadata', {}).get('source', result.get('collection', 'Unknown'))
        context_parts.append(f'[{i}] Source: {source}')
        context_parts.append(f'{content}\n')
    context_parts.append("\nUse the above context to help answer the user's question.\n")
    return '\n'.join(context_parts)


def format_rag_sources_for_display(results):
    """
    Format RAG sources for visual display in Open WebUI.
    Returns a markdown-formatted string showing retrieved documents.
    """
    if not results:
        return ''
    lines = [
        '---',
        '📚 **Retrieved Knowledge Sources**',
        '']
    for i, result in enumerate(results, 1):
        source = result.get('metadata', {}).get('source', result.get('collection', 'Unknown'))
        collection = result.get('collection', 'Unknown')
        score = result.get('score', 0)
        content_preview = result.get('content', result.get('text', ''))[:150]
        if len(result.get('content', result.get('text', ''))) > 150:
            content_preview += '...'
        lines.append(f'**{i}.** [{collection}] `{source}` (score: {score:.2f})')
        lines.append(f'> {content_preview}')
        lines.append('')
    lines.append('---')
    lines.append('')
    return '\n'.join(lines)


async def process_file_references(message):
    """
    Process @file and @@file references in a message.

    Patterns:
    - @filename.ext -> temporary context (inject into current query)
    - @@filename.ext -> permanent storage (add to RAG, then inject)

    Args:
        message: The user message containing file references

    Returns:
        Tuple of (cleaned_message, file_context, file_display_info)
    """
    if not _file_handler:
        return message, '', []

    file_display_info = []
    file_context = ''

    # Find @@file references (permanent storage)
    permanent_pattern = re.compile(r'@@(\S+)')
    permanent_refs = permanent_pattern.findall(message)

    # Find @file references (temporary context) - but not @@ ones
    temp_pattern = re.compile(r'(?<!@)@(\S+)')
    temp_refs = temp_pattern.findall(message)

    cleaned_message = message

    for filename in permanent_refs:
        cleaned_message = cleaned_message.replace(f'@@{filename}', '').strip()
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda f=filename: _file_handler.process_file(Path(f))
            )
            if result and result.get('content'):
                file_context += f'\n\n--- Content from {filename} ---\n{result["content"]}\n'
                file_display_info.append({
                    'filename': filename,
                    'status': 'success',
                    'storage_mode': 'permanent',
                    'chunks': result.get('chunks_stored', 0)
                })
            else:
                file_display_info.append({
                    'filename': filename,
                    'status': 'error',
                    'storage_mode': 'permanent',
                    'error': 'File not found or empty'
                })
        except Exception as e:
            logger.error(f'Error processing @@{filename}: {e}')
            file_display_info.append({
                'filename': filename,
                'status': 'error',
                'storage_mode': 'permanent',
                'error': str(e)
            })

    for filename in temp_refs:
        cleaned_message = cleaned_message.replace(f'@{filename}', '').strip()
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda f=filename: _file_handler.process_file(Path(f))
            )
            if result and result.get('content'):
                file_context += f'\n\n--- Content from {filename} ---\n{result["content"]}\n'
                file_display_info.append({
                    'filename': filename,
                    'status': 'success',
                    'storage_mode': 'temporary'
                })
            else:
                file_display_info.append({
                    'filename': filename,
                    'status': 'error',
                    'storage_mode': 'temporary',
                    'error': 'File not found or empty'
                })
        except Exception as e:
            logger.error(f'Error processing @{filename}: {e}')
            file_display_info.append({
                'filename': filename,
                'status': 'error',
                'storage_mode': 'temporary',
                'error': str(e)
            })

    return cleaned_message, file_context, file_display_info


def format_file_references_for_display(file_info):
    """
    Format file references for visual display in Open WebUI.
    """
    if not file_info:
        return ''
    lines = [
        '---',
        '📎 **Referenced Files**',
        '']
    for f in file_info:
        status_icon = '✅' if f['status'] == 'success' else '❌'
        mode_icon = '💾' if f.get('storage_mode') == 'permanent' else '📎'
        if f['status'] == 'success':
            lines.append(f'{status_icon} {mode_icon} **{f["filename"]}**')
        else:
            lines.append(f'{status_icon} {mode_icon} **{f["filename"]}** - {f.get("error", "Unknown error")}')
        lines.append('')
    lines.append('---')
    lines.append('')
    return '\n'.join(lines)


def run_interceptor_streaming(model_name, query, strategy):
    """
    Run the ReasoningInterceptor in a thread with REAL-TIME streaming.

    Uses a queue to communicate between the blocking interceptor thread
    and the async generator, enabling true chunk-by-chunk streaming
    just like CLI arena mode.
    """
    result_queue = queue.Queue()

    def _run():
        try:
            # Build the model string with strategy tag (e.g., "gemma3:latest+cot")
            model_with_strategy = f'{model_name}+{strategy}'
            log_a2a_event('interceptor.generate', 'started',
                          f'Model: {model_with_strategy}, Query length: {len(query)}')

            # Use streaming mode to get chunks in real-time
            stream = _interceptor.generate(
                model=model_with_strategy,
                prompt=query,
                stream=True
            )

            for chunk in stream:
                response_text = chunk.get('response', '')
                if response_text:
                    # Strip ANSI codes from reasoning output
                    clean_text = strip_ansi_codes(response_text)
                    if clean_text:
                        result_queue.put(('chunk', clean_text))

                if chunk.get('done', False):
                    break

            result_queue.put(('done', None))
            log_a2a_event('interceptor.generate', 'success',
                          f'Completed streaming for {model_with_strategy}')

        except Exception as e:
            logger.error(f'Interceptor streaming error: {e}')
            result_queue.put(('error', str(e)))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return result_queue


async def generate_streaming_response(
    request: ChatCompletionRequest,
    model_config: Dict[str, Any],
    rag_context: str,
    rag_results: Optional[List[Dict[str, Any]]] = None,
    file_display_info: Optional[List[Dict[str, Any]]] = None
) -> AsyncGenerator[str, None]:
    """
    Generate streaming chat completion response with REAL-TIME streaming.

    Yields SSE-formatted chunks compatible with OpenAI's streaming format.

    Uses ReasoningInterceptor directly (like CLI arena mode) for full
    multi-step streaming output from reasoning agents. Chunks are streamed
    in real-time as they are generated, not buffered.

    When rag_results is provided, displays the retrieved sources visually
    before the main response.

    When file_display_info is provided, displays the referenced files
    before RAG sources.
    """
    completion_id = f'chatcmpl-{uuid.uuid4().hex[:12]}'
    created = int(time.time())
    model_name = request.model

    def make_chunk(content=None, role=None, finish_reason=None):
        """Create an SSE-formatted chunk."""
        delta = {}
        if role:
            delta['role'] = role
        if content:
            delta['content'] = content

        chunk_data = {
            'id': completion_id,
            'object': 'chat.completion.chunk',
            'created': created,
            'model': model_name,
            'choices': [{
                'index': 0,
                'delta': delta,
                'finish_reason': finish_reason
            }]
        }
        return f'data: {json.dumps(chunk_data)}\n\n'

    # Send initial role chunk
    yield make_chunk(role='assistant')

    # Display file references if present
    if file_display_info:
        file_display = format_file_references_for_display(file_display_info)
        if file_display:
            yield make_chunk(content=file_display)

    # Display RAG sources if present
    if rag_results:
        sources_display = format_rag_sources_for_display(rag_results)
        if sources_display:
            yield make_chunk(content=sources_display)

    strategy = model_config.get('strategy', 'standard')
    is_reasoning = model_config.get('is_reasoning', False)
    base_model = _config.get('model_name', 'qwen3.5:9b')

    # Build the full prompt with context
    messages = request.messages
    last_message = ''
    for msg in reversed(messages):
        if msg.role == 'user' or (hasattr(msg.role, 'value') and msg.role.value == 'user'):
            last_message = extract_text_from_content(msg.content)
            break

    full_prompt = last_message
    if rag_context:
        full_prompt = f'{rag_context}\n\nUser Question: {last_message}'

    # Use ReasoningInterceptor for reasoning models when available
    if _interceptor and INTERCEPTOR_AVAILABLE and is_reasoning:
        try:
            log_a2a_event('openai.streaming', 'started',
                          f'Using ReasoningInterceptor with strategy: {strategy}')

            result_queue = run_interceptor_streaming(base_model, full_prompt, strategy)

            while True:
                try:
                    msg_type, msg_data = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: result_queue.get(timeout=120)
                    )

                    if msg_type == 'chunk':
                        yield make_chunk(content=msg_data)
                    elif msg_type == 'done':
                        break
                    elif msg_type == 'error':
                        yield make_chunk(content=f'\n\n⚠️ Error: {msg_data}')
                        break
                except queue.Empty:
                    yield make_chunk(content='\n\n⚠️ Response timeout.')
                    break

        except Exception as e:
            logger.error(f'Interceptor streaming failed: {e}')
            yield make_chunk(content=f'\n\n⚠️ Interceptor error: {str(e)}')

    # Fall back to reasoning ensemble
    elif _reasoning_ensemble and is_reasoning:
        try:
            log_a2a_event('openai.streaming', 'started',
                          f'Using RAGReasoningEnsemble with strategy: {strategy}')

            result = await _reasoning_ensemble.run(
                query=full_prompt,
                strategies=[strategy],
                use_rag=False,  # RAG already applied above
            )

            response_text = result.winner.get('response', '')
            clean_text = strip_ansi_codes(response_text)

            # Stream in small chunks for better UX
            chunk_size = 50
            for i in range(0, len(clean_text), chunk_size):
                yield make_chunk(content=clean_text[i:i + chunk_size])
                await asyncio.sleep(0.01)

        except Exception as e:
            logger.error(f'Ensemble streaming failed: {e}')
            yield make_chunk(content=f'\n\n⚠️ Error: {str(e)}')

    # Fall back to local agent
    elif _local_agent:
        try:
            log_a2a_event('openai.streaming', 'started', 'Using LocalRAGAgent fallback')

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: _local_agent.process_query(full_prompt)
            )

            response_text = result.get('answer', str(result))
            clean_text = strip_ansi_codes(response_text)

            chunk_size = 50
            for i in range(0, len(clean_text), chunk_size):
                yield make_chunk(content=clean_text[i:i + chunk_size])
                await asyncio.sleep(0.01)

        except Exception as e:
            logger.error(f'Local agent streaming failed: {e}')
            yield make_chunk(content=f'\n\n⚠️ Error: {str(e)}')
    else:
        yield make_chunk(content='⚠️ No reasoning backend available. Please check server configuration.')

    # Send finish chunk
    yield make_chunk(finish_reason='stop')
    yield 'data: [DONE]\n\n'


async def generate_non_streaming_response(
    request: ChatCompletionRequest,
    model_config: Dict[str, Any],
    rag_context: str
) -> ChatCompletionResponse:
    """
    Generate non-streaming chat completion response.
    """
    completion_id = f'chatcmpl-{uuid.uuid4().hex[:12]}'
    created = int(time.time())

    strategy = model_config.get('strategy', 'standard')
    is_reasoning = model_config.get('is_reasoning', False)
    base_model = _config.get('model_name', 'qwen3.5:9b')

    # Extract last user message
    messages = request.messages
    last_message = ''
    for msg in reversed(messages):
        if msg.role == 'user' or (hasattr(msg.role, 'value') and msg.role.value == 'user'):
            last_message = extract_text_from_content(msg.content)
            break

    full_prompt = last_message
    if rag_context:
        full_prompt = f'{rag_context}\n\nUser Question: {last_message}'

    response_text = ''

    # Use ReasoningInterceptor when available
    if _interceptor and INTERCEPTOR_AVAILABLE and is_reasoning:
        try:
            model_with_strategy = f'{base_model}+{strategy}'
            result = _interceptor.generate(
                model=model_with_strategy,
                prompt=full_prompt,
                stream=False
            )
            response_text = strip_ansi_codes(result.get('response', ''))
        except Exception as e:
            logger.error(f'Interceptor non-streaming error: {e}')
            response_text = f'Error: {str(e)}'

    elif _reasoning_ensemble and is_reasoning:
        try:
            result = await _reasoning_ensemble.run(
                query=full_prompt,
                strategies=[strategy],
                use_rag=False,
            )
            response_text = strip_ansi_codes(result.winner.get('response', ''))
        except Exception as e:
            logger.error(f'Ensemble non-streaming error: {e}')
            response_text = f'Error: {str(e)}'

    elif _local_agent:
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: _local_agent.process_query(full_prompt)
            )
            response_text = result.get('answer', str(result))
        except Exception as e:
            logger.error(f'Local agent non-streaming error: {e}')
            response_text = f'Error: {str(e)}'
    else:
        response_text = 'No reasoning backend available. Please check server configuration.'

    # Build response
    response = ChatCompletionResponse(
        id=completion_id,
        object='chat.completion',
        created=created,
        model=request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role='assistant', content=response_text),
                finish_reason='stop'
            )
        ],
        usage=UsageInfo(
            prompt_tokens=len(full_prompt.split()),
            completion_tokens=len(response_text.split()),
            total_tokens=len(full_prompt.split()) + len(response_text.split())
        )
    )

    return response


def extract_text_from_content(content):
    """
    Extract text content from a message that may be string or multimodal array.

    OpenAI API supports content as either:
    - A simple string
    - An array of ContentPart objects with type "text", "image_url", etc.

    Returns the concatenated text content.
    """
    if content is None:
        return ''
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict):
                if part.get('type') == 'text' and part.get('text'):
                    text_parts.append(part['text'])
            elif hasattr(part, 'type') and part.type == 'text' and part.text:
                text_parts.append(part.text)
        return ' '.join(text_parts)
    return str(content)


def extract_attachments_from_content(content):
    """
    Extract non-text attachments (images, files, URLs) from multimodal content.

    Returns list of attachment info dicts.
    """
    attachments = []
    if not isinstance(content, list):
        return attachments
    for part in content:
        if isinstance(part, dict):
            part_type = part.get('type', '')
            if part_type == 'image_url':
                attachments.append({
                    'type': 'image',
                    'url': part.get('image_url', {}).get('url', '')
                })
            elif part_type == 'file':
                attachments.append({
                    'type': 'file',
                    'name': part.get('name', ''),
                    'url': part.get('url', ''),
                    'data': part.get('data', '')
                })
            elif part_type not in ('text',):
                attachments.append({
                    'type': part_type,
                    'data': part
                })
        elif hasattr(part, 'type'):
            if part.type == 'image_url' and part.image_url:
                attachments.append({
                    'type': 'image',
                    'url': part.image_url.get('url', '') if isinstance(part.image_url, dict) else ''
                })
            elif part.type == 'file':
                attachments.append({
                    'type': 'file',
                    'name': getattr(part, 'name', ''),
                    'url': getattr(part, 'url', ''),
                    'data': getattr(part, 'data', '')
                })
    return attachments


def extract_openwebui_sources(message_content):
    """
    Extract source content from Open WebUI's preprocessed message format.

    Open WebUI embeds webpage content in messages using <source> tags:
    <source id="1" title="Page Title" url="https://...">
    ...content...
    </source>

    Returns list of source dicts with id, title, url, and content.
    """
    sources = []
    pattern = re.compile(r'<source\s+([^>]*)>(.*?)</source>', re.DOTALL | re.IGNORECASE)
    for match in pattern.finditer(message_content):
        attrs_str = match.group(1)
        content = match.group(2).strip()
        id_match = re.search(r'id="([^"]*)"', attrs_str)
        title_match = re.search(r'title="([^"]*)"', attrs_str)
        url_match = re.search(r'url="([^"]*)"', attrs_str)
        name_match = re.search(r'name="([^"]*)"', attrs_str)

        if title_match:
            title = title_match.group(1)
        elif name_match:
            title = name_match.group(1)
        else:
            title = ''

        source_info = {
            'id': id_match.group(1) if id_match else '',
            'title': title,
            'url': url_match.group(1) if url_match else '',
            'content': content
        }
        # Only add sources with substantial content
        if content and len(content) > 50:
            sources.append(source_info)
    return sources


def chunk_text(text, chunk_size=1000, overlap=200):
    """
    Split text into overlapping chunks for vector storage.

    Args:
        text: Text to chunk
        chunk_size: Target size of each chunk in characters
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # Try to break at sentence boundaries
        if end < len(text):
            for punct in ('. ', '.\n', '! ', '!\n', '? ', '?\n', '\n\n'):
                break_point = text.rfind(punct, start + chunk_size // 2, end)
                if break_point != -1:
                    end = break_point + len(punct)
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap if end < len(text) else len(text)
    return chunks


async def execute_via_a2a(
    query: str,
    strategy: str,
    use_rag: bool = False,
    collection: str = 'General',
    request_id: str = None
) -> Dict[str, Any]:
    """
    Execute a reasoning request via the A2A protocol.

    This routes the request through the A2AHandler which:
    1. Logs the request to Oracle DB event logger
    2. Executes the reasoning strategy
    3. Returns the response in A2A format

    Args:
        query: The user query to process
        strategy: Reasoning strategy (cot, tot, react, etc.)
        use_rag: Whether to use RAG context
        collection: RAG collection to use
        request_id: Optional request ID for tracking

    Returns:
        Dict with response and metadata
    """
    if not _a2a_handler:
        return {
            'error': 'A2A handler not available',
            'response': ''
        }

    try:
        from src.a2a_models import A2ARequest
        if not request_id:
            request_id = str(uuid.uuid4())

        a2a_request = A2ARequest(
            jsonrpc='2.0',
            method='reasoning.strategy',
            params={
                'query': query,
                'strategy': strategy,
                'use_rag': use_rag,
                'collection': collection
            },
            id=request_id
        )

        result = await _a2a_handler.handle_request(a2a_request)
        return result.result if hasattr(result, 'result') and result.result else {
            'error': result.error if hasattr(result, 'error') else 'Unknown error',
            'response': ''
        }

    except Exception as e:
        logger.error(f'A2A execution error: {e}')
        return {
            'error': str(e),
            'response': ''
        }


async def persist_openwebui_context_to_rag(message_content):
    """
    Extract Open WebUI embedded sources and persist them to Oracle AI Database.

    This function detects when Open WebUI has preprocessed webpage content into
    the message (with <source> tags) and stores the content in the WEBCOLLECTION
    for future RAG retrieval.

    Args:
        message_content: The full message content from Open WebUI

    Returns:
        Dict with status, sources_found, chunks_stored, and any errors
    """
    if not _vector_store:
        return {
            'status': 'skipped',
            'reason': 'No vector store available',
            'sources_found': 0,
            'chunks_stored': 0
        }

    sources = extract_openwebui_sources(message_content)
    if not sources:
        return {
            'status': 'no_sources',
            'sources_found': 0,
            'chunks_stored': 0
        }

    total_chunks_stored = 0
    errors = []

    for source in sources:
        try:
            content = source.get('content', '')
            title = source.get('title', '')
            url = source.get('url', '')

            if not content:
                continue

            # Chunk the content
            chunks = chunk_text(content)

            # Prepare chunks for storage
            web_chunks = []
            for i, chunk_text_content in enumerate(chunks):
                web_chunks.append({
                    'text': chunk_text_content,
                    'metadata': {
                        'source': url or f'openwebui_{source.get("id", "")}',
                        'title': title,
                        'type': 'openwebui_source',
                        'chunk_id': i,
                        'total_chunks': len(chunks)
                    }
                })

            # Store in WEBCOLLECTION
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda c=web_chunks, u=url: _vector_store.add_web_chunks(c, source_id=u or 'openwebui')
            )
            total_chunks_stored += len(web_chunks)

            log_a2a_event('openwebui.persist', 'success',
                          f'Stored {len(web_chunks)} chunks from: {title or url}')

            # Log to event logger if available
            if _event_logger:
                _event_logger.log_document_event(
                    document_type='openwebui_source',
                    document_id=source.get('id', str(uuid.uuid4())),
                    source=url,
                    chunks_processed=len(web_chunks),
                    status='success'
                )

        except Exception as e:
            error_msg = f'Failed to persist source {source.get("id", "unknown")}: {e}'
            logger.error(error_msg)
            errors.append(error_msg)

    return {
        'status': 'success' if not errors else 'partial',
        'sources_found': len(sources),
        'chunks_stored': total_chunks_stored,
        'errors': errors
    }


async def process_openwebui_url_uploads(request_files):
    """
    Process URL uploads from Open WebUI's "Upload Link" functionality.

    When a user uses "Upload Link" in Open WebUI, the URL is passed in the
    request.files array. This function:
    1. Detects URL files in the request
    2. Fetches and processes the URL content using WebProcessor
    3. Persists chunks to WEBCOLLECTION with openwebui_url source
    4. Logs the event to Oracle Autonomous

    Args:
        request_files: List of file attachments from request.files

    Returns:
        Dict with stats: {"urls_processed": int, "chunks_stored": int, "errors": []}
    """
    if not request_files or not _vector_store:
        return {
            'urls_processed': 0,
            'chunks_stored': 0,
            'errors': []
        }

    urls_processed = 0
    chunks_stored = 0
    errors = []
    web_processor = WebProcessor(chunk_size=500)

    for file_info in request_files:
        try:
            # Check if this is a URL file
            url = None
            if isinstance(file_info, dict):
                url = file_info.get('url', '')
                if not url and file_info.get('name', '').startswith('http'):
                    url = file_info['name']
            elif hasattr(file_info, 'url') and file_info.url:
                url = file_info.url
            elif hasattr(file_info, 'name') and file_info.name and is_url(file_info.name):
                url = file_info.name

            if not url or not is_url(url):
                continue

            log_a2a_event('openwebui.url_upload', 'started', f'Processing URL: {url}')

            # Process URL with WebProcessor
            loop = asyncio.get_event_loop()
            chunks = await loop.run_in_executor(
                None, lambda u=url: web_processor.process_url(u)
            )

            if chunks:
                # Prepare for storage
                web_chunks = []
                for chunk in chunks:
                    chunk['metadata']['source'] = f'openwebui_url:{url}'
                    web_chunks.append(chunk)

                # Store in WEBCOLLECTION
                await loop.run_in_executor(
                    None, lambda c=web_chunks, u=url: _vector_store.add_web_chunks(c, source_id=u)
                )

                urls_processed += 1
                chunks_stored += len(web_chunks)

                log_a2a_event('openwebui.url_upload', 'success',
                              f'Stored {len(web_chunks)} chunks from {url}')

                # Log event
                if _event_logger:
                    _event_logger.log_document_event(
                        document_type='openwebui_url',
                        document_id=url,
                        source=url,
                        chunks_processed=len(web_chunks),
                        status='success'
                    )

        except Exception as e:
            error_msg = f'Failed to process URL {url}: {e}'
            logger.error(error_msg)
            errors.append(error_msg)

    return {
        'urls_processed': urls_processed,
        'chunks_stored': chunks_stored,
        'errors': errors
    }


# ============================================================
# Route Handlers
# ============================================================

@router.get('/models', response_model=ModelList)
async def list_models():
    """List all available models."""
    return get_model_list()


@router.get('/models/{model_id}')
async def get_model(model_id: str):
    """Get information about a specific model."""
    model_config = get_model_config(model_id)
    if not model_config:
        raise HTTPException(status_code=404, detail=f'Model {model_id} not found')
    return ModelInfo(
        id=model_id,
        object='model',
        created=int(time.time()),
        owned_by='agentic-rag',
        name=model_config.get('name', model_id),
        description=model_config.get('description', '')
    )


@router.post('/chat/completions')
async def create_chat_completion(request: ChatCompletionRequest):
    """
    Create a chat completion (OpenAI-compatible).

    This is the main endpoint consumed by Open WebUI and other
    OpenAI-compatible clients. It routes to the appropriate reasoning
    strategy based on the model parameter.
    """
    start_time = time.time()

    try:
        # 1. Extract last user message
        last_user_message = ''
        for msg in reversed(request.messages):
            if msg.role == 'user' or (hasattr(msg.role, 'value') and msg.role.value == 'user'):
                last_user_message = extract_text_from_content(msg.content)
                break

        if not last_user_message:
            raise HTTPException(status_code=400, detail='No user message found in request')

        log_a2a_event('chat.completions', 'started',
                      f'Model: {request.model}, Query: {last_user_message[:100]}...')

        # 2. Determine model/strategy from request.model
        model_config = get_model_config(request.model)
        if not model_config:
            # Default to standard model config
            model_config = {
                'strategy': 'standard',
                'is_reasoning': False,
                'use_rag': False,
                'name': request.model,
                'description': 'Standard model'
            }

        # 3. Process Open WebUI embedded sources (persist to RAG)
        for msg in request.messages:
            if msg.role == 'user' or (hasattr(msg.role, 'value') and msg.role.value == 'user'):
                msg_content = extract_text_from_content(msg.content)
                if '<source' in msg_content:
                    await persist_openwebui_context_to_rag(msg_content)

        # 4. Process file references if _file_handler available
        file_display_info = None
        if _file_handler:
            cleaned_message, file_context, file_display_info = await process_file_references(
                last_user_message
            )
            if file_context:
                last_user_message = cleaned_message
                # Prepend file context to the message
                last_user_message = f'{file_context}\n\n{last_user_message}'

        # 5. Process URL uploads if present
        if request.files:
            await process_openwebui_url_uploads(request.files)

        # 6. Do RAG search if model config says use_rag
        rag_context = ''
        rag_results = None
        use_rag = model_config.get('use_rag', False)

        if use_rag and _vector_store:
            rag_results = await unified_rag_search(last_user_message, top_k=5)
            rag_context = build_rag_context(rag_results)
            log_a2a_event('chat.completions', 'rag_search',
                          f'Found {len(rag_results)} RAG results')

        # 7. Log API event
        if _event_logger:
            try:
                duration_ms = (time.time() - start_time) * 1000
                _event_logger.log_api_event(
                    endpoint='/v1/chat/completions',
                    method='POST',
                    request_data={
                        'model': request.model,
                        'query': last_user_message[:500],
                        'streaming': request.stream,
                        'use_rag': use_rag
                    },
                    status_code=200,
                    duration_ms=duration_ms
                )
            except Exception as e:
                logger.warning(f'Failed to log API event: {e}')

        # 8. If streaming: return StreamingResponse
        if request.stream:
            return StreamingResponse(
                generate_streaming_response(
                    request, model_config, rag_context, rag_results, file_display_info
                ),
                media_type='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'
                }
            )

        # 9. If not streaming: return non-streaming response
        response = await generate_non_streaming_response(request, model_config, rag_context)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Chat completion error: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/health')
async def openai_health():
    """Health check endpoint for OpenAI-compatible API."""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'interceptor_available': INTERCEPTOR_AVAILABLE,
        'vector_store_available': _vector_store is not None,
        'reasoning_ensemble_available': _reasoning_ensemble is not None,
        'local_agent_available': _local_agent is not None,
        'event_logger_available': _event_logger is not None,
        'file_handler_available': _file_handler is not None,
        'a2a_handler_available': _a2a_handler is not None
    }
