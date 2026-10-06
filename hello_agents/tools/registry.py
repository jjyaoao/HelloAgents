"""工具注册表 - HelloAgents原生工具系统"""

from typing import Optional, Any, Callable, Dict, Iterable
import time
import asyncio
import inspect
import json
from copy import deepcopy
from .base import Tool
from .response import ToolResponse, ToolStatus
from .errors import ToolErrorCode
from .circuit_breaker import CircuitBreaker


class ToolRegistry:
    """
    HelloAgents工具注册表

    提供工具的注册、管理和执行功能。
    支持两种工具注册方式：
    1. Tool对象注册（推荐）
    2. 函数直接注册（简便）
    """

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None, *, policy=None):
        if policy is not None and not callable(policy):
            raise TypeError("policy must be callable")
        self.policy = policy
        self._tools: dict[str, Tool] = {}
        self._functions: dict[str, dict[str, Any]] = {}

        # 文件元数据缓存（用于乐观锁机制）
        self.read_metadata_cache: Dict[str, Dict[str, Any]] = {}

        # 熔断器（默认启用）
        self.circuit_breaker = (
            circuit_breaker if circuit_breaker is not None else CircuitBreaker()
        )

    def fork(self, names: Optional[Iterable[str]] = None) -> "ToolRegistry":
        """复制可用名称映射，保留选定工具/函数实例和共享熔断状态。

        注册、替换或删除子表名称不会改变父表。工具内部状态不隔离；
        文件读取元数据复制为独立字典，避免子表缓存修改影响父表。
        未知名称拒绝，函数与 Tool 使用相同的过滤规则。
        """
        from copy import deepcopy

        available = self._tools.keys() | self._functions.keys()
        if names is None:
            selected = list(self._tools) + list(self._functions)
        else:
            if isinstance(names, str):
                raise TypeError("names 必须是名称序列，不能是单个字符串")
            selected = list(names)
            if any(not isinstance(name, str) for name in selected):
                raise TypeError("names 的每一项必须是字符串")
            unknown = set(selected) - available
            if unknown:
                raise ValueError(f"未注册的工具名称: {', '.join(sorted(unknown))}")
        child = ToolRegistry(circuit_breaker=self.circuit_breaker, policy=self.policy)
        child._tools = {
            name: self._tools[name] for name in selected if name in self._tools
        }
        child._functions = {
            name: dict(self._functions[name])
            for name in selected
            if name in self._functions
        }
        child.read_metadata_cache = deepcopy(self.read_metadata_cache)
        return child

    def _prepare_names(self, names, replace=False):
        if any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValueError("工具名称必须是非空字符串")
        if len(set(names)) != len(names):
            raise ValueError("展开后的工具名称重复")
        collisions = set(names) & (self._tools.keys() | self._functions.keys())
        if collisions and not replace:
            raise ValueError(
                f"工具名称已注册: {', '.join(sorted(collisions))}；替换请显式指定 replace=True"
            )
        for name in collisions:
            self.unregister(name)

    def register_tool(
        self, tool: Tool, auto_expand: bool = True, *, replace: bool = False
    ):
        """
        注册Tool对象

        Args:
            tool: Tool实例
            auto_expand: 是否自动展开可展开的工具（默认True）
            replace: 是否显式替换已注册的同名实现，默认拒绝撞名
        """
        # 检查工具是否可展开
        if auto_expand and hasattr(tool, "expandable") and tool.expandable:
            expanded_tools = tool.get_expanded_tools()
            if expanded_tools:
                for sub_tool in expanded_tools:
                    sub_tool.to_openai_schema()
                self._prepare_names(
                    [sub_tool.name for sub_tool in expanded_tools], replace
                )
                # 注册所有展开的子工具
                for sub_tool in expanded_tools:
                    self._tools[sub_tool.name] = sub_tool
                print(
                    f"✅ 工具 '{tool.name}' 已展开为 {len(expanded_tools)} 个独立工具"
                )
                return

        # 普通工具或不展开的工具
        tool.to_openai_schema()
        self._prepare_names([tool.name], replace)
        self._tools[tool.name] = tool
        print(f"✅ 工具 '{tool.name}' 已注册。")

    def register_function(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        *,
        replace: bool = False,
    ):
        """
        直接注册函数作为工具（简便方式）

        支持两种调用方式：
        1. 传统方式：register_function(name, description, func)
        2. 新方式：register_function(func, name=None, description=None)
           - 自动从函数名和 docstring 提取信息

        Args:
            func: 工具函数
            name: 工具名称（可选，默认使用函数名）
            description: 工具描述（可选，默认使用函数 docstring）
            replace: 是否显式替换同名工具或函数，默认拒绝撞名

        使用示例:
            >>> def my_tool(input: str) -> str:
            ...     '''这是我的工具'''
            ...     return f"处理: {input}"
            >>> registry.register_function(my_tool)
            >>> # 或者指定名称和描述
            >>> registry.register_function(my_tool, name="custom_name", description="自定义描述")
        """
        # 兼容旧的调用方式：register_function(name, description, func)
        if isinstance(func, str) and callable(description):
            # 旧方式：第一个参数是 name，第二个是 description，第三个是 func
            name, description, func = func, name, description

        if not callable(func):
            raise TypeError("func 必须可调用")

        # 自动提取名称
        if name is None:
            name = getattr(func, "__name__", type(func).__name__)

        # 自动提取描述
        if description is None:
            import inspect

            doc = inspect.getdoc(func)
            if doc:
                # 提取第一行作为描述
                description = doc.split("\n")[0].strip()
            else:
                description = f"执行 {name}"

        self._prepare_names([name], replace)

        self._functions[name] = {"description": description, "func": func}
        print(f"✅ 函数工具 '{name}' 已注册。")

    def unregister(self, name: str):
        """注销工具"""
        if name in self._tools or name in self._functions:
            self._tools.pop(name, None)
            self._functions.pop(name, None)
            self.circuit_breaker.close(name)
            print(f"🗑️ 工具 '{name}' 已注销。")
        else:
            print(f"⚠️ 工具 '{name}' 不存在。")

    def get_tool(self, name: str) -> Optional[Tool]:
        """获取Tool对象"""
        return self._tools.get(name)

    def get_function(self, name: str) -> Optional[Callable]:
        """获取工具函数"""
        func_info = self._functions.get(name)
        return func_info["func"] if func_info else None

    @staticmethod
    def _parameters(input_text: Any) -> Dict[str, Any]:
        if isinstance(input_text, str):
            try:
                parameters = json.loads(input_text)
            except json.JSONDecodeError:
                return {"input": input_text}
            if not isinstance(parameters, dict):
                raise ValueError("工具参数 JSON 必须是对象")
            return parameters
        if isinstance(input_text, dict):
            return input_text
        return {"input": str(input_text)}

    def _blocked(self, name):
        if not self.circuit_breaker.is_open(name):
            return None
        status = self.circuit_breaker.get_status(name)
        return ToolResponse.error(
            ToolErrorCode.CIRCUIT_OPEN,
            f"工具 '{name}' 当前被禁用，由于连续失败。{status['recover_in_seconds']} 秒后可用。",
            context={"tool_name": name, "circuit_status": status},
        )

    def _authorize(self, name, input_text):
        from copy import deepcopy
        from .permissions import PermissionDecision

        if self.policy is None:
            return None
        try:
            arguments = self._parameters(input_text) if name in self._tools else input_text
            decision = self.policy(name, deepcopy(arguments))
            if inspect.isawaitable(decision):
                if inspect.iscoroutine(decision):
                    decision.close()
                raise TypeError("Tool policies must be synchronous; resolve approvals in the host")
            if not isinstance(decision, PermissionDecision):
                raise TypeError("policy must return PermissionDecision")
        except Exception:
            # 权限检查发生故障时，不能意外放行会产生副作用的操作。
            return ToolResponse.error(ToolErrorCode.PERMISSION_DENIED,
                                      "Host policy evaluation failed; tool was not executed")
        if not decision.allowed:
            return ToolResponse.error(ToolErrorCode.PERMISSION_DENIED,
                                      decision.reason or "Host denied this operation")
        return None

    @staticmethod
    def _function_response(result, name, input_text, started):
        response = (
            result
            if isinstance(result, ToolResponse)
            else ToolResponse.success(text=str(result), data={"output": result})
        )
        response.stats = dict(response.stats or {})
        response.stats["time_ms"] = int((time.perf_counter() - started) * 1000)
        response.context = dict(response.context or {})
        response.context.update(tool_name=name, input=input_text)
        return response

    def execute_tool(self, name: str, input_text: Any) -> ToolResponse:
        """
        执行工具，返回 ToolResponse 对象（带熔断器保护）

        Args:
            name: 工具名称
            input_text: 输入参数

        Returns:
            ToolResponse: 标准化的工具响应对象
        """
        if self.policy is not None:
            try:
                input_text = deepcopy(input_text)
            except Exception:
                return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "Cannot snapshot tool input for authorization")
        denied = self._authorize(name, input_text)
        if denied is not None:
            return denied
        # 检查熔断器
        blocked = self._blocked(name)
        if blocked is not None:
            return blocked

        # 执行工具
        response = None

        # 优先查找Tool对象（新协议）
        if name in self._tools:
            tool = self._tools[name]
            try:
                # 解析参数（支持 JSON 字符串或字典）
                parameters = self._parameters(input_text)

                # 使用 run_with_timing 自动添加时间统计
                response = tool.run_with_timing(parameters)
            except ValueError as e:
                response = ToolResponse.error(ToolErrorCode.INVALID_PARAM, str(e))
            except Exception as e:
                response = ToolResponse.error(
                    code=ToolErrorCode.EXECUTION_ERROR,
                    message=f"执行工具 '{name}' 时发生异常: {str(e)}",
                    context={"tool_name": name, "input": input_text},
                )

        # 查找函数工具（自动包装为新协议）
        elif name in self._functions:
            func = self._functions[name]["func"]
            start_time = time.perf_counter()

            try:
                if inspect.iscoroutinefunction(func) or inspect.iscoroutinefunction(
                    getattr(func, "__call__", None)
                ):
                    response = ToolResponse.error(
                        ToolErrorCode.INVALID_PARAM,
                        "异步函数必须通过 aexecute_tool 调用",
                    )
                else:
                    result = func(input_text)
                    if inspect.isawaitable(result):
                        if inspect.iscoroutine(result):
                            result.close()
                        response = ToolResponse.error(
                            ToolErrorCode.INVALID_PARAM,
                            "函数返回 awaitable，请通过 aexecute_tool 调用",
                        )
                    else:
                        response = self._function_response(
                            result, name, input_text, start_time
                        )
            except Exception as e:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                response = ToolResponse.error(
                    code=ToolErrorCode.EXECUTION_ERROR,
                    message=f"函数执行失败: {str(e)}",
                    stats={"time_ms": elapsed_ms},
                    context={"tool_name": name, "input": input_text},
                )

        # 工具不存在
        else:
            response = ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message=f"未找到名为 '{name}' 的工具",
                context={"tool_name": name},
            )

        # 记录熔断器结果
        self.circuit_breaker.record_result(name, response)

        return response

    async def aexecute_tool(self, name: str, input_text: Any) -> ToolResponse:
        """异步执行使用同一注册表熔断状态；原生异步 Tool 不降级成同步。

        函数式工具沿用现有 input 约定，在工作线程中执行。
        并发调用开始后，已在运行的工具不会被随后开启的熔断取消。
        """
        if self.policy is not None:
            try:
                input_text = deepcopy(input_text)
            except Exception:
                return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "Cannot snapshot tool input for authorization")
        denied = self._authorize(name, input_text)
        if denied is not None:
            return denied
        blocked = self._blocked(name)
        if blocked is not None:
            return blocked
        started = time.perf_counter()
        try:
            if name in self._tools:
                try:
                    parameters = self._parameters(input_text)
                except ValueError as exc:
                    response = ToolResponse.error(ToolErrorCode.INVALID_PARAM, str(exc))
                else:
                    response = await self._tools[name].arun_with_timing(parameters)
            elif name in self._functions:
                func = self._functions[name]["func"]
                if inspect.iscoroutinefunction(func) or inspect.iscoroutinefunction(
                    getattr(func, "__call__", None)
                ):
                    result = await func(input_text)
                else:
                    result = await asyncio.to_thread(func, input_text)
                    if inspect.isawaitable(result):
                        result = await result
                response = self._function_response(result, name, input_text, started)
            else:
                response = ToolResponse.error(
                    ToolErrorCode.NOT_FOUND, f"未找到名为 '{name}' 的工具"
                )
        except Exception as exc:
            response = ToolResponse.error(ToolErrorCode.EXECUTION_ERROR, str(exc))
        self.circuit_breaker.record_result(name, response)
        return response

    def get_tools_description(self) -> str:
        """
        获取所有可用工具的格式化描述字符串

        Returns:
            工具描述字符串，用于构建提示词
        """
        descriptions = []

        # Tool对象描述
        for tool in self._tools.values():
            descriptions.append(f"- {tool.name}: {tool.description}")

        # 函数工具描述
        for name, info in self._functions.items():
            descriptions.append(f"- {name}: {info['description']}")

        return "\n".join(descriptions) if descriptions else "暂无可用工具"

    def list_tools(self) -> list[str]:
        """列出所有工具名称"""
        return list(self._tools.keys()) + list(self._functions.keys())

    def get_all_tools(self) -> list[Tool]:
        """获取所有Tool对象"""
        return list(self._tools.values())

    def clear(self):
        """清空所有工具"""
        for name in self.list_tools():
            self.circuit_breaker.close(name)
        self._tools.clear()
        self._functions.clear()
        self.read_metadata_cache.clear()
        print("🧹 所有工具已清空。")

    # ==================== 乐观锁机制支持 ====================

    def cache_read_metadata(self, file_path: str, metadata: Dict[str, Any]):
        """缓存 Read 工具获取的文件元数据

        Args:
            file_path: 文件路径（相对于 project_root）
            metadata: 文件元数据字典，包含：
                - file_mtime_ms: 文件修改时间（毫秒时间戳）
                - file_size_bytes: 文件大小（字节）
        """
        self.read_metadata_cache[file_path] = metadata

    def get_read_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取缓存的文件元数据

        Args:
            file_path: 文件路径

        Returns:
            文件元数据字典，如果不存在则返回 None
        """
        return self.read_metadata_cache.get(file_path)

    def clear_read_cache(self, file_path: Optional[str] = None):
        """清空文件元数据缓存

        Args:
            file_path: 指定文件路径，如果为 None 则清空所有缓存
        """
        if file_path:
            self.read_metadata_cache.pop(file_path, None)
        else:
            self.read_metadata_cache.clear()


# 全局工具注册表
global_registry = ToolRegistry()
