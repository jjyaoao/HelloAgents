

# HelloAgents - PyPI Ready 框架结构

## 项目根目录结构

```
hello-agents/
├── hello_agents/                  # 主包目录
│   ├── __init__.py               # 包初始化，导出核心API
│   ├── version.py                # 版本信息
│   │
│   ├── core/                     # 第7章：核心框架
│   │   ├── __init__.py
│   │   ├── agent.py              # Agent基类
│   │   ├── llm.py                # HelloAgentsLLM统一接口
│   │   ├── message.py            # 消息系统
│   │   ├── registry.py           # 全局注册中心
│   │   ├── config.py             # 配置管理
│   │   └── exceptions.py         # 异常体系
│   │
│   ├── agents/                   # 第7章：Agent实现
│   │   ├── __init__.py
│   │   ├── simple.py             # 简单Agent
│   │   ├── tool_agent.py         # 工具Agent
│   │   └── conversational.py     # 对话Agent
│   │
│   ├── tools/                    # 第7章：工具系统
│   │   ├── __init__.py
│   │   ├── base.py               # 工具基类
│   │   ├── registry.py           # 工具注册
│   │   └── builtin/              # 内置工具
│   │       ├── __init__.py
│   │       ├── search.py
│   │       ├── calculator.py
│   │       └── web_browser.py
│   │
│   ├── context/                  # 第8章：上下文工程
│   │   ├── __init__.py
│   │   ├── templates.py          # 提示词模板
│   │   ├── manager.py            # 上下文管理器
│   │   ├── compression.py        # 上下文压缩
│   │   ├── retrieval.py          # 上下文检索
│   │   └── optimization.py       # 上下文优化
│   │
│   ├── memory/                   # 第9章：记忆与RAG
│   │   ├── __init__.py
│   │   ├── base.py               # 记忆基类
│   │   ├── working.py            # 工作记忆
│   │   ├── vector.py             # 向量记忆
│   │   └── rag/                  # RAG系统
│   │       ├── __init__.py
│   │       ├── retriever.py
│   │       ├── embeddings.py
│   │       └── vector_store.py
│   │
│   ├── protocols/                # 第10章：通信协议
│   │   ├── __init__.py
│   │   ├── mcp/                  # Model Context Protocol
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   ├── server.py
│   │   │   └── tools.py
│   │   ├── a2a/                  # Agent-to-Agent
│   │   │   ├── __init__.py
│   │   │   ├── messaging.py
│   │   │   └── negotiation.py
│   │   └── anp/                  # Agent Network Protocol
│   │       ├── __init__.py
│   │       ├── discovery.py
│   │       └── routing.py
│   │
│   ├── orchestration/            # 第11章：多智能体编排
│   │   ├── __init__.py
│   │   ├── sequential.py
│   │   ├── parallel.py
│   │   ├── hierarchical.py
│   │   ├── debate.py
│   │   └── consensus.py
│   │
│   ├── evaluation/               # 第12章：评估指标
│   │   ├── __init__.py
│   │   ├── metrics/
│   │   │   ├── __init__.py
│   │   │   ├── accuracy.py
│   │   │   ├── efficiency.py
│   │   │   ├── robustness.py
│   │   │   └── collaboration.py
│   │   ├── benchmarks/
│   │   │   ├── __init__.py
│   │   │   ├── single_agent.py
│   │   │   └── multi_agent.py
│   │   └── reporting.py
│   │
│   └── utils/                    # 通用工具
│       ├── __init__.py
│       ├── logging.py
│       ├── serialization.py
│       └── helpers.py
│
├── examples/                     # 教学示例（不打包）
│   ├── chapter07_basic_setup.py
│   ├── chapter08_context_engineering.py
│   ├── chapter09_memory_rag.py
│   ├── chapter10_protocols.py
│   ├── chapter11_orchestration.py
│   └── chapter12_evaluation.py
│
├── tests/                        # 测试用例
│   ├── __init__.py
│   ├── test_core/
│   ├── test_agents/
│   ├── test_tools/
│   └── ...
│
├── docs/                         # 文档
│   ├── api/                      # API文档
│   ├── tutorials/                # 教程
│   └── examples/                 # 示例文档
│
├── setup.py                      # 安装配置
├── pyproject.toml                # 现代Python项目配置
├── requirements.txt              # 依赖
├── README.md                     # 项目说明
├── LICENSE                       # 许可证
└── MANIFEST.in                   # 打包配置
```

## 核心API设计（hello_agents/__init__.py）

```python
# 核心导出，用户友好的API
from .core.agent import Agent
from .core.llm import HelloAgentsLLM
from .core.message import Message
from .core.config import Config

# 常用Agent类型
from .agents.simple import SimpleAgent
from .agents.tool_agent import ToolAgent
from .agents.conversational import ConversationalAgent

# 工具系统
from .tools.base import Tool
from .tools.registry import ToolRegistry

# 记忆系统
from .memory.working import WorkingMemory
from .memory.vector import VectorMemory

# 编排系统
from .orchestration.sequential import SequentialOrchestrator
from .orchestration.parallel import ParallelOrchestrator

__version__ = "0.1.0"
__all__ = [
    "Agent", "HelloAgentsLLM", "Message", "Config",
    "SimpleAgent", "ToolAgent", "ConversationalAgent",
    "Tool", "ToolRegistry",
    "WorkingMemory", "VectorMemory",
    "SequentialOrchestrator", "ParallelOrchestrator"
]
```

## 使用示例

```python
# 简单易用的API
from hello_agents import SimpleAgent, HelloAgentsLLM

# 创建LLM
llm = HelloAgentsLLM(
    model="gpt-4",
    api_key="your-key"
)

# 创建Agent
agent = SimpleAgent(
    name="assistant",
    llm=llm
)

# 使用
response = agent.run("Hello, world!")


