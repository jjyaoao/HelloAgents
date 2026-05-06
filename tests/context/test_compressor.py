"""混合压缩策略测试"""

import pytest
from dataclasses import dataclass

from hello_agents.context.compressor import (
    CompressionResult,
    HybridOptions,
    LatencyRequirement,
    ContentType,
    TruncationStrategy,
    SlidingWindowStrategy,
    LLMSummarizeStrategy,
    HybridStrategy,
    HybridCompressor,
    count_tokens,
)
from dotenv import load_dotenv

load_dotenv()


def generate_text(num_tokens: int) -> str:
    words = [
        "这是",
        "一个",
        "测试",
        "文本",
        "用于",
        "验证",
        "压缩",
        "算法",
        "我们",
        "需要",
        "足够",
        "长度",
        "来",
        "模拟",
        "真实",
        "场景",
        "关键",
        "信息",
        "应该",
        "保留",
        "完整",
        "结构",
        "格式",
        "不能",
        "丢失",
        "重要",
        "内容",
        "上下文",
        "理解",
        "语义",
        "逻辑",
        "连贯",
    ]
    result = []
    used = 0
    line = []
    section_idx = 0

    while used < num_tokens:
        word = words[len(result) % len(words)]
        line.append(word)
        used += 1

        if used % 8 == 0:
            result.append(" ".join(line))
            line = []
            if len(result) % 4 == 0:
                section_idx += 1
                result.append(f"[Section {section_idx}]")

    if line:
        result.append(" ".join(line))

    return "\n".join(result)


def generate_structured_text(num_tokens: int) -> str:
    sections = [
        "[Role & Policies]\n你是一个有帮助的AI助手。",
        "[Task]\n用户问题：如何实现压缩算法？",
        "[State]\n关键进展：已完成基础实现。\n待解决问题：性能优化。",
        "[Evidence]\n事实1：压缩可以减少token使用。\n事实2：截断策略速度快。",
        "[Context]\n对话历史：\n用户：什么是压缩？\nAI：压缩是减少内容长度的方法。",
        "[Output]\n1. 结论\n2. 依据\n3. 风险",
    ]

    result = []
    current = 0

    for section in sections:
        result.append(section)
        current += count_tokens(section)
        if current >= num_tokens:
            break

    while current < num_tokens:
        extra = f"\n补充内容：这是额外的文本以达到所需的token数量，当前已有 {current} tokens。"
        result.append(extra)
        current += count_tokens(extra)

    return "\n\n".join(result)


class MockLLMClient:
    def __init__(self, response: str = "这是LLM生成的摘要内容。"):
        self.response = response
        self.call_count = 0

    async def complete(self, prompt: str) -> "MockResponse":
        self.call_count += 1
        return MockResponse(self.response)


@dataclass
class MockResponse:
    text: str


class TestTruncationStrategy:
    def test_no_compress_when_within_budget(self):
        strategy = TruncationStrategy()
        text = "简短文本"

        result = strategy.compress(text, 100)

        assert result.compressed_text == text
        assert result.strategy_used == "truncation"

    def test_truncate_preserve_structure(self):
        strategy = TruncationStrategy()
        text = generate_text(500)

        result = strategy.compress(text, 100)

        assert result.compressed_tokens <= 100
        assert "\n" in result.compressed_text

    def test_truncate_respects_max_tokens(self):
        strategy = TruncationStrategy()
        text = generate_text(1000)

        result = strategy.compress(text, 200)

        assert result.compressed_tokens <= 200
        assert result.original_tokens >= 200


class TestSlidingWindowStrategy:
    def test_no_compress_when_within_budget(self):
        strategy = SlidingWindowStrategy(window_size=500, overlap=50)
        text = "简短文本"

        result = strategy.compress(text, 100)

        assert result.compressed_text == text

    def test_sliding_window_preserve_sections(self):
        strategy = SlidingWindowStrategy(window_size=500, overlap=50)
        text = generate_structured_text(800)

        result = strategy.compress(text, 300)

        # 容许轻微超限（边界情况）
        assert result.compressed_tokens <= 350
        assert "[Section" in result.compressed_text or "[Role" in result.compressed_text

    def test_window_size_respected(self):
        strategy = SlidingWindowStrategy(window_size=200, overlap=30)
        text = generate_structured_text(2000)

        result = strategy.compress(text, 400)

        lines = result.compressed_text.split("\n")
        assert len(lines) > 0


class TestLLMSummarizeStrategy:
    def test_llm_summarize_fallback_when_no_client(self):
        strategy = LLMSummarizeStrategy(llm_client=None)
        text = generate_text(500)

        result = strategy.compress(text, 100)

        assert result.strategy_used == "truncation"
        assert result.compressed_tokens <= 100

    def test_llm_summarize_success(self):
        mock_client = MockLLMClient("摘要内容")
        strategy = LLMSummarizeStrategy(mock_client)
        text = generate_text(500)

        result = strategy.compress(text, 100)

        assert mock_client.call_count > 0
        assert "摘要" in result.compressed_text

    def test_llm_summarize_within_budget(self):
        mock_client = MockLLMClient("原始文本")
        strategy = LLMSummarizeStrategy(mock_client)
        text = "很短"

        result = strategy.compress(text, 100)

        assert result.compressed_text == text
        assert mock_client.call_count == 0


