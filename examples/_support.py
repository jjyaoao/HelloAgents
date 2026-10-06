"""离线预设模型响应，实际执行组件；--live 使用环境配置。"""

import os
import sys
from dotenv import load_dotenv
from hello_agents import Config, HelloAgentsLLM
from hello_agents.core.llm_response import ToolCall
from examples.agents.runtime_features import ScriptedLLM, response


def demo_config(**overrides):
    return Config(
        **(
            dict(
                trace_enabled=False,
                session_enabled=False,
                skills_enabled=False,
                subagent_enabled=False,
                todowrite_enabled=False,
                devlog_enabled=False,
            )
            | overrides
        )
    )


def demo_llm(responses, *, live=None):
    if not ("--live" in sys.argv if live is None else live):
        print("离线模式：预设模型响应，真实执行工具。")
        return ScriptedLLM(responses)
    load_dotenv()
    missing = [
        k for k in ("LLM_MODEL_ID", "LLM_API_KEY", "LLM_BASE_URL") if not os.getenv(k)
    ]
    if missing:
        raise ValueError("需设置：" + ", ".join(missing))
    return HelloAgentsLLM()


def tool_response(name, arguments, *, call_id="demo-call"):
    import json

    return response(
        calls=[ToolCall(call_id, name, json.dumps(arguments, ensure_ascii=False))],
        reason="tool_calls",
    )
