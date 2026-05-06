"""
智能检索路由测试

测试目标：
1. IntentClassifier 意图分类准确性
2. ContextAnalyzer 上下文依赖度计算正确性
3. RetrievalRouter 路由决策与矩阵匹配
4. 集成场景验证
"""

import unittest
from dataclasses import dataclass
from typing import List

from hello_agents.context.retrieval_router import (
    RetrievalRouter,
    IntentClassifier,
    ContextAnalyzer,
    IntentType,
    RoutingStrategy,
)


@dataclass
class MockMessage:
    """模拟 Message 类"""

    content: str
    role: str = "user"


class TestIntentClassifier(unittest.TestCase):
    """意图分类器测试"""

    def setUp(self):
        self.classifier = IntentClassifier()

    def test_factual_intent(self):
        queries = [
            "Python 闭包是什么？",
            "什么是机器学习？",
            "Transformer 的原理是什么？",
            "如何实现快速排序？",
        ]
        for q in queries:
            self.assertEqual(
                self.classifier.classify(q), IntentType.FACTUAL, f"Query: {q}"
            )

    def test_personal_intent(self):
        queries = [
            "我记得上次说过...",
            "我的那个项目需求...",
            "我之前提过的那个问题",
            "我们昨天讨论的内容",
        ]
        for q in queries:
            self.assertEqual(
                self.classifier.classify(q), IntentType.PERSONAL, f"Query: {q}"
            )

    def test_mixed_intent(self):
        queries = [
            "你好",
            "帮我写个总结",
            "Python 和 Java 的区别",
            "随便聊聊",
        ]
        for q in queries:
            self.assertEqual(
                self.classifier.classify(q), IntentType.MIXED, f"Query: {q}"
            )

    def test_empty_query(self):
        self.assertEqual(self.classifier.classify(""), IntentType.MIXED)
        self.assertEqual(self.classifier.classify("   "), IntentType.MIXED)


class TestContextAnalyzer(unittest.TestCase):
    """上下文依赖度分析器测试"""

    def setUp(self):
        self.analyzer = ContextAnalyzer()

    def test_low_dependency(self):
        history = []
        dependency = self.analyzer.analyze("Python 是什么？", history)
        self.assertLess(dependency, 0.3)

    def test_high_dependency_keywords(self):
        history = [MockMessage(content="昨天我们讨论了机器学习模型")]
        dependency = self.analyzer.analyze(
            "接着那个机器学习模型我们要继续训练它", history
        )
        self.assertGreater(dependency, 0.7)

    def test_medium_dependency_overlap(self):
        history = [MockMessage(content="深度学习中的卷积神经网络应用广泛")]
        dependency = self.analyzer.analyze("接着神经网络如何优化", history)
        # 有一定重叠词和关键词依赖
        self.assertGreaterEqual(dependency, 0.3)
        self.assertLessEqual(dependency, 0.7)

    def test_no_history(self):
        dependency = self.analyzer.analyze("解释一下量子力学", [])
        self.assertEqual(dependency, 0.0)

    def test_empty_query(self):
        dependency = self.analyzer.analyze("", [MockMessage("Hello")])
        self.assertEqual(dependency, 0.0)


class TestRetrievalRouter(unittest.TestCase):
    """智能检索路由器测试"""

    def setUp(self):
        self.router = RetrievalRouter()

    def assert_routing(
        self,
        query: str,
        history: List,
        expected_strategy: RoutingStrategy,
        expected_rag: float,
        expected_mem: float,
    ):
        result = self.router.route(query, history)
        self.assertEqual(
            result.strategy, expected_strategy, f"Strategy mismatch for: {query}"
        )
        self.assertAlmostEqual(result.rag_weight, expected_rag, places=1)
        self.assertAlmostEqual(result.memory_weight, expected_mem, places=1)

    # --- Fact Cases ---
    def test_fact_low_dependency(self):
        # 纯事实，无历史
        self.assert_routing(
            "Python 装饰器是什么？", [], RoutingStrategy.RAG_ONLY, 1.0, 0.0
        )

    def test_fact_medium_dependency(self):
        history = [MockMessage(content="Python 高级特性中生成器非常重要")]
        self.assert_routing(
            "接着如何实现生成器？", history, RoutingStrategy.DUAL_RETRIEVAL, 0.7, 0.3
        )

    # --- Personal Cases ---
    def test_personal_low_dependency(self):
        # 个人问题，但无重叠词
        self.assert_routing(
            "我记得那个需求很重要", [], RoutingStrategy.DUAL_RETRIEVAL, 0.3, 0.7
        )

    def test_personal_high_dependency(self):
        history = [MockMessage(content="关于项目进度的报告已经发你了")]
        self.assert_routing(
            "接着那个关于我的项目进度的报告我还要继续改",
            history,
            RoutingStrategy.MEMORY_ONLY,
            0.0,
            1.0,
        )

    # --- Mixed Cases ---
    def test_mixed_medium_dependency(self):
        history = [MockMessage(content="工业界最近开始大规模应用 AI 模型")]
        self.assert_routing(
            "接着这些模型在工业界应用广泛吗",
            history,
            RoutingStrategy.DUAL_RETRIEVAL,
            0.5,
            0.5,
        )

    # --- Edge Cases ---
    def test_default_routing(self):
        # 无法明确分类时，应走 Mixed/Medium 逻辑
        result = self.router.route("随便聊聊")
        self.assertEqual(result.strategy, RoutingStrategy.DUAL_RETRIEVAL)


if __name__ == "__main__":
    unittest.main()
