"""检索、记忆、上下文的组件组合示例。

默认只执行本地 SQLite 操作，不创建模型客户端。
资料为虚构教学材料，不可作为真实出游依据。
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from hello_agents.context import (
    ContextBuilder,
    ContextConfig,
    MemoryContextProvider,
    RetrievalContextProvider,
)
from hello_agents.memory import MemoryStore
from hello_agents.retrieval import RAGStore


NOTICE = """杭州示例博物馆参观说明（教学虚构资料）
平日参观无需预约。节假日需提前预约；未成年人由成人陪同。
预约规则只适用于杭州示例博物馆，不适用于其他同名场馆。
"""
UPDATED_NOTICE = """杭州示例博物馆预约通知（教学虚构资料）
杭州示例博物馆所有开放日均须提前预约，旧版的平日免预约条款停止适用。
周一闭馆；未成年人由成人陪同。预约满额时可改去湖畔公共步道。
"""
TRANSPORT = """杭州湖畔公共步道交通说明（教学虚构资料）
湖畔公共步道无需预约。公交到达东入口后，短线步行约两公里。
长线步行约九公里。需要减少步行时，选择短线并从同一入口返回。
"""


def stores(workspace):
    return (
        RAGStore(workspace / "knowledge.sqlite"),
        MemoryStore(
            workspace / "memory.sqlite", user_id="traveler", task_id="hangzhou"
        ),
    )


def local(workspace):
    rag, memory = stores(workspace)
    # 文档导入由宿主完成，不授予模型任意文件/网络导入权限。
    rag.add_document(NOTICE, "fixture://museum/notice", "1", document_id="museum")
    old = rag.search("杭州博物馆预约")[0]
    rag.add_document(
        UPDATED_NOTICE, "fixture://museum/notice", "2", document_id="museum"
    )
    rag.add_document(
        TRANSPORT, "fixture://lake/transport", "1", document_id="transport"
    )
    results = rag.search("杭州博物馆预约")
    print("当前资料检索：")
    print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
    print("先前取得的片段仍可回读确切版本：", rag.read_chunk(old.chunk_id).version)

    existing = memory.search("步行")
    if not existing:
        record = memory.add(
            "每天步行不超过八公里，偏好历史文化和自然风景。", "user:initial-preference"
        )
    else:
        record = existing[0]
    if "五公里" not in record.content:
        record = memory.revise(
            record.memory_id,
            "每天步行不超过五公里，偏好历史文化和自然风景。",
            "user:revised-preference",
        )
    assert (
        MemoryStore(workspace / "memory.sqlite", "another-user", "hangzhou").search()
        == []
    )

    # Providers 每次重新读取持久化状态；这里直接组装，不假装执行了模型。
    query = "安排杭州博物馆与步道两日游，说明预约条件。"
    providers = [
        RetrievalContextProvider(rag),
        MemoryContextProvider(memory, required=True),
    ]
    packets = [
        packet for provider in providers for packet in provider.get_context(query)
    ]
    result = ContextBuilder(ContextConfig(max_tokens=4000)).build_messages(
        [
            {
                "role": "system",
                "content": "只依据资料规划，标明来源，不确定时说明缺失。",
            },
            {"role": "user", "content": query},
        ],
        additional_packets=packets,
    )
    (workspace / "context-preview.json").write_text(
        json.dumps(
            {"messages": result.messages, "diagnostics": result.diagnostics},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("已生成上下文预览：", workspace / "context-preview.json")
    print("在新进程中读回偏好：")
    subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(Path(__file__).resolve()),
            "--mode",
            "resume",
            "--workspace",
            str(workspace.resolve()),
        ],
        check=True,
    )


def resume(workspace):
    if not (workspace / "memory.sqlite").exists():
        raise SystemExit("请先运行 local 模式，或指定已有的 workspace")
    _, memory = stores(workspace)
    print(
        json.dumps([r.to_dict() for r in memory.search()], ensure_ascii=False, indent=2)
    )


def live(workspace):
    from dotenv import load_dotenv

    load_dotenv()
    required = ["LLM_MODEL_ID", "LLM_API_KEY", "LLM_BASE_URL"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise SystemExit("live 模式需要环境变量：" + ", ".join(missing))
    if not (workspace / "knowledge.sqlite").exists():
        raise SystemExit("请先运行 local 模式准备资料和偏好")

    from hello_agents import Config, HelloAgentsLLM, SimpleAgent, ToolRegistry
    from hello_agents.tools.builtin import MemoryTool, RAGTool

    rag, memory = stores(workspace)
    registry = ToolRegistry()
    registry.register_tool(RAGTool(rag))
    registry.register_tool(MemoryTool(memory))
    # 显式选取组件；不为此例注册文件工具、子代理或其他写入能力。
    config = Config(
        trace_enabled=False,
        session_enabled=False,
        skills_enabled=False,
        subagent_enabled=False,
        todowrite_enabled=False,
        devlog_enabled=False,
    )
    agent = SimpleAgent(
        "旅行助手",
        HelloAgentsLLM(),
        config=config,
        tool_registry=registry,
        max_tool_iterations=6,
        system_prompt="使用教学资料与当前偏好规划；检索后标注来源和版本。不编造缺失信息。",
        context_builder=ContextBuilder(ContextConfig(max_tokens=8000)),
        context_providers=[MemoryContextProvider(memory, required=True)],
    )
    print(
        agent.run(
            "为杭州示例博物馆与湖畔公共步道安排两日行程。先查预约和交通，遵守我的步行限制。"
        )
    )
    print(json.dumps(agent.last_context_diagnostics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["local", "resume", "live"], default="local")
    parser.add_argument("--workspace", type=Path, default=Path(".hello-agents/travel"))
    args = parser.parse_args()
    {"local": local, "resume": resume, "live": live}[args.mode](args.workspace)
