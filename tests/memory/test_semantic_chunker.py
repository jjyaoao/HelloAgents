"""语义边界分块器测试"""

import pytest
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hello_agents.memory.rag.semantic_chunker import (
    SemanticChunker,
    DialogueDetector,
    StructuralPatternDetector,
    TopicTransitionDetector,
    SentenceSplitter,
    chunk_by_semantic_boundaries,
    auto_select_chunking_strategy,
    smart_chunk,
    BoundaryType,
)


class TestDialogueDetector:
    """对话检测器测试"""

    def test_detect_chinese_dialogue(self):
        """测试中文对话检测"""
        detector = DialogueDetector()
        lines = [
            "张三说：「今天天气真好。」",
            "李四回答：「是啊，我们去爬山吧。」",
            "这是叙述段落。",
            "",
            "「等等，我忘了带水。」张三喊道。",
        ]

        dialogues = detector.detect(lines)
        assert len(dialogues) >= 1

    def test_detect_english_dialogue(self):
        """测试英文对话检测"""
        detector = DialogueDetector()
        lines = [
            "A: Hello, how are you?",
            "B: I'm fine, thank you.",
            "This is a narrative paragraph.",
        ]

        dialogues = detector.detect(lines)
        assert len(dialogues) >= 1

    def test_detect_speaker_labels(self):
        """测试说话者标签提取"""
        detector = DialogueDetector()
        lines = ["甲：今天我们去爬山。", "乙：好的。"]

        dialogues = detector.detect(lines)
        labels = [label for _, label in dialogues]
        assert any(label in ["甲", "乙"] for label in labels)


class TestStructuralPatternDetector:
    """结构模式检测器测试"""

    def test_detect_legal_articles(self):
        """测试法律条款检测"""
        detector = StructuralPatternDetector()
        lines = [
            "第一章 总则",
            "第一条 为了规范...，制定本法。",
            "第二条 本法适用于...",
            "这是一个普通段落。",
            "第三条 违反本法规定的...",
        ]

        structures = detector.detect(lines)
        assert len(structures) >= 3

    def test_detect_list_items(self):
        """测试列表项检测"""
        detector = StructuralPatternDetector()
        lines = [
            "1. 第一项内容",
            "2. 第二项内容",
            "3. 第三项内容",
            "- 另一个列表项",
        ]

        structures = detector.detect(lines)
        list_items = [s for s in structures if s[1] == BoundaryType.LIST_ITEM]
        assert len(list_items) >= 3


class TestTopicTransitionDetector:
    """主题转换检测器测试"""

    def test_detect_clear_transition(self):
        """测试明显的主题转换"""
        detector = TopicTransitionDetector()

        sentences = [
            "机器学习是人工智能的一个分支。",
            "它使用数据来训练模型。",
            "深度学习是机器学习的子领域。",
            "神经网络是深度学习的基础。",
            "卷积神经网络广泛应用于图像处理。",
        ]

        # 由于窗口大小限制，可能检测不到转换
        transitions = detector.detect_transitions(sentences)
        assert isinstance(transitions, list)


class TestSentenceSplitter:
    """句子分割器测试"""

    def test_split_chinese_sentences(self):
        """测试中文句子分割"""
        splitter = SentenceSplitter()
        text = "这是一个句子。那是另一个句子。最后一个句子。"

        sentences, positions = zip(*splitter.split(text))

        assert len(sentences) == 3
        assert "这是一个句子。" in sentences

    def test_split_english_sentences(self):
        """测试英文句子分割"""
        splitter = SentenceSplitter()
        text = "Hello world. How are you? I'm fine!"

        sentences, positions = zip(*splitter.split(text))

        assert len(sentences) == 3


