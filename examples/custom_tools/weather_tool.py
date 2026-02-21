"""天气查询工具 - API 调用示例

这是一个真实的天气查询工具示例，展示如何：
- 调用外部 API
- 处理 API 响应和错误
- 实现参数验证
- 添加缓存机制
"""

from typing import Dict, Any, List, Optional
import logging
from hello_agents.tools import Tool, ToolParameter, ToolResponse
from hello_agents.tools.errors import ToolErrorCode

logger = logging.getLogger(__name__)


class WeatherTool(Tool):
    """天气查询工具
    
    功能:
        - 查询指定城市的实时天气
        - 支持多种温度单位（摄氏度/华氏度）
        - 自动缓存查询结果
    
    使用示例:
        >>> tool = WeatherTool(api_key="your_api_key")
        >>> response = tool.run({"city": "北京", "unit": "celsius"})
        >>> print(response.text)
    """
    
    def __init__(self, api_key: Optional[str] = None, cache_ttl: int = 300):
        """初始化天气工具
        
        Args:
            api_key: 天气 API 密钥（可选，示例中使用模拟数据）
            cache_ttl: 缓存过期时间（秒）
        """
        super().__init__(
            name="weather",
            description="查询指定城市的实时天气信息，支持多种温度单位"
        )
        
        self.api_key = api_key
        self.cache_ttl = cache_ttl
        self._cache = {}
        
        logger.info(f"初始化天气工具，缓存 TTL: {cache_ttl}s")
    
    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行天气查询
        
        Args:
            parameters: 包含 city 和 unit 参数
        
        Returns:
            ToolResponse: 天气查询结果
        """
        # 1. 参数验证
        city = parameters.get("city", "").strip()
        if not city:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="参数 'city' 不能为空",
                context={"provided_params": parameters}
            )
        
        unit = parameters.get("unit", "celsius").lower()
        if unit not in ["celsius", "fahrenheit"]:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="参数 'unit' 必须是 'celsius' 或 'fahrenheit'",
                context={"provided_unit": unit}
            )
        
        logger.info(f"查询天气: {city}, 单位: {unit}")
        
        # 2. 检查缓存
        cache_key = f"{city}_{unit}"
        if cache_key in self._cache:
            logger.info(f"缓存命中: {cache_key}")
            cached_data = self._cache[cache_key]
            return ToolResponse.success(
                text=self._format_weather_text(cached_data, city),
                data=cached_data,
                stats={"cache_hit": True}
            )
        
        # 3. 调用天气 API
        try:
            weather_data = self._fetch_weather(city, unit)
            
            if weather_data is None:
                return ToolResponse.error(
                    code=ToolErrorCode.NOT_FOUND,
                    message=f"未找到城市 '{city}' 的天气信息",
                    context={"city": city}
                )
            
            # 4. 缓存结果
            self._cache[cache_key] = weather_data
            
            # 5. 返回成功响应
            return ToolResponse.success(
                text=self._format_weather_text(weather_data, city),
                data=weather_data,
                stats={
                    "cache_hit": False,
                    "api_calls": 1
                }
            )
        
        except Exception as e:
            logger.error(f"天气查询失败: {e}")
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"天气查询失败: {str(e)}",
                context={"city": city, "unit": unit}
            )
    
    def get_parameters(self) -> List[ToolParameter]:
        """定义工具参数"""
        return [
            ToolParameter(
                name="city",
                type="string",
                description="要查询的城市名称（中文或英文）",
                required=True
            ),
            ToolParameter(
                name="unit",
                type="string",
                description="温度单位：celsius（摄氏度）或 fahrenheit（华氏度）",
                required=False,
                default="celsius"
            )
        ]
    
    def _fetch_weather(self, city: str, unit: str) -> Optional[Dict[str, Any]]:
        """调用天气 API
        
        实际使用时，这里应该调用真实的天气 API（如 OpenWeatherMap）
        示例中使用模拟数据
        """
        # 模拟 API 调用
        # 实际实现示例:
        # import requests
        # url = f"https://api.openweathermap.org/data/2.5/weather"
        # params = {"q": city, "appid": self.api_key, "units": "metric" if unit == "celsius" else "imperial"}
        # response = requests.get(url, params=params, timeout=10)
        # if response.status_code == 200:
        #     return response.json()
        # return None
        
        # 模拟数据
        mock_data = {
            "北京": {"temp": 15, "description": "晴天", "humidity": 45, "wind_speed": 12},
            "上海": {"temp": 20, "description": "多云", "humidity": 60, "wind_speed": 8},
            "深圳": {"temp": 25, "description": "小雨", "humidity": 75, "wind_speed": 15},
            "beijing": {"temp": 15, "description": "Sunny", "humidity": 45, "wind_speed": 12},
        }
        
        weather = mock_data.get(city)
        if weather is None:
            return None
        
        # 转换温度单位
        if unit == "fahrenheit":
            weather = weather.copy()
            weather["temp"] = weather["temp"] * 9/5 + 32
        
        return {
            "city": city,
            "temperature": weather["temp"],
            "unit": unit,
            "description": weather["description"],
            "humidity": weather["humidity"],
            "wind_speed": weather["wind_speed"]
        }
    
    def _format_weather_text(self, weather_data: Dict[str, Any], city: str) -> str:
        """格式化天气信息为文本"""
        unit_symbol = "°C" if weather_data["unit"] == "celsius" else "°F"
        
        return (
            f"{city} 的天气:\n"
            f"- 温度: {weather_data['temperature']:.1f}{unit_symbol}\n"
            f"- 天气: {weather_data['description']}\n"
            f"- 湿度: {weather_data['humidity']}%\n"
            f"- 风速: {weather_data['wind_speed']} km/h"
        )


# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":
    from hello_agents import ToolRegistry, ReActAgent, HelloAgentsLLM
    
    # 1. 创建工具
    print("=== 创建天气工具 ===")
    tool = WeatherTool(api_key="demo_key")
    
    # 2. 直接测试
    print("\n=== 直接测试 ===")
    response = tool.run({"city": "北京", "unit": "celsius"})
    print(f"状态: {response.status}")
    print(f"结果:\n{response.text}")
    print(f"数据: {response.data}")
    print()
    
    # 3. 测试缓存
    print("=== 测试缓存 ===")
    response2 = tool.run({"city": "北京", "unit": "celsius"})
    print(f"缓存命中: {response2.stats.get('cache_hit', False)}")
    print()
    
    # 4. 测试不同单位
    print("=== 测试华氏度 ===")
    response3 = tool.run({"city": "北京", "unit": "fahrenheit"})
    print(f"结果:\n{response3.text}")
    print()
    
    # 5. 测试错误处理
    print("=== 测试错误处理 ===")
    response4 = tool.run({"city": "不存在的城市"})
    print(f"状态: {response4.status}")
    print(f"错误: {response4.error_info}")
    print()
    
    # 6. 在 Agent 中使用
    print("=== 在 Agent 中使用 ===")
    registry = ToolRegistry()
    registry.register_tool(tool)
    
    llm = HelloAgentsLLM()
    agent = ReActAgent("assistant", llm, tool_registry=registry)
    
    result = agent.run("查询上海的天气")
    print(result)

