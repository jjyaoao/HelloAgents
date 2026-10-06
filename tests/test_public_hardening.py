"""Regressions found through first-use, provider and output-boundary review."""
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from hello_agents import HelloAgentsLLM, SimpleAgent, Config, AgentComponents
from hello_agents.core.llm_adapters import AnthropicAdapter, BaseLLMAdapter
from hello_agents.observability import TraceLogger


def test_trace_untrusted_html_and_privacy_flags(tmp_path):
    marker = '<img src=x onerror="window.marker=1">'
    with TraceLogger(str(tmp_path)) as logger:
        logger.log_event("tool_call", {"tool_name": marker, "api_key": "opaque-value", "nested": {"raw_response": "private-raw"}})
        logger.log_event("error", {"message": marker, "error_type": marker, "token": "tvly-dev-synthetic", "text": "Bearer first.second.third"})
    logger.finalize()
    html = logger.html_path.read_text(encoding="utf-8")
    raw = logger.jsonl_path.read_text(encoding="utf-8")
    assert '<img' not in html and '&lt;img' in html
    assert 'private-raw' not in html and 'private-raw' in raw
    assert not any(value in raw for value in ('opaque-value', 'tvly-dev-synthetic', 'first.second.third'))


def test_trace_custom_sanitizer_and_raw_opt_in(tmp_path):
    def redact(event):
        event['payload']['personal'] = '[REMOVED]'
        return event
    with TraceLogger(str(tmp_path), html_include_raw_response=True, sanitizer=redact) as logger:
        logger.log_event('test', {'raw_response': 'visible', 'personal': 'private'})
    assert 'visible' in logger.html_path.read_text(encoding='utf-8')
    assert 'private' not in logger.jsonl_path.read_text(encoding='utf-8')


@pytest.mark.parametrize('method', ['invoke', 'invoke_with_tools', 'stream_invoke', 'ainvoke', 'ainvoke_with_tools', 'astream_invoke', 'astream_invoke_with_tools'])
def test_instance_options_are_overridden_at_every_entry(method):
    llm = HelloAgentsLLM(top_p=0.2, extra_body={'nested': 1})
    adapter = Mock()
    captured = []
    def call(*args, **kw):
        captured.append(kw)
        return SimpleNamespace(content='ok', model='test', usage={}, latency_ms=0, finish_reason='stop')
    def stream(*args, **kw):
        call(*args, **kw)
        yield 'ok'
    async def astream(*args, **kw):
        call(*args, **kw)
        yield 'ok'
    adapter.invoke = adapter.invoke_with_tools = call
    adapter.stream_invoke = stream
    adapter.astream_invoke = adapter.astream_invoke_with_tools = astream
    llm._adapter = adapter
    args = ([{'role':'user','content':'hello'}],)
    if method.endswith('with_tools'):
        args += ([],)
    result = getattr(llm, method)(*args, top_p=0.7)
    async def consume():
        if method.startswith('astream'):
            return [x async for x in result]
        return await result
    if method.startswith('a'):
        asyncio.run(consume())
    elif method.startswith('stream'):
        list(result)
    assert captured[0]['top_p'] == 0.7
    captured[0]['extra_body']['nested'] = 99
    assert llm.kwargs['extra_body']['nested'] == 1


def test_provider_proxy_selection_and_host_detection():
    with HelloAgentsLLM(provider='anthropic', base_url='https://proxy.invalid') as llm:
        assert llm.provider == 'anthropic'
    with HelloAgentsLLM(base_url='https://anthropic.com.evil.invalid') as llm:
        assert llm.provider == 'openai'
    with pytest.raises(ValueError):
        HelloAgentsLLM(provider='typo')


@pytest.mark.parametrize('choice,expected', [('none', {'type':'none'}), ('auto', {'type':'auto'}), ('required', {'type':'any'}), ({'type':'function','function':{'name':'read'}}, {'type':'tool','name':'read'})])
def test_anthropic_tool_choice_in_actual_request(choice, expected):
    adapter = AnthropicAdapter('synthetic', 'https://example.invalid', 1, 'model')
    adapter._client = Mock()
    adapter._client.messages.create.return_value = SimpleNamespace(content=[], usage=SimpleNamespace(input_tokens=1, output_tokens=1), stop_reason='end_turn')
    adapter.invoke_with_tools([{'role':'user','content':'hi'}], [{'type':'function','function':{'name':'read','parameters':{'type':'object'}}}], tool_choice=choice)
    assert adapter._client.messages.create.call_args.kwargs['tool_choice'] == expected


def test_injected_or_main_model_for_summary_and_subagent():
    main, other = Mock(model='main'), Mock(model='other')
    agent = SimpleAgent('test', main)
    assert agent._get_summary_llm() is main
    assert agent._create_light_llm() is main
    agent = SimpleAgent('test', main, components=AgentComponents(summary_llm=other, subagent_llm=other))
    assert agent._get_summary_llm() is other
    assert agent._create_light_llm() is other


@pytest.mark.parametrize('value', [float('inf'), float('nan'), -1, 0])
def test_timeout_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        HelloAgentsLLM(timeout=value)
    with pytest.raises(ValueError):
        Config(llm_async_timeout=value)


