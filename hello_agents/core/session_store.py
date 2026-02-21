"""SessionStore - 会话持久化存储

职责：
- 保存会话到文件（原子写入）
- 从文件恢复会话
- 环境一致性检查
- 会话列表管理
"""

import json
import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from hashlib import sha256


class SessionStore:
    """会话存储器
    
    功能：
    - 保存会话到 JSON 文件
    - 从文件恢复会话
    - 环境一致性检查
    - 原子写入保证数据完整性
    
    用法示例：
    ```python
    store = SessionStore(session_dir="memory/sessions")
    
    # 保存会话
    filepath = store.save(
        agent_config={"name": "assistant", "llm_model": "gpt-4"},
        history=[...],
        tool_schema_hash="abc123",
        read_cache={},
        metadata={"total_tokens": 1000}
    )
    
    # 加载会话
    session_data = store.load(filepath)
    
    # 列出所有会话
    sessions = store.list_sessions()
    ```
    """
    
    def __init__(self, session_dir: str = "memory/sessions"):
        """初始化会话存储器
        
        Args:
            session_dir: 会话文件保存目录
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_session_id(self) -> str:
        """生成唯一的会话 ID
        
        格式：s-{timestamp}-{uuid}
        
        Returns:
            会话 ID
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        unique_suffix = uuid.uuid4().hex[:8]
        return f"s-{timestamp}-{unique_suffix}"
    
    def save(
        self,
        agent_config: Dict[str, Any],
        history: List[Any],
        tool_schema_hash: str,
        read_cache: Dict[str, Dict],
        metadata: Dict[str, Any],
        session_name: Optional[str] = None
    ) -> str:
        """保存会话
        
        Args:
            agent_config: Agent 配置信息
            history: 消息历史列表
            tool_schema_hash: 工具 Schema 哈希值
            read_cache: Read 工具的元数据缓存
            metadata: 会话元数据（tokens、steps、duration 等）
            session_name: 自定义会话名称（可选）
        
        Returns:
            保存的文件路径
        """
        # 生成会话 ID（只生成一次）
        session_id = self._generate_session_id()

        # 生成文件名
        if session_name:
            filename = f"{session_name}.json"
        else:
            filename = f"session-{session_id}.json"

        filepath = self.session_dir / filename

        # 构建会话数据
        session_data = {
            "session_id": session_id,
            "created_at": metadata.get("created_at", datetime.now().isoformat()),
            "saved_at": datetime.now().isoformat(),
            "agent_config": agent_config,
            "history": [
                msg.to_dict() if hasattr(msg, 'to_dict') else msg 
                for msg in history
            ],
            "tool_schema_hash": tool_schema_hash,
            "read_cache": read_cache,
            "metadata": metadata
        }
        
        # 原子写入（临时文件 + 重命名）
        temp_path = str(filepath) + ".tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        # 原子重命名
        os.replace(temp_path, filepath)
        
        return str(filepath)
    
    def load(self, filepath: str) -> Dict[str, Any]:
        """加载会话
        
        Args:
            filepath: 会话文件路径
        
        Returns:
            会话数据字典
        
        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: 文件格式错误
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        return session_data

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话

        Returns:
            会话信息列表，按保存时间倒序排列
        """
        sessions = []

        for filepath in self.session_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                sessions.append({
                    "filename": filepath.name,
                    "filepath": str(filepath),
                    "session_id": data.get("session_id"),
                    "created_at": data.get("created_at"),
                    "saved_at": data.get("saved_at"),
                    "metadata": data.get("metadata", {})
                })
            except Exception as e:
                print(f"⚠️ 警告：无法读取 {filepath}: {e}")

        # 按保存时间倒序
        sessions.sort(key=lambda x: x.get("saved_at", ""), reverse=True)

        return sessions

    def delete(self, session_name: str) -> bool:
        """删除会话

        Args:
            session_name: 会话名称（不含 .json 后缀）

        Returns:
            是否删除成功
        """
        filepath = self.session_dir / f"{session_name}.json"
        if filepath.exists():
            os.remove(filepath)
            return True
        return False

    def check_config_consistency(
        self,
        saved_config: Dict[str, Any],
        current_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查配置一致性

        Args:
            saved_config: 保存的配置
            current_config: 当前配置

        Returns:
            检查结果字典，包含 warnings 列表
        """
        warnings = []

        # 检查 LLM 提供商
        if saved_config.get("llm_provider") != current_config.get("llm_provider"):
            warnings.append(
                f"LLM 提供商变化: {saved_config.get('llm_provider')} → {current_config.get('llm_provider')}"
            )

        # 检查模型
        if saved_config.get("llm_model") != current_config.get("llm_model"):
            warnings.append(
                f"模型变化: {saved_config.get('llm_model')} → {current_config.get('llm_model')}"
            )

        # 检查 max_steps
        if saved_config.get("max_steps") != current_config.get("max_steps"):
            warnings.append(
                f"最大步数变化: {saved_config.get('max_steps')} → {current_config.get('max_steps')}"
            )

        return {
            "consistent": len(warnings) == 0,
            "warnings": warnings
        }

    def check_tool_schema_consistency(
        self,
        saved_hash: str,
        current_hash: str
    ) -> Dict[str, Any]:
        """检查工具 Schema 一致性

        Args:
            saved_hash: 保存的工具 Schema 哈希
            current_hash: 当前工具 Schema 哈希

        Returns:
            检查结果字典
        """
        changed = saved_hash != current_hash

        return {
            "changed": changed,
            "saved_hash": saved_hash,
            "current_hash": current_hash,
            "recommendation": "建议重新读取文件" if changed else "可以安全恢复"
        }

