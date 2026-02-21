"""文件操作工具 - 支持乐观锁机制

提供标准的文件读写编辑能力：
- ReadTool: 读取文件 + 元数据缓存
- WriteTool: 写入文件 + 冲突检测 + 原子写入
- EditTool: 精确替换 + 冲突检测 + 备份
- MultiEditTool: 批量替换 + 原子性保证

使用示例：
```python
from hello_agents import ToolRegistry
from hello_agents.tools.builtin import ReadTool, WriteTool, EditTool

registry = ToolRegistry()
registry.register_tool(ReadTool(project_root="./"))
registry.register_tool(WriteTool(project_root="./"))
registry.register_tool(EditTool(project_root="./"))
```
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from pathlib import Path
import os
import shutil
from datetime import datetime

from ..base import Tool, ToolParameter
from ..response import ToolResponse
from ..errors import ToolErrorCode

if TYPE_CHECKING:
    from ..registry import ToolRegistry


class ReadTool(Tool):
    """文件读取工具

    功能：
    - 读取文件内容（支持 offset/limit）
    - 列出目录内容（当 path 是目录时）
    - 自动获取文件元数据（mtime, size）
    - 缓存元数据到 ToolRegistry（用于乐观锁）
    - 跨平台兼容（Windows/Linux）

    参数：
    - path: 文件或目录路径（相对于 project_root）
    - offset: 起始行号（可选，默认 0，仅文件有效）
    - limit: 最大行数（可选，默认 2000，仅文件有效）
    """
    
    def __init__(
        self,
        project_root: str = ".",
        working_dir: Optional[str] = None,
        registry: Optional['ToolRegistry'] = None
    ):
        super().__init__(
            name="Read",
            description="读取文件内容或列出目录内容，支持行号范围和元数据缓存",
            expandable=False
        )
        self.project_root = Path(project_root).resolve()
        self.working_dir = Path(working_dir).resolve() if working_dir else self.project_root
        self.registry = registry
    
    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="要读取的文件路径或目录路径（相对项目根目录）。如果是目录，将列出目录内容",
                required=True
            ),
            ToolParameter(
                name="offset",
                type="integer",
                description="起始行号（从 0 开始，仅读取文件时有效）",
                required=False,
                default=0
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="最大行数（仅读取文件时有效）",
                required=False,
                default=2000
            )
        ]
    
    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行文件读取或目录列表"""
        path = parameters.get("path")
        offset = parameters.get("offset", 0)
        limit = parameters.get("limit", 2000)

        if not path:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="缺少必需参数: path"
            )

        try:
            # 解析路径
            full_path = self._resolve_path(path)

            if not full_path.exists():
                return ToolResponse.error(
                    code=ToolErrorCode.NOT_FOUND,
                    message=f"路径 '{path}' 不存在"
                )

            # 如果是目录，返回目录列表
            if full_path.is_dir():
                return self._list_directory(path, full_path)

            # 读取文件
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 应用 offset 和 limit
            total_lines = len(lines)
            if offset > 0:
                lines = lines[offset:]
            if limit > 0:
                lines = lines[:limit]

            content = ''.join(lines)

            # 获取文件元数据（用于乐观锁）
            mtime = os.path.getmtime(full_path)
            size = os.path.getsize(full_path)
            file_mtime_ms = int(mtime * 1000)
            file_size_bytes = size

            # 缓存元数据到 ToolRegistry
            if self.registry:
                self.registry.cache_read_metadata(path, {
                    "file_mtime_ms": file_mtime_ms,
                    "file_size_bytes": file_size_bytes
                })

            return ToolResponse.success(
                text=f"读取 {len(lines)} 行（共 {total_lines} 行，{file_size_bytes} 字节）",
                data={
                    "content": content,
                    "lines": len(lines),
                    "total_lines": total_lines,
                    "file_mtime_ms": file_mtime_ms,
                    "file_size_bytes": file_size_bytes,
                    "offset": offset,
                    "limit": limit
                }
            )
        
        except PermissionError:
            return ToolResponse.error(
                code=ToolErrorCode.PERMISSION_DENIED,
                message=f"无权限读取 '{path}'"
            )
        except Exception as e:
            return ToolResponse.error(
                code=ToolErrorCode.INTERNAL_ERROR,
                message=f"读取文件失败：{str(e)}"
            )

    def _list_directory(self, path: str, full_path: Path) -> ToolResponse:
        """列出目录内容（兼容 Windows 和 Linux）"""
        try:
            entries = []
            total_files = 0
            total_dirs = 0

            # 获取目录下所有条目
            for entry in sorted(full_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                try:
                    # 获取条目信息
                    is_dir = entry.is_dir()
                    name = entry.name

                    # 获取大小和修改时间
                    if is_dir:
                        size_str = "<DIR>"
                        total_dirs += 1
                    else:
                        try:
                            size = entry.stat().st_size
                            size_str = self._format_size(size)
                            total_files += 1
                        except:
                            size_str = "?"

                    # 获取修改时间
                    try:
                        mtime = entry.stat().st_mtime
                        mtime_str = self._format_time(mtime)
                    except:
                        mtime_str = "?"

                    # 使用正斜杠作为路径分隔符（跨平台兼容）
                    relative_path = str(entry.relative_to(self.project_root)).replace(os.sep, '/')

                    entries.append({
                        "name": name,
                        "type": "directory" if is_dir else "file",
                        "size": size_str,
                        "mtime": mtime_str,
                        "path": relative_path
                    })
                except Exception as e:
                    # 跳过无法访问的条目
                    continue

            # 构建输出文本
            if not entries:
                text = f"目录 '{path}' 为空"
            else:
                lines = [f"目录 '{path}' 包含 {total_files} 个文件，{total_dirs} 个目录：\n"]
                for entry in entries:
                    type_icon = "📁" if entry["type"] == "directory" else "📄"
                    lines.append(f"{type_icon} {entry['name']:<40} {entry['size']:>10} {entry['mtime']}")
                text = "\n".join(lines)

            return ToolResponse.success(
                text=text,
                data={
                    "path": path,
                    "entries": entries,
                    "total_files": total_files,
                    "total_dirs": total_dirs,
                    "is_directory": True
                }
            )
        except PermissionError:
            return ToolResponse.error(
                code=ToolErrorCode.ACCESS_DENIED,
                message=f"无权访问目录 '{path}'"
            )
        except Exception as e:
            return ToolResponse.error(
                code=ToolErrorCode.INTERNAL_ERROR,
                message=f"列出目录失败：{str(e)}"
            )

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"

    def _format_time(self, timestamp: float) -> str:
        """格式化时间戳（兼容 Windows 和 Linux）"""
        from datetime import datetime
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _resolve_path(self, path: str) -> Path:
        """解析相对路径（兼容 Windows 和 Linux）"""
        # 统一路径分隔符：将反斜杠转换为正斜杠
        path = path.replace('\\', '/')

        # 如果是绝对路径，直接使用
        if os.path.isabs(path):
            return Path(path)

        # 否则相对于 working_dir
        return self.working_dir / path


class WriteTool(Tool):
    """文件写入工具

    功能：
    - 创建或覆盖文件
    - 乐观锁冲突检测（如果文件已存在）
    - 原子写入（临时文件 + rename）
    - 自动备份原文件

    参数：
    - path: 文件路径
    - content: 文件内容
    - file_mtime_ms: 缓存的 mtime（可选，用于冲突检测）
    """

    def __init__(
        self,
        project_root: str = ".",
        working_dir: Optional[str] = None,
        registry: Optional['ToolRegistry'] = None
    ):
        super().__init__(
            name="Write",
            description="创建或覆盖文件，支持冲突检测和原子写入",
            expandable=False
        )
        self.project_root = Path(project_root).resolve()
        self.working_dir = Path(working_dir).resolve() if working_dir else self.project_root
        self.registry = registry

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="文件路径（相对项目根目录）",
                required=True
            ),
            ToolParameter(
                name="content",
                type="string",
                description="文件内容",
                required=True
            ),
            ToolParameter(
                name="file_mtime_ms",
                type="integer",
                description="缓存的文件修改时间（用于冲突检测）",
                required=False
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行文件写入"""
        path = parameters.get("path")
        content = parameters.get("content")
        cached_mtime = parameters.get("file_mtime_ms")

        if not path:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="缺少必需参数: path"
            )

        if content is None:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="缺少必需参数: content"
            )

        try:
            # 解析路径
            full_path = self._resolve_path(path)
            backup_path = None

            # 检查文件是否存在
            if full_path.exists():
                # 获取当前文件元数据
                current_mtime = os.path.getmtime(full_path)
                current_mtime_ms = int(current_mtime * 1000)

                # 检查乐观锁冲突
                if cached_mtime is not None:
                    if current_mtime_ms != cached_mtime:
                        return ToolResponse.error(
                            code=ToolErrorCode.CONFLICT,
                            message=f"文件自上次读取后被修改。当前 mtime={current_mtime_ms}, 缓存 mtime={cached_mtime}",
                            context={
                                "current_mtime_ms": current_mtime_ms,
                                "cached_mtime_ms": cached_mtime
                            }
                        )

                # 备份原文件
                backup_path = self._backup_file(full_path)
            else:
                # 确保父目录存在
                full_path.parent.mkdir(parents=True, exist_ok=True)

            # 原子写入（临时文件 + 重命名）
            temp_path = full_path.with_suffix(full_path.suffix + '.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # 原子重命名
            os.replace(temp_path, full_path)

            size_bytes = len(content.encode('utf-8'))

            return ToolResponse.success(
                text=f"成功写入 {path} ({size_bytes} 字节)",
                data={
                    "written": True,
                    "size_bytes": size_bytes,
                    "backup_path": str(backup_path.relative_to(self.working_dir)) if backup_path else None
                }
            )

        except PermissionError:
            return ToolResponse.error(
                code=ToolErrorCode.PERMISSION_DENIED,
                message=f"无权限写入 '{path}'"
            )
        except Exception as e:
            return ToolResponse.error(
                code=ToolErrorCode.INTERNAL_ERROR,
                message=f"写入文件失败：{str(e)}"
            )

    def _backup_file(self, full_path: Path) -> Path:
        """备份文件"""
        backup_dir = full_path.parent / ".backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{full_path.name}.{timestamp}.bak"
        backup_path = backup_dir / backup_name

        shutil.copy2(full_path, backup_path)
        return backup_path

    def _resolve_path(self, path: str) -> Path:
        """解析相对路径"""
        if os.path.isabs(path):
            return Path(path)
        return self.working_dir / path


class EditTool(Tool):
    """文件编辑工具

    功能：
    - 精确替换文件内容（old_string 必须唯一匹配）
    - 乐观锁冲突检测
    - 自动备份原文件

    参数：
    - path: 文件路径
    - old_string: 要替换的内容
    - new_string: 替换后的内容
    - file_mtime_ms: 缓存的 mtime（可选）
    """

    def __init__(
        self,
        project_root: str = ".",
        working_dir: Optional[str] = None,
        registry: Optional['ToolRegistry'] = None
    ):
        super().__init__(
            name="Edit",
            description="精确替换文件内容，支持冲突检测和自动备份",
            expandable=False
        )
        self.project_root = Path(project_root).resolve()
        self.working_dir = Path(working_dir).resolve() if working_dir else self.project_root
        self.registry = registry

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="要编辑的文件路径（相对项目根目录）",
                required=True
            ),
            ToolParameter(
                name="old_string",
                type="string",
                description="要替换的内容（必须唯一匹配）",
                required=True
            ),
            ToolParameter(
                name="new_string",
                type="string",
                description="替换后的内容",
                required=True
            ),
            ToolParameter(
                name="file_mtime_ms",
                type="integer",
                description="缓存的文件修改时间（用于冲突检测）",
                required=False
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行文件编辑"""
        path = parameters.get("path")
        old_string = parameters.get("old_string")
        new_string = parameters.get("new_string")
        cached_mtime = parameters.get("file_mtime_ms")

        if not path:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="缺少必需参数: path"
            )

        if old_string is None:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="缺少必需参数: old_string"
            )

        if new_string is None:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="缺少必需参数: new_string"
            )

        try:
            # 解析路径
            full_path = self._resolve_path(path)

            if not full_path.exists():
                return ToolResponse.error(
                    code=ToolErrorCode.NOT_FOUND,
                    message=f"文件 '{path}' 不存在"
                )

            # 获取当前文件元数据
            current_mtime = os.path.getmtime(full_path)
            current_mtime_ms = int(current_mtime * 1000)

            # 检查乐观锁冲突
            if cached_mtime is not None and current_mtime_ms != cached_mtime:
                return ToolResponse.error(
                    code=ToolErrorCode.CONFLICT,
                    message=f"文件自上次读取后被修改。当前 mtime={current_mtime_ms}, 缓存 mtime={cached_mtime}",
                    context={
                        "current_mtime_ms": current_mtime_ms,
                        "cached_mtime_ms": cached_mtime
                    }
                )

            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查 old_string 是否唯一匹配
            matches = content.count(old_string)
            if matches != 1:
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message=f"old_string 必须唯一匹配文件内容。找到 {matches} 处匹配。",
                    data={"matches": matches}
                )

            # 执行替换
            new_content = content.replace(old_string, new_string)

            # 备份原文件
            backup_path = self._backup_file(full_path)

            # 写入新内容
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            changed_bytes = len(new_string.encode('utf-8')) - len(old_string.encode('utf-8'))

            return ToolResponse.success(
                text=f"成功编辑 {path} (变化 {changed_bytes:+d} 字节)",
                data={
                    "modified": True,
                    "changed_bytes": changed_bytes,
                    "backup_path": str(backup_path.relative_to(self.working_dir))
                }
            )

        except PermissionError:
            return ToolResponse.error(
                code=ToolErrorCode.PERMISSION_DENIED,
                message=f"无权限编辑 '{path}'"
            )
        except Exception as e:
            return ToolResponse.error(
                code=ToolErrorCode.INTERNAL_ERROR,
                message=f"编辑文件失败：{str(e)}"
            )

    def _backup_file(self, full_path: Path) -> Path:
        """备份文件"""
        backup_dir = full_path.parent / ".backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{full_path.name}.{timestamp}.bak"
        backup_path = backup_dir / backup_name

        shutil.copy2(full_path, backup_path)
        return backup_path

    def _resolve_path(self, path: str) -> Path:
        """解析相对路径"""
        if os.path.isabs(path):
            return Path(path)
        return self.working_dir / path