def test_import_does_not_change_host_logging():
    result = subprocess.run([sys.executable, '-c', 'import logging; logging.getLogger("httpx").setLevel(10); import hello_agents; assert logging.getLogger("httpx").level == 10'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_readme_env_setup_in_fresh_process(tmp_path):
    (tmp_path / '.env').write_text('LLM_MODEL_ID=synthetic\nLLM_API_KEY=synthetic\nLLM_BASE_URL=https://example.invalid\n', encoding='utf-8')
    env = {k:v for k,v in os.environ.items() if not k.startswith('LLM_')}
    result = subprocess.run([sys.executable, '-c', 'from dotenv import load_dotenv; load_dotenv(".env"); from hello_agents import HelloAgentsLLM; llm=HelloAgentsLLM(); assert llm.model=="synthetic"; llm.close()'], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.asyncio
async def test_fallback_stream_stops_producer_and_closes_source():
    class Adapter(BaseLLMAdapter):
        def create_client(self): pass
        def invoke(self, *args, **kwargs): pass
        def invoke_with_tools(self, *args, **kwargs): pass
        def stream_invoke(self, *args, **kwargs):
            try:
                for i in range(100):
                    self.produced += 1
                    yield str(i)
                    time.sleep(0.005)
            finally:
                self.finished = True
    adapter = Adapter('synthetic', None, 1, 'test')
    adapter.produced, adapter.finished = 0, False
    stream = adapter.astream_invoke([])
    await anext(stream)
    await stream.aclose()
    await asyncio.sleep(0.15)
    assert adapter.finished and adapter.produced < 100


@pytest.mark.asyncio
async def test_client_closure_idempotent_and_reuse_rejected():
    from unittest.mock import AsyncMock
    llm = HelloAgentsLLM()
    sync, async_client = Mock(), Mock(close=AsyncMock())
    llm._adapter._client, llm._adapter._async_client = sync, async_client
    with pytest.raises(RuntimeError, match='aclose'):
        llm.close()
    await llm.aclose()
    await llm.aclose()
    sync.close.assert_called_once()
    async_client.close.assert_awaited_once()
    with pytest.raises(RuntimeError, match='closed'):
        llm.invoke([{'role':'user','content':'x'}])


def test_gemini_passes_options_and_rejects_unknown_fields():
    pytest.importorskip('google.genai')
    from hello_agents.core.llm_adapters import GeminiAdapter
    adapter=GeminiAdapter('synthetic','https://example.invalid',2,'model')
    adapter._client=Mock()
    adapter._client.models.generate_content.return_value=SimpleNamespace(text='ok',usage_metadata=None,candidates=[])
    adapter.invoke([{'role':'user','content':'hello'}],top_p=0.2,max_tokens=64)
    config=adapter._client.models.generate_content.call_args.kwargs['config']
    assert config.top_p==0.2 and config.max_output_tokens==64
    with pytest.raises(Exception,match='unsupported_audit_option'):
        adapter.invoke([{'role':'user','content':'hello'}],unsupported_audit_option=True)


@pytest.mark.parametrize('mode',['sync','async','stream'])
def test_provider_reasoning_is_returned_to_model_not_public_chunks(mode):
    from copy import deepcopy
    from hello_agents import ToolRegistry
    from hello_agents.tools import Tool, ToolResponse
    from hello_agents.core.llm_response import LLMToolResponse, ToolCall
    class Lookup(Tool):
        def __init__(self): super().__init__('lookup','lookup a fact')
        def get_parameters(self): return []
        def run(self,parameters): return ToolResponse.success('fact')
    class Scripted:
        model='scripted'
        def __init__(self): self.inputs=[]
        def invoke_with_tools(self,messages,tools,**kw):
            self.inputs.append(deepcopy(messages))
            if len(self.inputs)==1:
                return LLMToolResponse(None,[ToolCall('c1','lookup','{}')],self.model,reasoning_content='private-field')
            return LLMToolResponse('public answer',[],self.model,reasoning_content='final-private-field')
    llm=Scripted()
    registry=ToolRegistry();registry.register_tool(Lookup())
    agent=SimpleAgent('test',llm,tool_registry=registry)
    if mode=='sync': result=agent.run('task')
    elif mode=='async': result=asyncio.run(agent.arun('task'))
    else: result=''.join(agent.stream_run('task'))
    assert result=='public answer' and 'private-field' not in result
    assert llm.inputs[1][-2]['reasoning_content']=='private-field'


def test_planner_auto_does_not_assume_forced_tool_support():
    from hello_agents.agents.plan_solve_agent import Planner
    from hello_agents.core.llm_response import LLMToolResponse,ToolCall
    llm=Mock()
    llm.invoke_with_tools.return_value=LLMToolResponse(None,[ToolCall('p','generate_plan','{"steps":["one"]}')],'test')
    assert Planner(llm).plan('task')==['one']
    assert llm.invoke_with_tools.call_args.kwargs['tool_choice']=='auto'


def test_sync_stream_early_close_releases_sdk_response():
    from hello_agents.core.llm_adapters import OpenAIAdapter
    class Stream:
        closed=False
        def __iter__(self):
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content='x'))],usage=None)
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content='y'))],usage=None)
        def close(self): self.closed=True
    adapter=OpenAIAdapter('test','https://example.invalid',1,'test')
    adapter._client=Mock()
    response=Stream()
    adapter._client.chat.completions.create.return_value=response
    stream=adapter.stream_invoke([])
    assert next(stream)=='x'
    stream.close()
    assert response.closed


def test_first_concurrent_requests_create_one_sdk_client():
    from concurrent.futures import ThreadPoolExecutor
    from hello_agents.core.llm_adapters import OpenAIAdapter
    adapter=OpenAIAdapter('test','https://example.invalid',1,'test')
    client=object()
    def create():
        time.sleep(0.01)
        return client
    adapter.create_client=Mock(side_effect=create)
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(item is client for item in pool.map(lambda _:adapter._get_client(),range(16)))
    adapter.create_client.assert_called_once()
