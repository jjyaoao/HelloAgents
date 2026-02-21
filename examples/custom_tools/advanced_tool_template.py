"""高级工具模板 - 完整特性

这是一个功能完整的自定义工具模板，展示了所有高级特性。

特性:
    - 完整的参数验证
    - 异步执行支持
    - 资源管理（上下文管理器）
    - 详细的日志记录
    - 统计信息收集
    - 错误处理和重试
    - 配置管理

使用方法:
    1. 复制此文件并重命名
    2. 根据需求修改和扩展功能
    3. 实现具体的业务逻辑
"""

from typing import Dict, Any, List, Optional
import logging
import time
import asyncio
from hello_agents.tools import Tool, ToolParameter, ToolResponse
from hello_agents.tools.errors import ToolErrorCode

# 配置日志
logger = logging.getLogger(__name__)


class AdvancedToolTemplate(Tool):
    """高级工具模板
    
    这是一个功能完整的工具模板，展示了所有高级特性。
    
    特性:
        - 支持同步和异步执行
        - 完整的参数验证
        - 资源管理（上下文管理器）
        - 详细的日志和统计
        - 错误处理和重试机制
    
    使用示例:
        >>> tool = AdvancedToolTemplate(api_key="your_key")
        >>> response = tool.run({"query": "test", "timeout": 30})
        >>> print(response.text)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 30,
        enable_cache: bool = True
    ):
        """初始化高级工具
        
        Args:
            api_key: API 密钥（可选）
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
            enable_cache: 是否启用缓存
        """
        super().__init__(
            name="advanced_tool",
            description="高级工具模板，展示完整的工具特性"
        )
        
        # 配置参数
        self.api_key = api_key
        self.max_retries = max_retries
        self.timeout = timeout
        self.enable_cache = enable_cache
        
        # 内部状态
        self._cache = {} if enable_cache else None
        self._stats = {
            "total_calls": 0,
            "success_calls": 0,
            "error_calls": 0,
            "cache_hits": 0
        }
        
        logger.info(f"初始化工具 {self.name}，配置: max_retries={max_retries}, timeout={timeout}")
    
    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行工具（同步版本）
        
        Args:
            parameters: 工具参数
        
        Returns:
            ToolResponse: 工具响应
        """
        self._stats["total_calls"] += 1
        start_time = time.time()
        
        logger.info(f"执行工具 {self.name}，参数: {parameters}")
        
        # 1. 参数验证
        validation_error = self._validate_parameters(parameters)
        if validation_error:
            self._stats["error_calls"] += 1
            return validation_error
        
        # 2. 检查缓存
        if self.enable_cache:
            cache_key = self._get_cache_key(parameters)
            if cache_key in self._cache:
                self._stats["cache_hits"] += 1
                logger.info(f"缓存命中: {cache_key}")
                return self._cache[cache_key]
        
        # 3. 执行业务逻辑（带重试）
        for attempt in range(self.max_retries):
            try:
                result = self._execute_logic(parameters)
                
                # 4. 构建成功响应
                elapsed_time = time.time() - start_time
                response = ToolResponse.success(
                    text=f"执行成功: {result}",
                    data={
                        "result": result,
                        "parameters": parameters,
                        "attempt": attempt + 1
                    },
                    stats={
                        "time_ms": int(elapsed_time * 1000),
                        "retries": attempt,
                        "cache_hit": False
                    }
                )
                
                # 5. 缓存结果
                if self.enable_cache:
                    self._cache[cache_key] = response
                
                self._stats["success_calls"] += 1
                logger.info(f"工具执行成功，耗时: {elapsed_time:.2f}s")
                return response
            
            except TimeoutError as e:
                logger.warning(f"执行超时 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    self._stats["error_calls"] += 1
                    return ToolResponse.error(
                        code=ToolErrorCode.TIMEOUT,
                        message=f"执行超时，已重试 {self.max_retries} 次",
                        context={"parameters": parameters}
                    )
            
            except Exception as e:
                logger.error(f"执行失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    self._stats["error_calls"] += 1
                    return ToolResponse.error(
                        code=ToolErrorCode.EXECUTION_ERROR,
                        message=f"执行失败: {str(e)}",
                        context={"parameters": parameters, "retries": attempt + 1}
                    )
            
            # 重试前等待
            time.sleep(0.5 * (attempt + 1))
        
        # 不应该到达这里
        return ToolResponse.error(
            code=ToolErrorCode.INTERNAL_ERROR,
            message="未知错误"
        )
    
    async def arun(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行工具（异步版本）
        
        Args:
            parameters: 工具参数
        
        Returns:
            ToolResponse: 工具响应
        """
        logger.info(f"异步执行工具 {self.name}")
        
        # 参数验证
        validation_error = self._validate_parameters(parameters)
        if validation_error:
            return validation_error
        
        # 异步执行业务逻辑
        try:
            result = await self._execute_logic_async(parameters)
            return ToolResponse.success(
                text=f"异步执行成功: {result}",
                data={"result": result}
            )
        except Exception as e:
            logger.error(f"异步执行失败: {e}")
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=str(e)
            )

    def get_parameters(self) -> List[ToolParameter]:
        """定义工具参数"""
        return [
            ToolParameter(
                name="query",
                type="string",
                description="查询字符串",
                required=True
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="超时时间（秒）",
                required=False,
                default=30
            ),
            ToolParameter(
                name="format",
                type="string",
                description="输出格式 (json/text)",
                required=False,
                default="json"
            )
        ]

    def _validate_parameters(self, parameters: Dict[str, Any]) -> Optional[ToolResponse]:
        """验证参数

        Returns:
            如果验证失败，返回错误响应；否则返回 None
        """
        # 检查必需参数
        if "query" not in parameters or not parameters["query"]:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="参数 'query' 不能为空"
            )

        # 检查参数类型
        if "timeout" in parameters:
            try:
                timeout = int(parameters["timeout"])
                if timeout <= 0:
                    return ToolResponse.error(
                        code=ToolErrorCode.INVALID_PARAM,
                        message="参数 'timeout' 必须大于 0"
                    )
            except (ValueError, TypeError):
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message="参数 'timeout' 必须是整数"
                )

        # 检查枚举值
        if "format" in parameters:
            if parameters["format"] not in ["json", "text"]:
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message="参数 'format' 必须是 'json' 或 'text'"
                )

        return None

    def _get_cache_key(self, parameters: Dict[str, Any]) -> str:
        """生成缓存键"""
        import hashlib
        import json

        # 将参数序列化为字符串
        param_str = json.dumps(parameters, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()

    def _execute_logic(self, parameters: Dict[str, Any]) -> str:
        """执行业务逻辑（同步版本）

        在这里实现你的工具逻辑
        """
        query = parameters["query"]
        timeout = parameters.get("timeout", self.timeout)

        # 模拟耗时操作
        time.sleep(0.1)

        # 实现你的业务逻辑
        result = f"处理查询 '{query}' 的结果"

        return result

    async def _execute_logic_async(self, parameters: Dict[str, Any]) -> str:
        """执行业务逻辑（异步版本）"""
        query = parameters["query"]

        # 模拟异步操作
        await asyncio.sleep(0.1)

        # 实现你的异步业务逻辑
        result = f"异步处理查询 '{query}' 的结果"

        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取工具统计信息"""
        return self._stats.copy()

    def clear_cache(self):
        """清空缓存"""
        if self._cache:
            self._cache.clear()
            logger.info("缓存已清空")

    # 上下文管理器支持
    def __enter__(self):
        """进入上下文"""
        logger.info(f"进入工具上下文: {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        logger.info(f"退出工具上下文: {self.name}")
        # 清理资源
        if self._cache:
            self.clear_cache()


# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":
    import logging
    from hello_agents import ToolRegistry

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 1. 基本使用
    print("=== 基本使用 ===")
    tool = AdvancedToolTemplate(api_key="test_key", enable_cache=True)

    response = tool.run({"query": "test query", "timeout": 10})
    print(f"状态: {response.status}")
    print(f"文本: {response.text}")
    print(f"统计: {response.stats}")
    print()

    # 2. 缓存测试
    print("=== 缓存测试 ===")
    response2 = tool.run({"query": "test query", "timeout": 10})
    print(f"缓存命中: {response2.stats.get('cache_hit', False)}")
    print(f"工具统计: {tool.get_stats()}")
    print()

    # 3. 上下文管理器
    print("=== 上下文管理器 ===")
    with AdvancedToolTemplate(api_key="test_key") as tool:
        response = tool.run({"query": "context test"})
        print(f"结果: {response.text}")
    print()

    # 4. 异步执行
    print("=== 异步执行 ===")
    async def test_async():
        tool = AdvancedToolTemplate()
        response = await tool.arun({"query": "async test"})
        print(f"异步结果: {response.text}")

    asyncio.run(test_async())

