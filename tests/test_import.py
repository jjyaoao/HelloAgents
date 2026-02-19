"""测试包与主要导出能否正常导入（使用子模块导入，避免拉取可选依赖）。"""

import pytest


def test_import_version():
    from hello_agents.version import __version__
    assert __version__ and isinstance(__version__, str)


def test_import_core():
    from hello_agents.core.config import Config
    from hello_agents.core.message import Message
    from hello_agents.core.exceptions import HelloAgentsException
    from hello_agents.core.llm import HelloAgentsLLM
    assert Config is not None
    assert Message is not None
    assert HelloAgentsException is not None
    assert HelloAgentsLLM is not None


def test_import_simple_agent():
    from hello_agents.agents.simple_agent import SimpleAgent
    assert SimpleAgent is not None


def test_import_tools():
    from hello_agents.tools.registry import ToolRegistry
    from hello_agents.tools.builtin.calculator import CalculatorTool
    assert ToolRegistry is not None
    assert CalculatorTool is not None
