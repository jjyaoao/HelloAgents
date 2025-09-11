# HelloAgents

这是一个基于 Python 的多智能体框架。

## 目录结构

```
HelloAgents/
├── core/                  # 核心抽象和执行引擎
│   ├── agent.py           # Agent的定义
│   ├── state.py           # 状态对象的定义
│   ├── graph.py           # 工作流图的构建器
│   ├── node.py            # 图中节点（操作单元）的定义
│   └── tool.py            # 工具的基类和装饰器
│
├── components/            # 可插拔的模块和实现
│   ├── llms/              # 对接不同LLM的实现
│   ├── memory/            # 不同记忆机制的实现
│   ├── parsers/           # 输出解析器
│   └── retrievers/        # 检索器（用于RAG）
│
├── teams/                 # 多智能体协作相关
│   ├── team.py            # 智能体团队的定义
│   ├── router.py          # 任务分发器
│   └── communication.py   # 智能体间通信协议
│
├── evaluators/            # 性能与伦理评估
│   ├── benchmark.py       # 基准测试套件
│   └── safety.py          # 安全与伦理护栏
│
└── examples/              # 使用框架的具体案例
    ├── 01_simple_assistant.py
    ├── 02_rag_agent.py
    └── 03_multi_agent_research.py
```

## 快速开始

(即将推出)
