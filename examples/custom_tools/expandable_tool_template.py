"""可展开工具模板 - 多功能工具

这是一个可展开工具模板，展示如何使用 @tool_action 装饰器将一个工具展开为多个子工具。

特性:
    - 使用 @tool_action 装饰器标记子功能
    - 自动从方法签名和 docstring 提取参数
    - 每个子功能作为独立工具注册
    - 共享父工具的状态和资源

使用方法:
    1. 复制此文件并重命名
    2. 使用 @tool_action 装饰器标记每个子功能
    3. 实现各个子功能的逻辑
    4. 注册时框架会自动展开为多个工具
"""

from typing import Dict, Any, List
import logging
from hello_agents.tools import Tool, tool_action, ToolParameter, ToolResponse
from hello_agents.tools.errors import ToolErrorCode

logger = logging.getLogger(__name__)


class ExpandableToolTemplate(Tool):
    """可展开工具模板
    
    这是一个多功能工具，可以展开为多个独立的子工具。
    
    子工具:
        - expandable_create: 创建资源
        - expandable_read: 读取资源
        - expandable_update: 更新资源
        - expandable_delete: 删除资源
    
    使用示例:
        >>> tool = ExpandableToolTemplate()
        >>> registry.register_tool(tool)
        >>> # 框架会自动注册 4 个子工具
    """
    
    def __init__(self, storage_path: str = "./data"):
        """初始化可展开工具
        
        Args:
            storage_path: 数据存储路径
        """
        super().__init__(
            name="expandable",
            description="可展开的多功能工具模板",
            expandable=True  # 标记为可展开
        )
        
        self.storage_path = storage_path
        self._data_store = {}  # 模拟数据存储
        
        logger.info(f"初始化可展开工具，存储路径: {storage_path}")
    
    # ============================================
    # 子工具定义（使用 @tool_action 装饰器）
    # ============================================
    
    @tool_action("expandable_create", "创建新资源")
    def create(self, name: str, content: str, tags: str = "") -> ToolResponse:
        """创建新资源
        
        Args:
            name: 资源名称
            content: 资源内容
            tags: 标签（可选，逗号分隔）
        """
        logger.info(f"创建资源: {name}")
        
        # 检查资源是否已存在
        if name in self._data_store:
            return ToolResponse.error(
                code=ToolErrorCode.CONFLICT,
                message=f"资源 '{name}' 已存在",
                context={"name": name}
            )
        
        # 创建资源
        resource = {
            "name": name,
            "content": content,
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "created_at": "2025-02-21T00:00:00Z"
        }
        
        self._data_store[name] = resource
        
        return ToolResponse.success(
            text=f"资源 '{name}' 创建成功",
            data={"resource": resource}
        )
    
    @tool_action("expandable_read", "读取资源")
    def read(self, name: str, include_metadata: bool = True) -> ToolResponse:
        """读取资源内容
        
        Args:
            name: 资源名称
            include_metadata: 是否包含元数据
        """
        logger.info(f"读取资源: {name}")
        
        # 检查资源是否存在
        if name not in self._data_store:
            return ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message=f"资源 '{name}' 不存在",
                context={"name": name}
            )
        
        resource = self._data_store[name]
        
        # 构建响应
        if include_metadata:
            text = f"资源 '{name}':\n内容: {resource['content']}\n标签: {', '.join(resource['tags'])}"
            data = resource
        else:
            text = f"资源 '{name}': {resource['content']}"
            data = {"content": resource['content']}
        
        return ToolResponse.success(text=text, data=data)
    
    @tool_action("expandable_update", "更新资源")
    def update(self, name: str, content: str = None, tags: str = None) -> ToolResponse:
        """更新资源
        
        Args:
            name: 资源名称
            content: 新内容（可选）
            tags: 新标签（可选，逗号分隔）
        """
        logger.info(f"更新资源: {name}")
        
        # 检查资源是否存在
        if name not in self._data_store:
            return ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message=f"资源 '{name}' 不存在",
                context={"name": name}
            )
        
        resource = self._data_store[name]
        updated_fields = []
        
        # 更新内容
        if content is not None:
            resource["content"] = content
            updated_fields.append("content")
        
        # 更新标签
        if tags is not None:
            resource["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
            updated_fields.append("tags")
        
        if not updated_fields:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="至少需要提供 content 或 tags 参数"
            )
        
        resource["updated_at"] = "2025-02-21T00:00:00Z"
        
        return ToolResponse.success(
            text=f"资源 '{name}' 更新成功，更新字段: {', '.join(updated_fields)}",
            data={"resource": resource, "updated_fields": updated_fields}
        )
    
    @tool_action("expandable_delete", "删除资源")
    def delete(self, name: str, confirm: bool = False) -> ToolResponse:
        """删除资源
        
        Args:
            name: 资源名称
            confirm: 确认删除（必须为 true）
        """
        logger.info(f"删除资源: {name}")
        
        # 检查确认标志
        if not confirm:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="删除操作需要确认，请设置 confirm=true"
            )

        # 检查资源是否存在
        if name not in self._data_store:
            return ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message=f"资源 '{name}' 不存在",
                context={"name": name}
            )

        # 删除资源
        deleted_resource = self._data_store.pop(name)

        return ToolResponse.success(
            text=f"资源 '{name}' 已删除",
            data={"deleted_resource": deleted_resource}
        )

    @tool_action("expandable_list", "列出所有资源")
    def list_resources(self, filter_tag: str = "") -> ToolResponse:
        """列出所有资源

        Args:
            filter_tag: 按标签过滤（可选）
        """
        logger.info(f"列出资源，过滤标签: {filter_tag}")

        resources = list(self._data_store.values())

        # 按标签过滤
        if filter_tag:
            resources = [r for r in resources if filter_tag in r.get("tags", [])]

        return ToolResponse.success(
            text=f"找到 {len(resources)} 个资源",
            data={
                "resources": resources,
                "count": len(resources),
                "filter_tag": filter_tag
            }
        )

    # ============================================
    # 普通模式的 run() 方法（可选）
    # ============================================

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """普通模式下的执行方法

        当工具不展开时，可以提供一个默认的执行逻辑。
        """
        return ToolResponse.error(
            code=ToolErrorCode.NOT_IMPLEMENTED,
            message="此工具需要展开使用，请使用子工具: expandable_create, expandable_read, expandable_update, expandable_delete, expandable_list"
        )

    def get_parameters(self) -> List[ToolParameter]:
        """普通模式下的参数定义（可选）"""
        return []


# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":
    from hello_agents import ToolRegistry

    # 1. 创建可展开工具
    print("=== 创建可展开工具 ===")
    tool = ExpandableToolTemplate(storage_path="./data")

    # 2. 查看展开后的子工具
    print("\n=== 展开后的子工具 ===")
    expanded_tools = tool.get_expanded_tools()
    if expanded_tools:
        for sub_tool in expanded_tools:
            print(f"- {sub_tool.name}: {sub_tool.description}")
    print()

    # 3. 注册到 ToolRegistry（自动展开）
    print("=== 注册到 ToolRegistry ===")
    registry = ToolRegistry()
    registry.register_tool(tool)

    # 查看注册的工具
    print("已注册的工具:")
    for tool_name in registry.list_tools():
        print(f"- {tool_name}")
    print()

    # 4. 测试子工具
    print("=== 测试子工具 ===")

    # 创建资源
    response = registry.execute_tool("expandable_create", {
        "name": "doc1",
        "content": "这是第一个文档",
        "tags": "重要, 文档"
    })
    print(f"创建: {response.text}")

    # 读取资源
    response = registry.execute_tool("expandable_read", {
        "name": "doc1",
        "include_metadata": True
    })
    print(f"读取: {response.text}")

    # 更新资源
    response = registry.execute_tool("expandable_update", {
        "name": "doc1",
        "content": "更新后的内容"
    })
    print(f"更新: {response.text}")

    # 列出资源
    response = registry.execute_tool("expandable_list", {})
    print(f"列出: {response.text}")

    # 删除资源
    response = registry.execute_tool("expandable_delete", {
        "name": "doc1",
        "confirm": True
    })
    print(f"删除: {response.text}")

