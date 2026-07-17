"""工具注册表 - HelloAgents原生工具系统"""

from typing import Optional, Any, Callable, Dict
import time
from .base import Tool
from .response import ToolResponse, ToolStatus
from .errors import ToolErrorCode
from .circuit_breaker import CircuitBreaker
from .interceptor import ToolInterceptor, AlwaysAllowInterceptor

class ToolRegistry:
    """
    HelloAgents工具注册表

    提供工具的注册、管理和执行功能。
    支持两种工具注册方式：
    1. Tool对象注册（推荐）
    2. 函数直接注册（简便）

    支持工具调用拦截器（Human-in-the-loop）：
    - 在工具执行前插入确认环节
    - 通过 set_interceptor() 设置拦截策略
    """

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None,
                 interceptor: Optional[ToolInterceptor] = None):
        self._tools: dict[str, Tool] = {}
        self._functions: dict[str, dict[str, Any]] = {}

        # 文件元数据缓存（用于乐观锁机制）
        self.read_metadata_cache: Dict[str, Dict[str, Any]] = {}

        # 熔断器（默认启用）
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

        # 工具调用拦截器（默认始终放行，向后兼容）
        self.interceptor: ToolInterceptor = interceptor or AlwaysAllowInterceptor()

    def set_interceptor(self, interceptor: ToolInterceptor):
        """设置工具调用拦截器

        Args:
            interceptor: ToolInterceptor 实例

        Example:
            >>> registry.set_interceptor(ConsoleConfirmInterceptor(whitelist={"ReadTool"}))
        """
        self.interceptor = interceptor

    def register_tool(self, tool: Tool, auto_expand: bool = True):
        """
        注册Tool对象

        Args:
            tool: Tool实例
            auto_expand: 是否自动展开可展开的工具（默认True）
        """
        # 检查工具是否可展开
        if auto_expand and hasattr(tool, 'expandable') and tool.expandable:
            expanded_tools = tool.get_expanded_tools()
            if expanded_tools:
                # 注册所有展开的子工具
                for sub_tool in expanded_tools:
                    if sub_tool.name in self._tools:
                        print(f"⚠️ 警告：工具 '{sub_tool.name}' 已存在，将被覆盖。")
                    self._tools[sub_tool.name] = sub_tool
                print(f"✅ 工具 '{tool.name}' 已展开为 {len(expanded_tools)} 个独立工具")
                return

        # 普通工具或不展开的工具
        if tool.name in self._tools:
            print(f"⚠️ 警告：工具 '{tool.name}' 已存在，将被覆盖。")

        self._tools[tool.name] = tool
        print(f"✅ 工具 '{tool.name}' 已注册。")

    def register_function(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None
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

        # 自动提取名称
        if name is None:
            name = func.__name__

        # 自动提取描述
        if description is None:
            import inspect
            doc = inspect.getdoc(func)
            if doc:
                # 提取第一行作为描述
                description = doc.split('\n')[0].strip()
            else:
                description = f"执行 {name}"

        if name in self._functions:
            print(f"⚠️ 警告：工具 '{name}' 已存在，将被覆盖。")

        self._functions[name] = {
            "description": description,
            "func": func
        }
        print(f"✅ 函数工具 '{name}' 已注册。")

    def unregister(self, name: str):
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            print(f"🗑️ 工具 '{name}' 已注销。")
        elif name in self._functions:
            del self._functions[name]
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

    def execute_tool(self, name: str, input_text: str) -> ToolResponse:
        """
        执行工具，返回 ToolResponse 对象（带熔断器保护）

        Args:
            name: 工具名称
            input_text: 输入参数

        Returns:
            ToolResponse: 标准化的工具响应对象
        """
        # 检查熔断器
        if self.circuit_breaker.is_open(name):
            status = self.circuit_breaker.get_status(name)
            return ToolResponse.error(
                code=ToolErrorCode.CIRCUIT_OPEN,
                message=f"工具 '{name}' 当前被禁用，由于连续失败。{status['recover_in_seconds']} 秒后可用。",
                context={
                    "tool_name": name,
                    "circuit_status": status
                }
            )

        # 检查拦截器（Human-in-the-loop）
        import json as _json
        params_for_intercept = input_text
        if isinstance(input_text, str):
            try:
                params_for_intercept = _json.loads(input_text)
            except _json.JSONDecodeError:
                params_for_intercept = {"input": input_text}
        elif isinstance(input_text, dict):
            params_for_intercept = input_text
        else:
            params_for_intercept = {"input": str(input_text)}

        interceptor_result = self.interceptor.intercept(
            tool_name=name,
            parameters=params_for_intercept,
            context={"tool_registry": type(self).__name__}
        )
        if interceptor_result.is_denied:
            return ToolResponse.error(
                code=ToolErrorCode.PERMISSION_DENIED,
                message=f"工具 '{name}' 被拦截器拒绝: {interceptor_result.reason}",
                context={"tool_name": name, "interceptor_reason": interceptor_result.reason}
            )

        # 执行工具
        return self._execute_tool_internal(name, input_text)

    async def aexecute_tool(self, name: str, input_text: str) -> ToolResponse:
        """
        异步执行工具，返回 ToolResponse 对象（带熔断器 + 拦截器保护）

        与 execute_tool() 功能相同，但使用异步拦截器。
        适用于 async Agent（如 ReActAgent.arun()）。

        Args:
            name: 工具名称
            input_text: 输入参数

        Returns:
            ToolResponse: 标准化的工具响应对象
        """
        # 检查熔断器
        if self.circuit_breaker.is_open(name):
            status = self.circuit_breaker.get_status(name)
            return ToolResponse.error(
                code=ToolErrorCode.CIRCUIT_OPEN,
                message=f"工具 '{name}' 当前被禁用，由于连续失败。{status['recover_in_seconds']} 秒后可用。",
                context={
                    "tool_name": name,
                    "circuit_status": status
                }
            )

        # 检查拦截器（异步版本 - Human-in-the-loop）
        import json as _json
        params_for_intercept = input_text
        if isinstance(input_text, str):
            try:
                params_for_intercept = _json.loads(input_text)
            except _json.JSONDecodeError:
                params_for_intercept = {"input": input_text}
        elif isinstance(input_text, dict):
            params_for_intercept = input_text
        else:
            params_for_intercept = {"input": str(input_text)}

        interceptor_result = await self.interceptor.aintercept(
            tool_name=name,
            parameters=params_for_intercept,
            context={"tool_registry": type(self).__name__}
        )
        if interceptor_result.is_denied:
            return ToolResponse.error(
                code=ToolErrorCode.PERMISSION_DENIED,
                message=f"工具 '{name}' 被拦截器拒绝: {interceptor_result.reason}",
                context={"tool_name": name, "interceptor_reason": interceptor_result.reason}
            )

        # 执行工具（与同步版本相同逻辑）
        return self._execute_tool_internal(name, input_text)

    def _execute_tool_internal(self, name: str, input_text: str) -> ToolResponse:
        """内部工具执行逻辑（供 execute_tool 和 aexecute_tool 共用）

        在熔断器和拦截器检查通过后调用。
        """
        import json
        import time as time_module

        response = None

        # 优先查找Tool对象（新协议）
        if name in self._tools:
            tool = self._tools[name]
            try:
                # 解析参数（支持 JSON 字符串或字典）
                if isinstance(input_text, str):
                    try:
                        parameters = json.loads(input_text)
                    except json.JSONDecodeError:
                        # 如果不是 JSON，作为普通字符串处理
                        parameters = {"input": input_text}
                elif isinstance(input_text, dict):
                    parameters = input_text
                else:
                    parameters = {"input": str(input_text)}

                # 使用 run_with_timing 自动添加时间统计
                response = tool.run_with_timing(parameters)
            except Exception as e:
                response = ToolResponse.error(
                    code=ToolErrorCode.EXECUTION_ERROR,
                    message=f"执行工具 '{name}' 时发生异常: {str(e)}",
                    context={"tool_name": name, "input": input_text}
                )

        # 查找函数工具（自动包装为新协议）
        elif name in self._functions:
            func = self._functions[name]["func"]
            start_time = time_module.time()

            try:
                result = func(input_text)
                elapsed_ms = int((time_module.time() - start_time) * 1000)

                # 包装为 ToolResponse
                response = ToolResponse.success(
                    text=str(result),
                    data={"output": result},
                    stats={"time_ms": elapsed_ms},
                    context={"tool_name": name, "input": input_text}
                )
            except Exception as e:
                elapsed_ms = int((time_module.time() - start_time) * 1000)
                response = ToolResponse.error(
                    code=ToolErrorCode.EXECUTION_ERROR,
                    message=f"函数执行失败: {str(e)}",
                    stats={"time_ms": elapsed_ms},
                    context={"tool_name": name, "input": input_text}
                )

        # 工具不存在
        else:
            response = ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message=f"未找到名为 '{name}' 的工具",
                context={"tool_name": name}
            )

        # 记录熔断器结果
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
        self._tools.clear()
        self._functions.clear()
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
