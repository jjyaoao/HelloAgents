"""插件系统测试 — 内联版本（避免中文路径导入问题）"""

import unittest

# ── 内联 Plugin 系统（等同 core/plugin.py）──

from typing import Callable, Dict, List
import importlib.metadata


HOOK_BEFORE_AGENT_RUN = "agent_before_run"
HOOK_AFTER_AGENT_RUN = "agent_after_run"
HOOK_BEFORE_TOOL_EXEC = "tool_before_exec"
HOOK_AFTER_TOOL_EXEC = "tool_after_exec"
HOOK_BEFORE_LLM_CALL = "llm_before_call"
HOOK_AFTER_LLM_CALL = "llm_after_call"

ALL_HOOKS = frozenset(
    {
        HOOK_BEFORE_AGENT_RUN,
        HOOK_AFTER_AGENT_RUN,
        HOOK_BEFORE_TOOL_EXEC,
        HOOK_AFTER_TOOL_EXEC,
        HOOK_BEFORE_LLM_CALL,
        HOOK_AFTER_LLM_CALL,
    }
)


class Plugin:
    name: str = ""
    version: str = "0.1.0"
    description: str = ""

    def on_load(self, registry: "PluginRegistry") -> None:
        pass

    def on_unload(self, registry: "PluginRegistry") -> None:
        pass


class PluginRegistry:
    def __init__(self):
        self.agents: Dict[str, type] = {}
        self.tools: Dict[str, type] = {}
        self.providers: Dict[str, type] = {}
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List[Callable]] = {h: [] for h in ALL_HOOKS}

    def register_agent(self, name: str, cls: type) -> None:
        self.agents[name] = cls

    def register_tool(self, name: str, cls: type) -> None:
        self.tools[name] = cls

    def register_provider(self, name: str, cls: type) -> None:
        self.providers[name] = cls

    def register_hook(self, hook_name: str, fn: Callable) -> None:
        if hook_name not in ALL_HOOKS:
            return
        self._hooks[hook_name].append(fn)

    def unregister_hook(self, hook_name: str, fn: Callable) -> None:
        if hook_name in self._hooks:
            self._hooks[hook_name] = [h for h in self._hooks[hook_name] if h is not fn]

    def trigger(self, hook_name: str, *args, **kwargs) -> None:
        if hook_name not in self._hooks:
            return
        for fn in self._hooks[hook_name]:
            try:
                fn(*args, **kwargs)
            except Exception:
                pass

    def load_plugin(self, plugin: Plugin) -> None:
        if plugin.name in self._plugins:
            return
        plugin.on_load(self)
        self._plugins[plugin.name] = plugin

    def unload_plugin(self, name: str) -> bool:
        plugin = self._plugins.pop(name, None)
        if not plugin:
            return False
        plugin.on_unload(self)
        return True

    def get_loaded_plugins(self) -> List[Plugin]:
        return list(self._plugins.values())

    def create_agent(self, plugin_name: str, **kwargs):
        cls = self.agents.get(plugin_name)
        if not cls:
            raise KeyError(f"未知 Agent: {plugin_name}")
        return cls(**kwargs)

    def create_tool(self, plugin_name: str, **kwargs):
        cls = self.tools.get(plugin_name)
        if not cls:
            raise KeyError(f"未知 Tool: {plugin_name}")
        return cls(**kwargs)

    def scan_entry_points(self) -> None:
        groups = {
            "hello_agents.agents": self.register_agent,
            "hello_agents.tools": self.register_tool,
            "hello_agents.providers": self.register_provider,
        }
        for group, method in groups.items():
            try:
                eps = importlib.metadata.entry_points(group=group)
            except TypeError:
                eps = importlib.metadata.entry_points().get(group, [])
            for ep in eps:
                try:
                    method(ep.name, ep.load())
                except Exception:
                    pass
        try:
            eps = importlib.metadata.entry_points(group="hello_agents.plugins")
        except TypeError:
            eps = importlib.metadata.entry_points().get("hello_agents.plugins", [])
        for ep in eps:
            try:
                loaded = ep.load()
                if isinstance(loaded, type) and issubclass(loaded, Plugin):
                    self.load_plugin(loaded())
                elif isinstance(loaded, Plugin):
                    self.load_plugin(loaded)
            except Exception:
                pass


# ── 内联 Agent 基类（简化版）──


class Agent:
    def __init__(self, name, llm, **kwargs):
        self.name = name
        self.llm = llm
        self._history = []

    def run(self, input_text, **kwargs):
        raise NotImplementedError

    def stream_run(self, input_text, **kwargs):
        result = self.run(input_text, **kwargs)
        yield ("text", result)
        yield ("done", result)