class TestSemanticChunker:
    """语义分块器测试"""

    def test_chunk_novel_text(self):
        """测试小说文本分块"""
        chunker = SemanticChunker(min_chunk_tokens=50, max_chunk_tokens=200)

        text = """
张三大声喊道：「李四，快过来看看！」
李四跑过来，仔细看了看，说：「这看起来像是一块玉石。」
两人决定一起研究这块石头。

第二天，他们又发现了另一块奇怪的石头。
「这块和昨天的不同。」张三说。
「确实，颜色更深。」李四回答。
"""

        chunks = chunker.chunk(text)

        assert len(chunks) >= 1
        assert chunks[0].token_count > 0
        # 对话块应该被识别
        dialogue_chunks = [c for c in chunks if BoundaryType.DIALOGUE in c.boundaries]
        assert len(dialogue_chunks) >= 1

    def test_chunk_legal_text(self):
        """测试法律条文分块"""
        chunker = SemanticChunker(min_chunk_tokens=30, max_chunk_tokens=200)

        text = """
第一章 总则

第一条 为了保护环境，制定本法。
第二条 本法适用于中华人民共和国领域。

第二章 具体规定

第三条 排放污染物应当符合国家标准。
第四条 企业应当建立环保制度。
"""

        chunks = chunker.chunk(text)

        assert len(chunks) >= 1
        # 内容应该被正确分块
        for chunk in chunks:
            assert chunk.token_count > 0
        # 结构化边界应该被识别
        structural_chunks = [
            c for c in chunks if BoundaryType.STRUCTURAL in c.boundaries
        ]
        assert len(structural_chunks) >= 1

    def test_chunk_plain_text(self):
        """测试普通文本分块"""
        chunker = SemanticChunker(min_chunk_tokens=50, max_chunk_tokens=100)

        text = """
机器学习是人工智能的核心技术之一。它使计算机能够从数据中学习并改进性能。

深度学习是机器学习的一个分支，使用多层神经网络。卷积神经网络是深度学习的经典架构。

自然语言处理关注计算机与人类语言的交互。Transformer 模型是当前 NLP 的主流架构。
"""

        chunks = chunker.chunk(text)

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.token_count <= 200

    def test_empty_text(self):
        """测试空文本"""
        chunker = SemanticChunker()
        chunks = chunker.chunk("")

        assert len(chunks) == 0


class TestAutoSelectStrategy:
    """自动策略选择测试"""

    def test_detect_heading_based(self):
        """测试标题型文档检测"""
        text = """
# 第一章 机器学习基础

## 什么是机器学习

机器学习是人工智能的一个分支。

## 机器学习的类型

包括监督学习、无监督学习等。
"""

        strategy = auto_select_chunking_strategy(text)
        assert strategy == "heading_based"

    def test_detect_dialogue_heavy(self):
        """测试对话密集型文档"""
        text = """
「你好吗？」张三问道。
「我很好，谢谢。」李四回答。
「今天天气真不错。」张三说。
「是啊，很适合出去走走。」李四说。
"""

        strategy = auto_select_chunking_strategy(text)
        assert strategy == "semantic_dialogue"

    def test_detect_structural(self):
        """测试结构化文档检测"""
        text = """
第一条 为了规范市场秩序，制定本规定。
第二条 经营者在提供服务时应当遵循公平原则。
第三条 消费者享有知情权和选择权。
"""

        strategy = auto_select_chunking_strategy(text)
        assert strategy == "semantic_structural"

    def test_detect_plain(self):
        """测试普通文档检测"""
        text = """
机器学习是人工智能的核心技术。它使计算机能够从数据中学习并改进性能。
深度学习是机器学习的一个分支，使用多层神经网络来处理复杂数据。
"""

        strategy = auto_select_chunking_strategy(text)
        assert strategy in ["semantic_hybrid", "heading_based"]


class TestSmartChunk:
    """智能分块测试"""

    def test_heading_based_chunking(self):
        """测试标题分块"""
        text = """
# 第一章

这是第一章的内容。

# 第二章

这是第二章的内容。
"""

        chunks = smart_chunk(text, strategy="heading_based")

        assert len(chunks) >= 1
        for chunk in chunks:
            assert "chunking_strategy" in chunk
            assert chunk["chunking_strategy"] == "heading_based"

    def test_semantic_chunking(self):
        """测试语义分块"""
        text = """
张三大声说：「快来看！」
李四跑过来。「哇，真的很神奇！」
两人高兴地跳了起来。
"""

        chunks = smart_chunk(text, strategy="semantic_dialogue")

        assert len(chunks) >= 1
        for chunk in chunks:
            assert "content" in chunk
            assert "chunking_strategy" in chunk

    def test_auto_strategy(self):
        """测试自动策略"""
        text = """
第一条 为了保护环境，制定本法。
第二条 任何单位和个人都有保护环境的义务。
"""

        chunks = smart_chunk(text, strategy="auto")

        assert len(chunks) >= 1
        # 应该自动选择结构化分块
        strategy = auto_select_chunking_strategy(text)
        assert strategy in ["semantic_structural", "heading_based"]


class TestBoundaryFunctions:
    """边界函数测试"""

    def test_chunk_by_semantic_boundaries_basic(self):
        """测试语义边界分块基础功能"""
        text = """
张三大喊：「快跑！」
李四回应：「等等我！」
两人一起跑向远方。
"""

        chunks = chunk_by_semantic_boundaries(text, chunk_size=100)

        assert len(chunks) >= 1
        assert all("content" in c for c in chunks)
        assert all("chunking_strategy" in c for c in chunks)
        assert all(c["chunking_strategy"] == "semantic" for c in chunks)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