class MultiEditTool(Tool):
    """批量编辑工具

    功能：
    - 批量执行多个替换操作
    - 原子性保证（要么全部成功，要么全部失败）
    - 乐观锁冲突检测（所有替换前检查一次）

    参数：
    - path: 文件路径
    - edits: 替换列表 [{"old_string": "...", "new_string": "..."}]
    - file_mtime_ms: 缓存的 mtime（可选）
    """

    def __init__(
        self,
        project_root: str = ".",
        working_dir: Optional[str] = None,
        registry: Optional['ToolRegistry'] = None
    ):
        super().__init__(
            name="MultiEdit",
            description="批量替换文件内容，支持原子性和冲突检测",
            expandable=False
        )
        self.project_root = Path(project_root).resolve()
        self.working_dir = Path(working_dir).resolve() if working_dir else self.project_root
        self.registry = registry

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="要编辑的文件路径（相对项目根目录）",
                required=True
            ),
            ToolParameter(
                name="edits",
                type="array",
                description="替换列表，每项包含 old_string 和 new_string",
                required=True
            ),
            ToolParameter(
                name="file_mtime_ms",
                type="integer",
                description="缓存的文件修改时间（用于冲突检测）",
                required=False
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行批量编辑"""
        path = parameters.get("path")
        edits = parameters.get("edits")
        cached_mtime = parameters.get("file_mtime_ms")

        if not path:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="缺少必需参数: path"
            )

        if not edits or not isinstance(edits, list):
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="缺少必需参数: edits（必须是列表）"
            )

        try:
            # 解析路径
            full_path = self._resolve_path(path)

            if not full_path.exists():
                return ToolResponse.error(
                    code=ToolErrorCode.NOT_FOUND,
                    message=f"文件 '{path}' 不存在"
                )

            # 获取当前文件元数据
            current_mtime = os.path.getmtime(full_path)
            current_mtime_ms = int(current_mtime * 1000)

            # 检查乐观锁冲突（所有替换前检查一次）
            if cached_mtime is not None and current_mtime_ms != cached_mtime:
                return ToolResponse.error(
                    code=ToolErrorCode.CONFLICT,
                    message=f"文件自上次读取后被修改。所有替换已取消。当前 mtime={current_mtime_ms}, 缓存 mtime={cached_mtime}",
                    context={
                        "current_mtime_ms": current_mtime_ms,
                        "cached_mtime_ms": cached_mtime
                    }
                )

            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 验证所有替换操作
            for i, edit in enumerate(edits):
                old_string = edit.get("old_string")
                new_string = edit.get("new_string")

                if old_string is None or new_string is None:
                    return ToolResponse.error(
                        code=ToolErrorCode.INVALID_PARAM,
                        message=f"编辑项 {i} 缺少 old_string 或 new_string"
                    )

                # 检查是否唯一匹配
                matches = content.count(old_string)
                if matches != 1:
                    return ToolResponse.error(
                        code=ToolErrorCode.INVALID_PARAM,
                        message=f"编辑项 {i}: old_string 必须唯一匹配。找到 {matches} 处匹配。",
                        data={"edit_index": i, "matches": matches}
                    )

            # 执行所有替换（原子性）
            for edit in edits:
                content = content.replace(edit["old_string"], edit["new_string"])

            # 备份原文件
            backup_path = self._backup_file(full_path)

            # 写入新内容
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            changed_bytes = len(content.encode('utf-8')) - len(original_content.encode('utf-8'))

            return ToolResponse.success(
                text=f"成功执行 {len(edits)} 个替换操作 (变化 {changed_bytes:+d} 字节)",
                data={
                    "modified": True,
                    "num_edits": len(edits),
                    "changed_bytes": changed_bytes,
                    "backup_path": str(backup_path.relative_to(self.working_dir))
                }
            )

        except PermissionError:
            return ToolResponse.error(
                code=ToolErrorCode.PERMISSION_DENIED,
                message=f"无权限编辑 '{path}'"
            )
        except Exception as e:
            return ToolResponse.error(
                code=ToolErrorCode.INTERNAL_ERROR,
                message=f"批量编辑失败：{str(e)}"
            )

    def _backup_file(self, full_path: Path) -> Path:
        """备份文件"""
        backup_dir = full_path.parent / ".backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{full_path.name}.{timestamp}.bak"
        backup_path = backup_dir / backup_name

        shutil.copy2(full_path, backup_path)
        return backup_path

    def _resolve_path(self, path: str) -> Path:
        """解析相对路径"""
        if os.path.isabs(path):
            return Path(path)
        return self.working_dir / path