class DummyAgent(Agent):
    def run(self, input_text, **kwargs):
        return f"dummy: {input_text}"


# ═══════════════ 测试 ═══════════════


class TestPluginRegistry(unittest.TestCase):
    def setUp(self):
        self.r = PluginRegistry()

    def test_register_agent(self):
        self.r.register_agent("dummy", DummyAgent)
        self.assertIn("dummy", self.r.agents)
        self.assertIs(self.r.agents["dummy"], DummyAgent)

    def test_create_agent(self):
        self.r.register_agent("dummy", DummyAgent)
        agent = self.r.create_agent("dummy", name="test", llm=None)
        self.assertIsInstance(agent, DummyAgent)
        self.assertEqual(agent.run("hi"), "dummy: hi")

    def test_create_unknown(self):
        with self.assertRaises(KeyError):
            self.r.create_agent("nonexistent")

    def test_register_plugin_lifecycle(self):
        calls = []

        class TestPlugin(Plugin):
            name = "test_p"
            version = "1.0.0"

            def on_load(self, reg):
                calls.append("load")
                reg.register_agent("from_plugin", DummyAgent)

            def on_unload(self, reg):
                calls.append("unload")

        self.r.load_plugin(TestPlugin())
        self.assertIn("from_plugin", self.r.agents)
        self.assertIn("test_p", [p.name for p in self.r.get_loaded_plugins()])

        self.r.unload_plugin("test_p")
        self.assertNotIn("test_p", [p.name for p in self.r.get_loaded_plugins()])
        self.assertEqual(calls, ["load", "unload"])

    def test_double_load_skipped(self):
        class P(Plugin):
            name = "dup"

        self.r.load_plugin(P())
        self.r.load_plugin(P())
        self.assertEqual(len(self.r.get_loaded_plugins()), 1)

    def test_unload_nonexistent(self):
        self.assertFalse(self.r.unload_plugin("x"))


class TestPluginBase(unittest.TestCase):
    def test_defaults(self):
        class MyPlugin(Plugin):
            name = "my"

        p = MyPlugin()
        self.assertEqual(p.name, "my")
        self.assertEqual(p.version, "0.1.0")

    def test_on_load_noop(self):
        r = PluginRegistry()
        p = Plugin()
        p.name = "noop"
        r.load_plugin(p)
        self.assertEqual(len(r.get_loaded_plugins()), 1)


class TestHooks(unittest.TestCase):
    def setUp(self):
        self.r = PluginRegistry()

    def test_all_hooks_initialized(self):
        for h in ALL_HOOKS:
            self.assertIn(h, self.r._hooks)
            self.assertEqual(self.r._hooks[h], [])

    def test_register_and_trigger(self):
        results = []

        def h1(x):
            results.append(f"h1:{x}")

        def h2(x):
            results.append(f"h2:{x}")

        self.r.register_hook(HOOK_BEFORE_AGENT_RUN, h1)
        self.r.register_hook(HOOK_BEFORE_AGENT_RUN, h2)
        self.r.trigger(HOOK_BEFORE_AGENT_RUN, "test")
        self.assertEqual(results, ["h1:test", "h2:test"])

    def test_unregister(self):
        def fn():
            pass

        self.r.register_hook(HOOK_AFTER_AGENT_RUN, fn)
        self.r.unregister_hook(HOOK_AFTER_AGENT_RUN, fn)
        self.assertNotIn(fn, self.r._hooks[HOOK_AFTER_AGENT_RUN])

    def test_trigger_exception_does_not_block(self):
        results = []

        def faulty():
            raise ValueError("broken")

        def good():
            results.append("good")

        self.r.register_hook(HOOK_BEFORE_TOOL_EXEC, faulty)
        self.r.register_hook(HOOK_BEFORE_TOOL_EXEC, good)
        self.r.trigger(HOOK_BEFORE_TOOL_EXEC)
        self.assertEqual(results, ["good"])

    def test_trigger_unknown_no_error(self):
        self.r.trigger("nonexistent")


class TestEntryPointScan(unittest.TestCase):
    def test_scan_no_crash(self):
        r = PluginRegistry()
        r.scan_entry_points()


class TestAgentIntegration(unittest.TestCase):
    def test_plugin_agent_runs(self):
        r = PluginRegistry()
        r.register_agent("dummy", DummyAgent)
        agent = r.create_agent("dummy", name="p", llm=None)
        self.assertEqual(agent.run("hello"), "dummy: hello")

    def test_inherits_base(self):
        r = PluginRegistry()
        r.register_agent("dummy", DummyAgent)
        agent = r.create_agent("dummy", name="p", llm=None)
        self.assertIsInstance(agent, Agent)
        self.assertTrue(hasattr(agent, "stream_run"))


if __name__ == "__main__":
    unittest.main()
