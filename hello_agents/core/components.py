"""Agent 组件的显式注入与默认装配，不提供全局容器或插件生命周期。"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, TYPE_CHECKING, Union

from .config import Config
from .message import Message

if TYPE_CHECKING:
    from .agent import Agent
    from ..skills.loader import Skill


class HistoryProtocol(Protocol):
    min_retain_rounds: int

    def append(self, message: Message) -> None: ...
    def get_history(self) -> List[Message]: ...
    def clear(self) -> None: ...
    def compress(self, summary: str) -> None: ...
    def estimate_rounds(self) -> int: ...
    def find_round_boundaries(self) -> List[int]: ...


class TokenCounterProtocol(Protocol):
    def count_message(self, message: Message) -> int: ...
    def count_messages(self, messages: List[Message]) -> int: ...
    def clear_cache(self) -> None: ...


class TruncatorProtocol(Protocol):
    def truncate(self, tool_name: str, output: str) -> Dict[str, Any]: ...


class SessionStoreProtocol(Protocol):
    def save(
        self,
        agent_config: Dict[str, Any],
        history: List[Message],
        tool_schema_hash: str,
        read_cache: Dict[str, Dict],
        metadata: Dict[str, Any],
        session_name: Optional[str] = None,
    ) -> str: ...
    def load(self, filepath: str) -> Dict[str, Any]: ...
    def list_sessions(self) -> List[Dict[str, Any]]: ...
    def check_config_consistency(
        self,
        saved_config: Dict[str, Any],
        current_config: Dict[str, Any],
    ) -> Dict[str, Any]: ...
    def check_tool_schema_consistency(
        self, saved_hash: str, current_hash: str
    ) -> Dict[str, Any]: ...


class SkillLoaderProtocol(Protocol):
    def get_descriptions(self) -> str: ...
    def get_skill(self, name: str) -> Optional["Skill"]: ...
    def list_skills(self) -> List[str]: ...


class _DefaultComponent(Enum):
    VALUE = "use_config_default"


DEFAULT_COMPONENT = _DefaultComponent.VALUE


@dataclass
class AgentComponents:
    """构造时覆盖指定组件；所有实例由宿主管理生命周期。

    必需组件的 None 表示创建默认实例。可选 session_store / skill_loader：
    DEFAULT_COMPONENT 根据 Config 创建，None 显式禁用，实例显式替换。
    """

    summary_llm: Any = None
    subagent_llm: Any = None
    history_manager: Optional[HistoryProtocol] = None
    token_counter: Optional[TokenCounterProtocol] = None
    truncator: Optional[TruncatorProtocol] = None
    session_store: Union[SessionStoreProtocol, None, _DefaultComponent] = (
        DEFAULT_COMPONENT
    )
    skill_loader: Union[SkillLoaderProtocol, None, _DefaultComponent] = (
        DEFAULT_COMPONENT
    )


@dataclass(frozen=True)
class ResolvedAgentComponents:
    history_manager: HistoryProtocol
    token_counter: TokenCounterProtocol
    truncator: TruncatorProtocol
    session_store: Optional[SessionStoreProtocol]
    skill_loader: Optional[SkillLoaderProtocol]


_METHODS = {
    "history_manager": (
        "append",
        "get_history",
        "clear",
        "compress",
        "estimate_rounds",
        "find_round_boundaries",
    ),
    "token_counter": ("count_message", "count_messages", "clear_cache"),
    "truncator": ("truncate",),
    "session_store": (
        "save",
        "load",
        "list_sessions",
        "check_config_consistency",
        "check_tool_schema_consistency",
    ),
    "skill_loader": ("get_descriptions", "get_skill", "list_skills"),
}


def build_agent_components(
    config: Config,
    model: str,
    components: Optional[AgentComponents] = None,
) -> ResolvedAgentComponents:
    """解析注入项，未指定的组件按 Config 装配；不覆盖传入实例状态。"""
    if components is not None and not isinstance(components, AgentComponents):
        raise TypeError("components 必须是 AgentComponents 或 None")
    requested = components if components is not None else AgentComponents()

    # 先校验宿主对象，避免发现无效注入前已经创建默认存储目录。
    for name, methods in _METHODS.items():
        value = getattr(requested, name)
        if value is None:
            continue
        if name in {"session_store", "skill_loader"} and value is DEFAULT_COMPONENT:
            continue
        missing = [
            method for method in methods if not callable(getattr(value, method, None))
        ]
        if missing:
            raise TypeError(f"组件 {name} 缺少方法：{', '.join(missing)}")
        if name == "history_manager":
            retained = getattr(value, "min_retain_rounds", None)
            if type(retained) is not int or retained < 1:
                raise ValueError("history_manager.min_retain_rounds 必须是正整数")

    from ..context.history import HistoryManager
    from ..context.token_counter import TokenCounter
    from ..context.truncator import ObservationTruncator
    from ..skills.loader import SkillLoader
    from .session_store import SessionStore

    history = requested.history_manager
    if history is None:
        history = HistoryManager(config.min_retain_rounds, config.compression_threshold)
    counter = requested.token_counter
    if counter is None:
        counter = TokenCounter(model=model)
    truncator = requested.truncator
    if truncator is None:
        truncator = ObservationTruncator(
            max_lines=config.tool_output_max_lines,
            max_bytes=config.tool_output_max_bytes,
            truncate_direction=config.tool_output_truncate_direction,
            output_dir=config.tool_output_dir,
        )
    session = requested.session_store
    if session is DEFAULT_COMPONENT:
        session = SessionStore(config.session_dir) if config.session_enabled else None
    skills = requested.skill_loader
    if skills is DEFAULT_COMPONENT:
        skills = SkillLoader(config.skills_dir) if config.skills_enabled else None
    return ResolvedAgentComponents(history, counter, truncator, session, skills)


def register_default_tools(agent: "Agent") -> None:
    """按显式配置装配可选工具；显式禁用组件后不自动创建替代实例。"""
    if agent.tool_registry is None:
        return
    existing = set(agent.tool_registry.list_tools())
    if (
        agent.skill_loader is not None
        and agent.config.skills_auto_register
        and "Skill" not in existing
    ):
        from ..tools.builtin.skill_tool import SkillTool

        agent.tool_registry.register_tool(SkillTool(skill_loader=agent.skill_loader))
    if agent.config.subagent_enabled and "Task" not in existing:
        agent._register_task_tool()
    if agent.config.todowrite_enabled and "TodoWrite" not in existing:
        agent._register_todowrite_tool()
    if agent.config.devlog_enabled and "DevLog" not in existing:
        agent._register_devlog_tool()
