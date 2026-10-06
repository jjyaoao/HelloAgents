"""通过临时会话状态，将空闲 Agent 复用为子任务执行器。"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime

_MISSING = object()
_STATE = (
    "tool_registry", "session_store", "_history_token_count", "_session_metadata",
    "_messages_since_save", "_start_time", "max_steps", "max_tool_iterations",
    "last_run", "last_context_diagnostics",
)


@contextmanager
def subagent_scope(agent, tool_filter=None, max_steps=None):
    """始终恢复父 Agent 状态，结果处理失败时也不例外。

    复制注册名称与读取元数据；工具实例及其外部
    修改仍然共享。在该作用域内禁用父会话持久化。
    同一 Agent 实例不能并发使用此作用域。
    """
    if getattr(agent, "_run_active", False):
        raise RuntimeError("运行中的 Agent 不能复用为子代理，请创建独立实例")
    if max_steps is not None and (type(max_steps) is not int or max_steps < 1):
        raise ValueError("max_steps_override 必须是正整数")
    history = list(agent.history_manager.get_history())
    state = {name: getattr(agent, name, _MISSING) for name in _STATE}
    registry = agent.tool_registry
    # 修改状态前，先校验过滤器并构造隔离的映射。
    if registry is not None:
        names = tool_filter.filter(registry.list_tools()) if tool_filter is not None else None
        registry = registry.fork(names)
    metadata = deepcopy(agent._session_metadata)
    try:
        agent.tool_registry = registry
        agent.session_store = None
        agent._session_metadata = metadata
        agent._start_time = datetime.now()
        agent._messages_since_save = 0
        agent.history_manager.clear()
        agent._history_token_count = 0
        if max_steps is not None:
            for name in ("max_steps", "max_tool_iterations"):
                if state[name] is not _MISSING:
                    setattr(agent, name, max_steps)
        yield
    finally:
        try:
            agent.history_manager.clear()
            for message in history:
                agent.history_manager.append(message)
        finally:
            # 即使注入的历史组件发生故障，也要恢复控制配置。
            for name, value in state.items():
                if value is _MISSING:
                    if hasattr(agent, name):
                        delattr(agent, name)
                else:
                    setattr(agent, name, value)
