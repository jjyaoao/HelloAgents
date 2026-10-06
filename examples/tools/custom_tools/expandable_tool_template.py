"""共享 SQLite 存储的五个 action。运行 python -m examples.tools.custom_tools.expandable_tool_template。

storage_path 是实际存储目录。默认演示使用临时目录，重建实例验证持久化。
这是单机资料 CRUD 示例，没有用户权限或跨资源事务接口。
"""

from contextlib import closing, contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from hello_agents.tools import Tool, ToolResponse, ToolRegistry, tool_action


class ExpandableToolTemplate(Tool):
    def __init__(self, storage_path):
        super().__init__(
            "expandable", "本地资料创建、查询、修改、删除", expandable=True
        )
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.database = self.storage_path / "resources.sqlite"
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS resources (
                name TEXT PRIMARY KEY, content TEXT NOT NULL, tags TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
            )

    @contextmanager
    def _connect(self):
        with closing(sqlite3.connect(self.database)) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                yield connection

    @staticmethod
    def _valid_name(name):
        return isinstance(name, str) and bool(name.strip())

    @staticmethod
    def _valid_tags(tags):
        return isinstance(tags, list) and all(
            isinstance(tag, str) and bool(tag.strip()) for tag in tags
        )

    @staticmethod
    def _resource(row):
        item = dict(row)
        item["tags"] = json.loads(item["tags"])
        return item

    @tool_action("expandable_create", "创建资料；tags 是标签字符串数组")
    def create(self, name: str, content: str, tags: list[str] | None = None):
        tags = [] if tags is None else tags
        if (
            not self._valid_name(name)
            or not isinstance(content, str)
            or not self._valid_tags(tags)
        ):
            return ToolResponse.error(
                "INVALID_PARAM", "名称不能为空，content 为字符串，tags 为非空字符串数组"
            )
        stamp = datetime.now(timezone.utc).isoformat()
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO resources VALUES (?, ?, ?, ?, ?)",
                    (name, content, json.dumps(tags, ensure_ascii=False), stamp, stamp),
                )
        except sqlite3.IntegrityError:
            return ToolResponse.error("CONFLICT", "同名资料已存在")
        return self.read(name)

    @tool_action("expandable_read", "按名称读取资料")
    def read(self, name: str, include_metadata: bool = True):
        if not self._valid_name(name) or type(include_metadata) is not bool:
            return ToolResponse.error(
                "INVALID_PARAM", "名称不能为空，include_metadata 必须是布尔值"
            )
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM resources WHERE name = ?", (name,)
            ).fetchone()
        if row is None:
            return ToolResponse.error("NOT_FOUND", "资料不存在")
        resource = (
            self._resource(row) if include_metadata else {"content": row["content"]}
        )
        return ToolResponse.success("已读取资料", data={"resource": resource})

    @tool_action("expandable_update", "修改资料内容或标签；空 tags 数组清空标签")
    def update(
        self, name: str, content: str | None = None, tags: list[str] | None = None
    ):
        if (
            not self._valid_name(name)
            or (content is None and tags is None)
            or (content is not None and not isinstance(content, str))
            or (tags is not None and not self._valid_tags(tags))
        ):
            return ToolResponse.error(
                "INVALID_PARAM", "需提供有效名称以及 content 或 tags"
            )
        fields, values = ["updated_at = ?"], [datetime.now(timezone.utc).isoformat()]
        if content is not None:
            fields.append("content = ?")
            values.append(content)
        if tags is not None:
            fields.append("tags = ?")
            values.append(json.dumps(tags, ensure_ascii=False))
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE resources SET " + ", ".join(fields) + " WHERE name = ?",
                values + [name],
            )
            if cursor.rowcount == 0:
                return ToolResponse.error("NOT_FOUND", "资料不存在")
        return self.read(name)

    @tool_action("expandable_delete", "删除资料；confirm 必须为 true，宿主仍需负责授权")
    def delete(self, name: str, confirm: bool = False):
        if not self._valid_name(name) or confirm is not True:
            return ToolResponse.error("INVALID_PARAM", "提供名称并设置 confirm=true")
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM resources WHERE name = ?", (name,))
            if cursor.rowcount == 0:
                return ToolResponse.error("NOT_FOUND", "资料不存在")
        return ToolResponse.success("资料已删除", data={"name": name})

    @tool_action("expandable_list", "按名称列出资料，可按精确标签筛选")
    def list_resources(self, filter_tag: str = ""):
        if not isinstance(filter_tag, str):
            return ToolResponse.error("INVALID_PARAM", "filter_tag 必须是字符串")
        with self._connect() as connection:
            resources = [
                self._resource(row)
                for row in connection.execute("SELECT * FROM resources ORDER BY name")
            ]
        if filter_tag:
            resources = [item for item in resources if filter_tag in item["tags"]]
        return ToolResponse.success(
            "资料列表", data={"resources": resources, "count": len(resources)}
        )

    def get_parameters(self):
        return []

    def run(self, parameters):
        return ToolResponse.error("INVALID_PARAM", "请注册并调用展开后的 action")


def main():
    with TemporaryDirectory() as directory:
        registry = ToolRegistry()
        registry.register_tool(ExpandableToolTemplate(directory))
        created = registry.execute_tool(
            "expandable_create",
            {"name": "预约", "content": "先核对开放时间", "tags": ["旅行"]},
        )
        print(created.to_json())
        restored = ExpandableToolTemplate(directory)
        assert restored.read("预约").data == created.data
        assert restored.list_resources("旅行").data["count"] == 1
        print(restored.update("预约", tags=[]).to_json())
        print(restored.delete("预约", confirm=True).to_json())


if __name__ == "__main__":
    main()
