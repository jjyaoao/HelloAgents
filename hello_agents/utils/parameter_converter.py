"""参数类型转换工具

提供统一的参数类型转换功能，用于Agent和工具之间的参数处理。
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def convert_parameter_types(
    tool_name: str,
    param_dict: Dict[str, Any],
    tool_registry: Optional['ToolRegistry'] = None
) -> Dict[str, Any]:
    """
    根据工具的参数定义转换参数类型

    Args:
        tool_name: 工具名称
        param_dict: 参数字典
        tool_registry: 工具注册表（可选）

    Returns:
        类型转换后的参数字典

    Example:
        >>> registry = ToolRegistry()
        >>> params = {"a": "12", "b": "3.5", "enabled": "true"}
        >>> converted = convert_parameter_types("calculator", params, registry)
        >>> print(converted)
        {"a": 12, "b": 3.5, "enabled": True}
    """
    if not tool_registry:
        logger.debug("未提供工具注册表，跳过参数类型转换")
        return param_dict

    # 获取工具对象
    tool = tool_registry.get_tool(tool_name)
    if not tool:
        logger.warning(f"未找到工具 '{tool_name}'，跳过参数类型转换")
        return param_dict

    # 获取工具的参数定义
    try:
        tool_params = tool.get_parameters()
    except AttributeError as e:
        logger.debug(f"工具 {tool_name} 不支持参数定义: {e}")
        return param_dict
    except Exception as e:
        logger.warning(f"获取工具参数定义失败: {e}")
        return param_dict

    # 创建参数类型映射
    param_types = {}
    for param in tool_params:
        param_types[param.name] = param.type

    # 转换参数类型
    converted_dict = {}
    for key, value in param_dict.items():
        param_type = param_types.get(key)

        if not param_type:
            # 未找到参数定义，保持原值
            converted_dict[key] = value
            continue

        try:
            normalized_type = param_type.lower()

            if normalized_type in {"number", "float"}:
                # 转换为浮点数
                if isinstance(value, str):
                    converted_dict[key] = float(value)
                else:
                    converted_dict[key] = float(value) if value is not None else value

            elif normalized_type in {"integer", "int"}:
                # 转换为整数
                if isinstance(value, str):
                    converted_dict[key] = int(value)
                else:
                    converted_dict[key] = int(value) if value is not None else value

            elif normalized_type in {"boolean", "bool"}:
                # 转换为布尔值
                if isinstance(value, bool):
                    converted_dict[key] = value
                elif isinstance(value, (int, float)):
                    converted_dict[key] = bool(value)
                elif isinstance(value, str):
                    converted_dict[key] = value.lower() in {"true", "1", "yes"}
                else:
                    converted_dict[key] = bool(value)

            else:
                # 其他类型保持原值
                converted_dict[key] = value

        except (TypeError, ValueError) as e:
            # 转换失败，保持原值
            logger.debug(f"参数 {key} 类型转换失败: {e}，保持原值")
            converted_dict[key] = value
        except Exception as e:
            # 其他异常，保持原值
            logger.warning(f"参数 {key} 转换时发生异常: {e}，保持原值")
            converted_dict[key] = value

    return converted_dict
