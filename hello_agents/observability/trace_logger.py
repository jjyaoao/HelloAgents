"""TraceLogger - 双格式 Trace 记录器

输出格式：
- JSONL: 机器可读，流式追加，支持 jq 分析
- HTML: 人类可读，可视化界面，内置统计面板
"""

import json
import uuid
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path


class TraceLogger:
    """双格式 Trace Logger
    
    特性：
    - JSONL 流式写入（实时追加）
    - HTML 增量渲染（实时可查看）
    - 自动脱敏（API Key、路径）
    - 内置统计面板（Token、工具调用、错误）
    
    使用示例：
        logger = TraceLogger(output_dir="memory/traces")
        logger.log_event("session_start", {"agent_name": "MyAgent"})
        logger.log_event("tool_call", {"tool_name": "Calculator"}, step=1)
        logger.finalize()  # 生成最终 HTML
    """
    
    def __init__(
        self,
        output_dir: str = "memory/traces",
        sanitize: bool = True,
        html_include_raw_response: bool = False
    ):
        """初始化 TraceLogger
        
        Args:
            output_dir: 输出目录
            sanitize: 是否脱敏敏感信息
            html_include_raw_response: HTML 是否包含原始响应
        """
        self.output_dir = Path(output_dir)
        self.sanitize = sanitize
        self.html_include_raw = html_include_raw_response
        
        # 生成会话 ID
        self.session_id = self._generate_session_id()
        
        # 事件缓存（用于生成统计和最终 HTML）
        self._events: List[Dict] = []
        
        # 确保目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # JSONL 文件路径
        self.jsonl_path = self.output_dir / f"trace-{self.session_id}.jsonl"
        
        # 打开 JSONL 文件（流式写入）
        self.jsonl_file = open(self.jsonl_path, 'w', encoding='utf-8')
        
        # HTML 文件路径
        self.html_path = self.output_dir / f"trace-{self.session_id}.html"
        
        # 打开 HTML 文件（增量写入）
        self.html_file = open(self.html_path, 'w', encoding='utf-8')
        
        # 写入 HTML 头部
        self._write_html_header()
    
    def _generate_session_id(self) -> str:
        """生成会话 ID
        
        格式: s-YYYYMMDD-HHMMSS-xxxx
        示例: s-20250118-143052-a3f2
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        random_suffix = uuid.uuid4().hex[:4]
        return f"s-{timestamp}-{random_suffix}"
    
    def log_event(
        self,
        event: str,
        payload: Dict[str, Any],
        step: Optional[int] = None
    ):
        """记录事件
        
        Args:
            event: 事件类型（session_start, tool_call, tool_result, etc.）
            payload: 事件数据
            step: ReAct 循环的步骤序号（可选）
        """
        # 构造事件对象
        event_obj = {
            "ts": datetime.now().isoformat(),
            "session_id": self.session_id,
            "step": step,
            "event": event,
            "payload": payload
        }
        
        # 脱敏
        if self.sanitize:
            event_obj = self._sanitize_event(event_obj)
        
        # 追加到缓存
        self._events.append(event_obj)
        
        # 流式写入 JSONL
        self.jsonl_file.write(json.dumps(event_obj, ensure_ascii=False) + "\n")
        self.jsonl_file.flush()
        
        # 增量写入 HTML 事件片段
        self._write_html_event(event_obj)
    
    def _sanitize_event(self, event: Dict) -> Dict:
        """脱敏敏感信息

        脱敏规则：
        - API Key: sk-xxx, Bearer xxx -> sk-***, Bearer ***
        - 路径中的用户名: /Users/xxx/ -> /Users/***/
        """
        import copy
        event = copy.deepcopy(event)

        # 递归脱敏 payload
        event["payload"] = self._sanitize_value(event.get("payload", {}))

        return event

    def _sanitize_value(self, value: Any) -> Any:
        """递归脱敏值

        Args:
            value: 待脱敏的值（可能是字符串、字典、列表等）

        Returns:
            脱敏后的值
        """
        if isinstance(value, str):
            # 脱敏字符串
            # API Key: sk-xxx -> sk-***
            value = re.sub(r'sk-[a-zA-Z0-9]+', 'sk-***', value)
            # Bearer Token: Bearer xxx -> Bearer ***
            value = re.sub(r'Bearer\s+[a-zA-Z0-9_\-]+', 'Bearer ***', value)
            # 路径中的用户名
            value = re.sub(r'(/Users/|/home/|C:\\Users\\)[^/\\]+', r'\1***', value)
            return value
        elif isinstance(value, dict):
            # 递归处理字典
            return {k: self._sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            # 递归处理列表
            return [self._sanitize_value(item) for item in value]
        else:
            # 其他类型直接返回
            return value

    def finalize(self):
        """生成最终 HTML 并关闭文件

        步骤：
        1. 计算统计数据
        2. 写入 HTML 尾部（包含统计面板）
        3. 关闭所有文件
        """
        # 计算统计数据
        stats = self._compute_stats()

        # 写入 HTML 尾部（统计面板 + 脚本）
        self._write_html_footer(stats)

        # 关闭文件
        self.jsonl_file.close()
        self.html_file.close()

        print(f"✅ Trace 已保存:")
        print(f"   JSONL: {self.jsonl_path}")
        print(f"   HTML:  {self.html_path}")

    def _compute_stats(self) -> Dict[str, Any]:
        """计算统计数据

        Returns:
            统计数据字典
        """
        stats = {
            "total_steps": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "tool_calls": {},  # {tool_name: count}
            "errors": [],
            "duration_seconds": 0.0,
            "model_calls": 0,
        }

        session_start = None
        session_end = None

        for event in self._events:
            # 会话时长
            if event["event"] == "session_start":
                session_start = datetime.fromisoformat(event["ts"])
            if event["event"] == "session_end":
                session_end = datetime.fromisoformat(event["ts"])

            # 步骤数
            if event.get("step"):
                stats["total_steps"] = max(stats["total_steps"], event["step"])

            # Token 统计
            if event["event"] == "model_output":
                usage = event.get("payload", {}).get("usage", {})
                stats["total_tokens"] += usage.get("total_tokens", 0)
                stats["total_cost"] += usage.get("cost", 0.0)
                stats["model_calls"] += 1

            # 工具调用统计
            if event["event"] == "tool_call":
                tool_name = event["payload"].get("tool_name", "unknown")
                stats["tool_calls"][tool_name] = stats["tool_calls"].get(tool_name, 0) + 1

            # 错误统计
            if event["event"] == "error":
                stats["errors"].append({
                    "step": event.get("step"),
                    "type": event["payload"].get("error_type"),
                    "message": event["payload"].get("message")
                })

        # 计算时长
        if session_start and session_end:
            stats["duration_seconds"] = (session_end - session_start).total_seconds()

        return stats

    def _write_html_header(self):
        """写入 HTML 头部"""
        header = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Trace: {self.session_id}</title>
    <style>
        body {{
            font-family: 'Consolas', 'Monaco', monospace;
            padding: 20px;
            background: #1a1a1a;
            color: #e0e0e0;
            margin: 0;
        }}
        .header {{
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            color: #4af626;
        }}
        .stats-panel {{
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-item {{
            background: #1a1a1a;
            padding: 15px;
            border-radius: 5px;
            border-left: 3px solid #4af626;
        }}
        .stat-label {{
            display: block;
            color: #888;
            font-size: 12px;
            margin-bottom: 5px;
        }}
        .stat-value {{
            display: block;
            color: #e0e0e0;
            font-size: 24px;
            font-weight: bold;
        }}
        .tool-stats {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .tool-stats th, .tool-stats td {{
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #333;
        }}
        .tool-stats th {{
            color: #4af626;
        }}
        .error-list {{
            list-style: none;
            padding: 0;
        }}
        .error-list li {{
            background: #331111;
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 3px solid #ff4444;
        }}
        .events-container {{
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
        }}
        .event {{
            border: 1px solid #333;
            margin: 10px 0;
            padding: 15px;
            border-radius: 5px;
            background: #1a1a1a;
        }}
        .event-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }}
        .step {{
            color: #888;
            font-size: 12px;
        }}
        .timestamp {{
            color: #666;
            font-size: 11px;
        }}
        .event-type {{
            color: #4af626;
            font-weight: bold;
        }}
        .expandable {{
            cursor: pointer;
            color: #4af626;
            user-select: none;
        }}
        .expandable:hover {{
            color: #6fff48;
        }}
        .details {{
            display: none;
            margin-top: 10px;
            padding: 10px;
            background: #0d0d0d;
            border-radius: 5px;
            overflow-x: auto;
        }}
        .details pre {{
            margin: 0;
            color: #e0e0e0;
        }}
        .tool-call {{
            border-left: 3px solid #4af626;
        }}
        .tool-result {{
            border-left: 3px solid #ffd700;
        }}
        .error {{
            border-left: 3px solid #ff4444;
            background: #2a1a1a;
        }}
        .model-output {{
            border-left: 3px solid #00bfff;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Trace Session: {self.session_id}</h1>
        <p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="events-container">
        <h2>📋 事件列表</h2>
"""
        self.html_file.write(header)
        self.html_file.flush()

    def _write_html_event(self, event: Dict):
        """写入单个事件的 HTML 片段（增量写入）"""
        event_type = event["event"]
        step = event.get("step", "")
        timestamp = event["ts"]
        payload = event.get("payload", {})

        # 确定 CSS 类
        css_class = "event"
        if event_type == "tool_call":
            css_class += " tool-call"
        elif event_type == "tool_result":
            css_class += " tool-result"
        elif event_type == "error":
            css_class += " error"
        elif event_type == "model_output":
            css_class += " model-output"

        # 生成唯一 ID
        details_id = f"details-{len(self._events)}"

        # 格式化 payload
        payload_json = json.dumps(payload, indent=2, ensure_ascii=False)

        # 生成事件 HTML
        event_html = f"""
        <div class="{css_class}">
            <div class="event-header">
                <span class="step">Step {step if step else '-'}</span>
                <span class="timestamp">{timestamp}</span>
                <span class="event-type">{event_type}</span>
                <span class="expandable" onclick="toggleDetails('{details_id}')">[▼ 详情]</span>
            </div>
            <div id="{details_id}" class="details">
                <pre>{payload_json}</pre>
            </div>
        </div>
"""
        self.html_file.write(event_html)
        self.html_file.flush()

    def _write_html_footer(self, stats: Dict[str, Any]):
        """写入 HTML 尾部（统计面板 + 脚本）"""
        # 构建工具调用统计表格
        tool_stats_rows = ""
        for tool_name, count in sorted(stats["tool_calls"].items(), key=lambda x: x[1], reverse=True):
            tool_stats_rows += f"<tr><td>{tool_name}</td><td>{count}</td></tr>\n"

        # 构建错误列表
        error_list_html = ""
        if stats["errors"]:
            error_items = ""
            for error in stats["errors"]:
                step = error.get("step", "?")
                error_type = error.get("type", "UNKNOWN")
                message = error.get("message", "")
                error_items += f"<li>Step {step}: <strong>{error_type}</strong> - {message}</li>\n"
            error_list_html = f"""
        <h3>❌ 错误列表 ({len(stats["errors"])})</h3>
        <ul class="error-list">
            {error_items}
        </ul>
"""

        footer = f"""
    </div>

    <div class="stats-panel">
        <h2>📊 会话统计</h2>
        <div class="stats-grid">
            <div class="stat-item">
                <span class="stat-label">总步骤数</span>
                <span class="stat-value">{stats["total_steps"]}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">总 Token</span>
                <span class="stat-value">{stats["total_tokens"]:,}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">总成本</span>
                <span class="stat-value">${stats["total_cost"]:.4f}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">会话时长</span>
                <span class="stat-value">{stats["duration_seconds"]:.1f}s</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">模型调用次数</span>
                <span class="stat-value">{stats["model_calls"]}</span>
            </div>
        </div>

        <h3>🔧 工具调用统计</h3>
        <table class="tool-stats">
            <tr><th>工具名称</th><th>调用次数</th></tr>
            {tool_stats_rows if tool_stats_rows else '<tr><td colspan="2">无工具调用</td></tr>'}
        </table>

        {error_list_html}
    </div>

    <script>
        function toggleDetails(id) {{
            const el = document.getElementById(id);
            if (el.style.display === 'none' || el.style.display === '') {{
                el.style.display = 'block';
            }} else {{
                el.style.display = 'none';
            }}
        }}
    </script>
</body>
</html>
"""
        self.html_file.write(footer)
        self.html_file.flush()

    def __enter__(self):
        """上下文管理器：进入"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器：退出（自动 finalize）"""
        # 如果发生异常，记录错误事件
        if exc_type is not None:
            self.log_event(
                "error",
                {
                    "error_type": exc_type.__name__,
                    "message": str(exc_val),
                    "stacktrace": str(exc_tb)
                }
            )

        # 自动 finalize
        self.finalize()

        # 不抑制异常
        return False


