"""可观测性使用示例

演示如何使用 TraceLogger 记录 Agent 执行过程：
- 双格式输出 (JSONL + HTML)
- 事件记录和统计
- 自动脱敏
"""

from hello_agents.observability.trace_logger import TraceLogger
from hello_agents.tools.response import ToolResponse, ToolStatus
from hello_agents.tools.errors import ToolErrorCode
import tempfile
from pathlib import Path
import time
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


def demo_basic_logging():
    """演示基本日志记录"""
    print("=" * 60)
    print("示例 1: 基本事件记录")
    print("=" * 60)

    # 使用相对路径
    output_dir = Path("memory/traces/demo")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 创建 TraceLogger
    logger = TraceLogger(
        output_dir=str(output_dir),
        sanitize=True,
        html_include_raw_response=False
    )

    print(f"\n会话 ID: {logger.session_id}")

    # 记录会话开始
    logger.log_event("session_start", {
        "agent_name": "DemoAgent",
        "llm_model": "gpt-4",
        "timestamp": time.time()
    })

    # 记录工具调用
    logger.log_event("tool_call", {
        "tool_name": "Calculator",
        "parameters": {"expression": "2 + 3"}
    }, step=1)

    # 记录工具结果
    logger.log_event("tool_result", {
        "tool_name": "Calculator",
        "status": "success",
        "result": "5"
    }, step=1)

    # 记录 LLM 响应
    logger.log_event("llm_response", {
        "content": "计算结果是 5",
        "tokens": 10
    }, step=1)

    # 记录会话结束
    logger.log_event("session_end", {
        "final_answer": "计算完成",
        "total_steps": 1
    })

    # 生成最终报告
    logger.finalize()

    # 验证文件生成
    jsonl_path = output_dir / f"trace-{logger.session_id}.jsonl"
    html_path = output_dir / f"trace-{logger.session_id}.html"

    assert jsonl_path.exists()
    assert html_path.exists()

    print(f"\n✅ JSONL 文件: {jsonl_path.name}")
    print(f"✅ HTML 文件: {html_path.name}")
    print(f"✅ 事件数量: {len(logger._events)}")


def demo_sanitization():
    """演示敏感信息脱敏"""
    print("\n" + "=" * 60)
    print("示例 2: 敏感信息脱敏")
    print("=" * 60)

    # 使用相对路径
    output_dir = Path("memory/traces/demo")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = TraceLogger(output_dir=str(output_dir), sanitize=True)

    # 记录包含敏感信息的事件
    logger.log_event("config_loaded", {
        "api_key": "sk-1234567890abcdef",
        "openai_api_key": "sk-abcdefghijklmnop",
        "file_path": "C:/Users/admin/project/config.py",
        "database_url": "postgresql://user:pass@localhost/db"
    })

    # 检查脱敏效果
    event = logger._events[-1]
    payload = event["payload"]

    print("\n脱敏后的数据:")
    print(f"  api_key: {payload.get('api_key', 'N/A')}")
    print(f"  openai_api_key: {payload.get('openai_api_key', 'N/A')}")
    print(f"  file_path: {payload.get('file_path', 'N/A')}")

    # 验证脱敏（脱敏格式为 sk-*** 而不是 [REDACTED]）
    assert "sk-1234567890abcdef" not in str(payload)
    assert "sk-abcdefghijklmnop" not in str(payload)
    assert "sk-***" in str(payload)
    assert "/Users/***/" in str(payload) or "C:/Users/***/project/config.py" in str(payload)

    # 确保文件正确关闭
    logger.finalize()
    print("\n✅ 敏感信息脱敏测试完成")


def demo_error_tracking():
    """演示错误追踪"""
    print("\n" + "=" * 60)
    print("示例 3: 错误追踪")
    print("=" * 60)

    # 使用相对路径
    output_dir = Path("memory/traces/demo")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = TraceLogger(output_dir=str(output_dir))

    logger.log_event("session_start", {"agent_name": "ErrorDemo"})

    # 记录成功的工具调用
    logger.log_event("tool_call", {"tool_name": "Read"}, step=1)
    logger.log_event("tool_result", {
        "tool_name": "Read",
        "status": "success"
    }, step=1)

    # 记录失败的工具调用
    logger.log_event("tool_call", {"tool_name": "Write"}, step=2)
    logger.log_event("tool_result", {
        "tool_name": "Write",
        "status": "error",
        "error_code": ToolErrorCode.PERMISSION_DENIED,
        "error_message": "没有写入权限"
    }, step=2)

    # 记录熔断事件
    logger.log_event("circuit_breaker", {
        "tool_name": "Write",
        "action": "opened",
        "reason": "连续失败 3 次"
    }, step=3)

    logger.log_event("session_end", {
        "status": "error",
        "error": "工具执行失败"
    })

    logger.finalize()

    # 统计错误
    error_events = [e for e in logger._events if "error" in str(e).lower()]
    print(f"\n错误事件数: {len(error_events)}")
    print("✅ 错误追踪测试完成")


def demo_statistics():
    """演示统计信息"""
    print("\n" + "=" * 60)
    print("示例 4: 统计信息")
    print("=" * 60)

    # 使用相对路径避免暴露系统路径
    output_dir = Path("memory/traces/demo")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = TraceLogger(output_dir=str(output_dir))

    logger.log_event("session_start", {"agent_name": "StatsDemo"})

    # 模拟多步执行
    for step in range(1, 6):
        logger.log_event("tool_call", {"tool_name": f"Tool{step}"}, step=step)
        logger.log_event("tool_result", {
            "tool_name": f"Tool{step}",
            "status": "success"
        }, step=step)
        logger.log_event("model_output", {
            "usage": {
                "total_tokens": 50 + step * 10,
                "cost": 0.001 * step
            }
        }, step=step)

    logger.log_event("session_end", {"total_steps": 5})

    # 生成统计（使用正确的方法名）
    stats = logger._compute_stats()

    print(f"\n统计信息:")
    print(f"  总步数: {stats['total_steps']}")
    print(f"  工具调用次数: {len(stats['tool_calls'])}")
    print(f"  总 Tokens: {stats['total_tokens']}")
    print(f"  总成本: ${stats['total_cost']:.4f}")
    print(f"  错误数: {len(stats['errors'])}")
    print(f"  会话时长: {stats['duration_seconds']:.2f}s")

    logger.finalize()
    print("\n✅ 统计信息测试完成")


if __name__ == "__main__":
    demo_basic_logging()
    demo_sanitization()
    demo_error_tracking()
    demo_statistics()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成！")
    print("=" * 60)

