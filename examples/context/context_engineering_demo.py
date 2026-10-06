"""上下文预算、整轮压缩和长输出回读；无需密钥。"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from hello_agents.context import ContextBuilder, ContextConfig, ContextPacket
from hello_agents.context.history import HistoryManager
from hello_agents.context.truncator import ObservationTruncator
from hello_agents.core.message import Message


def main():
    messages = [
        dict(role="system", content="根据资料规划，未知信息注明待确认。"),
        dict(role="user", content="杭州两日游，每天步行不超过 5 公里。"),
    ]
    packets = [
        ContextPacket(
            content="用户喜欢历史文化，预算 1500 元。",
            relevance_score=1.0,
            metadata={"source": "user:preferences"},
        ),
        ContextPacket(
            content="杭州教学景点资料。" * 3000,
            relevance_score=0.4,
            metadata={"source": "fixture:long-document"},
        ),
    ]
    result = ContextBuilder(ContextConfig(max_tokens=1000)).build_messages(
        messages, additional_packets=packets
    )
    assert result.diagnostics["estimated_tokens"] <= result.diagnostics["budget"]
    print(json.dumps(result.diagnostics, ensure_ascii=False, default=str))
    history = HistoryManager(min_retain_rounds=1)
    for request, answer in [
        ("预算 1500 元", "已记录"),
        ("步行上限改成 3 公里", "按新要求规划"),
    ]:
        history.append(Message(request, "user"))
        history.append(Message(answer, "assistant"))
    history.compress("已确认预算 1500 元。")  # 手工摘要，不冒充模型生成。
    assert history.get_history()[-2].content == "步行上限改成 3 公里"
    print([(m.role, m.content) for m in history.get_history()])
    with TemporaryDirectory() as directory:
        truncator = ObservationTruncator(
            max_lines=3, max_bytes=1024, output_dir=directory
        )
        output = "\n".join(f"景点条目 {i}" for i in range(30))
        truncated = truncator.truncate("search", output)
        assert truncated["truncated"] and Path(truncated["full_output_path"]).exists()
        print("工具预览：", truncated["preview"])
        print("完整输出已保存，可按 full_output_path 回读。")


if __name__ == "__main__":
    main()