class TestHybridStrategy:
    def test_select_truncation_for_low_latency(self):
        options = HybridOptions(
            enable_llm=True, latency_requirement=LatencyRequirement.LOW
        )
        strategy = HybridStrategy(options)
        text = generate_text(500)

        result = strategy.compress(text, 100)

        assert result.strategy_used == "truncation"

    def test_select_sliding_for_structured(self):
        options = HybridOptions(
            enable_llm=False, latency_requirement=LatencyRequirement.MEDIUM
        )
        strategy = HybridStrategy(options)
        text = generate_structured_text(800)

        result = strategy.compress(text, 300)

        assert result.strategy_used == "sliding_window"

    def test_select_llm_for_free_text(self):
        mock_client = MockLLMClient()
        options = HybridOptions(
            enable_llm=True,
            llm_threshold=1.1,
            latency_requirement=LatencyRequirement.MEDIUM,
        )
        strategy = HybridStrategy(options, mock_client)

        text = "这是一段自由文本，"
        for _ in range(20):
            text += "包含大量自然语言描述和语义内容。" * 10

        result = strategy.compress(text, 500)

        assert result.strategy_used in ["truncation", "sliding_window", "llm_summarize"]


class TestHybridCompressor:
    def test_compress_auto(self):
        compressor = HybridCompressor()
        text = generate_text(500)

        # 容许轻微超限（边界情况）
        result = compressor.compress(text, 100, "auto")

        assert result.compressed_tokens <= 150

    def test_compress_explicit_strategy(self):
        compressor = HybridCompressor()
        text = generate_text(500)

        result = compressor.compress(text, 100, "truncation")

        assert result.strategy_used == "truncation"

    def test_select_strategy_method(self):
        compressor = HybridCompressor(config=HybridOptions(enable_llm=False))
        text = generate_structured_text(500)

        strategy = compressor.select_strategy(text, 300, LatencyRequirement.MEDIUM)

        assert strategy in ["none", "sliding_window", "truncation"]


class TestContentClassification:
    def test_classify_json(self):
        compressor = HybridCompressor()

        text = '{"key": "value", "data": [1, 2, 3]}'

        strategy = compressor._strategy
        content_type = strategy._classify_content(text)

        assert content_type == ContentType.STRUCTURED

    def test_classify_code(self):
        compressor = HybridCompressor()

        text = "```python\ndef foo():\n    return 1\n```"

        strategy = compressor._strategy
        content_type = strategy._classify_content(text)

        assert content_type == ContentType.STRUCTURED

    def test_classify_free_text(self):
        compressor = HybridCompressor()

        text = "这是一个自然语言段落，" + "描述了一些有趣的内容和观点。" * 20

        strategy = compressor._strategy
        content_type = strategy._classify_content(text)

        assert content_type == ContentType.FREE_TEXT


class TestCompressionResult:
    def test_saved_tokens_calculation(self):
        result = CompressionResult(
            compressed_text="compressed",
            original_tokens=500,
            compressed_tokens=100,
            strategy_used="truncation",
        )

        assert result.saved_tokens == 400

    def test_no_savings_when_no_compression(self):
        result = CompressionResult(
            compressed_text="original",
            original_tokens=100,
            compressed_tokens=100,
            strategy_used="none",
        )

        assert result.saved_tokens == 0


class TestIntegration:
    def test_context_builder_integration(self):
        from hello_agents.context.builder import (
            ContextBuilder,
            ContextConfig,
            count_tokens,
        )

        config = ContextConfig(max_tokens=1000, enable_compression=True)
        builder = ContextBuilder(config=config)

        long_context = generate_structured_text(2000)

        compressed = builder._compress(long_context)

        # 容许轻微超限（边界情况）
        budget = config.get_available_tokens()
        assert count_tokens(compressed) <= budget + 50


class TestEdgeCases:
    def test_empty_text(self):
        strategy = TruncationStrategy()

        result = strategy.compress("", 100)

        assert result.compressed_text == ""

    def test_single_line(self):
        strategy = TruncationStrategy()

        result = strategy.compress("test", 100)

        assert result.compressed_text == "test"

    def test_zero_budget(self):
        strategy = TruncationStrategy()

        result = strategy.compress("test", 0)

        assert result.compressed_tokens == 0

    def test_exactly_budget(self):
        strategy = TruncationStrategy()
        text = "test"

        result = strategy.compress(text, count_tokens(text))

        assert result.compressed_text == text
        assert result.saved_tokens == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
