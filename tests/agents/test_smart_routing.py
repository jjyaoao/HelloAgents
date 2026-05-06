"""
智能路由算法测试

测试目标：
1. 数据结构正确性
2. 多因子评分算法正确性
3. 路由策略正确性
4. 容错机制正确性
"""

import unittest
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


# ===== 待测试模块 =====
class TaskType(Enum):
    TEXT_PROCESSING = "text_processing"
    IMAGE_PROCESSING = "image_processing"
    DATA_ANALYSIS = "data_analysis"
    REALTIME = "realtime"
    BATCH = "batch"


class RoutingStrategy(Enum):
    CAPABILITY_MATCH = "capability_match"
    LOAD_BALANCE = "load_balance"
    LATENCY_MIN = "latency_min"
    COST_OPTIMAL = "cost_optimal"
    HYBRID = "hybrid"


@dataclass
class AgentCapability:
    service_type: str
    algorithms: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    accuracy: float = 0.0
    specializations: List[str] = field(default_factory=list)


@dataclass
class AgentMetrics:
    load: float = 0.0
    latency_ms: float = 0.0
    success_rate: float = 1.0
    throughput: float = 0.0
    cost_per_request: float = 0.0


@dataclass
class AgentInfo:
    agent_id: str
    name: str
    endpoint: str
    capabilities: AgentCapability
    metrics: AgentMetrics
    status: str = "online"


@dataclass
class RoutingContext:
    task_type: TaskType
    requirements: Dict[str, Any] = field(default_factory=dict)
    priority: str = "normal"
    budget: Optional[float] = None
    deadline_ms: Optional[int] = None


@dataclass
class RouteScore:
    agent_id: str
    total_score: float = 0.0
    factors: Dict[str, float] = field(default_factory=dict)
    reason: str = ""


# ===== 默认权重 =====
DEFAULT_WEIGHTS = {
    "capability_match": 0.35,
    "load_balance": 0.25,
    "latency": 0.20,
    "success_rate": 0.10,
    "cost": 0.10,
}


# ===== 智能路由实现 =====
class SmartRouter:
    """智能路由引擎"""

    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.HYBRID):
        self.strategy = strategy
        self.agents: Dict[str, AgentInfo] = {}
        self.weights = DEFAULT_WEIGHTS.copy()

    def register_agent(self, agent: AgentInfo):
        """注册智能体"""
        self.agents[agent.agent_id] = agent

    def _adjust_weights(self, context: RoutingContext) -> Dict[str, float]:
        """根据策略调整权重"""
        weights = DEFAULT_WEIGHTS.copy()

        if self.strategy == RoutingStrategy.CAPABILITY_MATCH:
            weights = {
                "capability_match": 0.6,
                "load_balance": 0.2,
                "latency": 0.1,
                "success_rate": 0.1,
                "cost": 0.0,
            }
        elif self.strategy == RoutingStrategy.LOAD_BALANCE:
            weights = {
                "capability_match": 0.2,
                "load_balance": 0.5,
                "latency": 0.15,
                "success_rate": 0.15,
                "cost": 0.0,
            }
        elif self.strategy == RoutingStrategy.LATENCY_MIN:
            weights = {
                "capability_match": 0.2,
                "load_balance": 0.1,
                "latency": 0.6,
                "success_rate": 0.1,
                "cost": 0.0,
            }
        elif self.strategy == RoutingStrategy.COST_OPTIMAL:
            weights = {
                "capability_match": 0.25,
                "load_balance": 0.15,
                "latency": 0.15,
                "success_rate": 0.15,
                "cost": 0.3,
            }

        return weights

    def _filter_candidates(self, context: RoutingContext) -> List[AgentInfo]:
        """过滤候选智能体"""
        candidates = []

        for agent in self.agents.values():
            if agent.status != "online":
                continue
            if not self._has_required_capability(agent, context):
                continue
            if context.budget and agent.metrics.cost_per_request > context.budget:
                continue
            candidates.append(agent)

        return candidates

    def _has_required_capability(
        self, agent: AgentInfo, context: RoutingContext
    ) -> bool:
        """检查是否具备必需能力"""
        if context.task_type.value == agent.capabilities.service_type:
            return True
        return False

    def _calculate_capability_score(
        self, agent: AgentInfo, context: RoutingContext
    ) -> float:
        """计算能力匹配分数"""
        score = 0.0
        caps = agent.capabilities

        if context.task_type.value == caps.service_type:
            score += 0.4

        required = context.requirements.get("algorithms", [])
        if required:
            matched = len(set(required) & set(caps.algorithms))
            score += matched / len(required) * 0.3

        languages = context.requirements.get("languages", [])
        if languages:
            matched = len(set(languages) & set(caps.languages))
            score += matched / len(languages) * 0.2

        specs = context.requirements.get("specializations", [])
        if specs:
            matched = len(set(specs) & set(caps.specializations))
            score += matched / len(specs) * 0.1

        return min(score, 1.0)

    def _calculate_load_score(self, agent: AgentInfo) -> float:
        """计算负载均衡分数"""
        load = agent.metrics.load
        if 0 <= load <= 1:
            return 1.0 - load
        return 0.0

    def _calculate_latency_score(self, agent: AgentInfo) -> float:
        """计算延迟分数"""
        latency = agent.metrics.latency_ms

        if latency <= 0:
            return 1.0
        elif latency < 100:
            return 1.0 - (latency / 100) * 0.2
        elif latency < 500:
            return 0.8 - ((latency - 100) / 400) * 0.3
        else:
            return max(0.0, 0.5 - ((latency - 500) / 1000) * 0.5)

    def _calculate_success_rate_score(self, agent: AgentInfo) -> float:
        """计算成功率分数"""
        return agent.metrics.success_rate

    def _calculate_cost_score(self, agent: AgentInfo, context: RoutingContext) -> float:
        """计算成本分数"""
        budget = context.budget
        cost = agent.metrics.cost_per_request

        if budget is None:
            return 1.0
        if cost <= budget:
            return (budget - cost) / budget
        return 0.0

    def _calculate_score(self, agent: AgentInfo, context: RoutingContext) -> RouteScore:
        """计算综合评分"""
        weights = self._adjust_weights(context)
        factors = {}

        factors["capability_match"] = self._calculate_capability_score(agent, context)
        factors["load_balance"] = self._calculate_load_score(agent)
        factors["latency"] = self._calculate_latency_score(agent)
        factors["success_rate"] = self._calculate_success_rate_score(agent)
        factors["cost"] = self._calculate_cost_score(agent, context)

        total = sum(factors[key] * weights.get(key, 0) for key in factors)

        weight_sum = sum(weights.values())
        if weight_sum > 0:
            total /= weight_sum

        reason = f"能力:{factors['capability_match']:.2f}, 负载:{factors['load_balance']:.2f}, 延迟:{factors['latency']:.2f}"

        return RouteScore(
            agent_id=agent.agent_id, total_score=total, factors=factors, reason=reason
        )

    def route(self, context: RoutingContext) -> Optional[RouteScore]:
        """路由方法"""
        candidates = self._filter_candidates(context)

        if not candidates:
            return None

        scores = [self._calculate_score(agent, context) for agent in candidates]
        scores.sort(key=lambda x: x.total_score, reverse=True)

        return scores[0]


# ===== 测试用例 =====
class TestSmartRouter(unittest.TestCase):
    """智能路由测试"""

    def setUp(self):
        """设置测试环境"""
        self.router = SmartRouter()

        # 创建测试智能体
        self.agent1 = AgentInfo(
            agent_id="agent_1",
            name="文本处理专家A",
            endpoint="http://localhost:8001",
            capabilities=AgentCapability(
                service_type="text_processing",
                algorithms=["sentiment", "ner"],
                languages=["en", "zh"],
                accuracy=0.9,
                specializations=["finance"],
            ),
            metrics=AgentMetrics(
                load=0.3, latency_ms=50, success_rate=0.95, cost_per_request=0.01
            ),
        )

        self.agent2 = AgentInfo(
            agent_id="agent_2",
            name="文本处理专家B",
            endpoint="http://localhost:8002",
            capabilities=AgentCapability(
                service_type="text_processing",
                algorithms=["sentiment"],
                languages=["en"],
                accuracy=0.85,
                specializations=["healthcare"],
            ),
            metrics=AgentMetrics(
                load=0.7, latency_ms=200, success_rate=0.90, cost_per_request=0.02
            ),
        )

        self.agent3 = AgentInfo(
            agent_id="agent_3",
            name="图像处理专家",
            endpoint="http://localhost:8003",
            capabilities=AgentCapability(
                service_type="image_processing",
                algorithms=["detection"],
                languages=["en"],
                accuracy=0.88,
            ),
            metrics=AgentMetrics(
                load=0.5, latency_ms=150, success_rate=0.92, cost_per_request=0.015
            ),
        )

        # 注册智能体
        self.router.register_agent(self.agent1)
        self.router.register_agent(self.agent2)
        self.router.register_agent(self.agent3)

    def test_register_agent(self):
        """测试智能体注册"""
        self.assertEqual(len(self.router.agents), 3)
        self.assertIn("agent_1", self.router.agents)
        self.assertIn("agent_2", self.router.agents)
        self.assertIn("agent_3", self.router.agents)

    def test_capability_filter(self):
        """测试能力过滤"""
        context = RoutingContext(task_type=TaskType.TEXT_PROCESSING)
        candidates = self.router._filter_candidates(context)

        self.assertEqual(len(candidates), 2)
        agent_ids = [a.agent_id for a in candidates]
        self.assertIn("agent_1", agent_ids)
        self.assertIn("agent_2", agent_ids)
        self.assertNotIn("agent_3", agent_ids)

    def test_capability_score_perfect_match(self):
        """测试能力匹配-完美匹配"""
        context = RoutingContext(
            task_type=TaskType.TEXT_PROCESSING,
            requirements={
                "algorithms": ["sentiment", "ner"],
                "languages": ["en", "zh"],
                "specializations": ["finance"],  # 添加specializations匹配
            },
        )

        score = self.router._calculate_capability_score(self.agent1, context)

        self.assertAlmostEqual(score, 1.0, places=2)

    def test_capability_score_partial_match(self):
        """测试能力匹配-部分匹配"""
        context = RoutingContext(
            task_type=TaskType.TEXT_PROCESSING,
            requirements={
                "algorithms": ["sentiment", "ner", "translation"],
                "languages": ["en", "zh", "ja"],
            },
        )

        score = self.router._calculate_capability_score(self.agent1, context)

        self.assertGreater(score, 0.5)
        self.assertLess(score, 1.0)

    def test_capability_score_no_match(self):
        """测试能力匹配-不匹配"""
        context = RoutingContext(
            task_type=TaskType.IMAGE_PROCESSING,  # 不同task_type
            requirements={"algorithms": ["translation"], "languages": ["ja"]},
        )

        score = self.router._calculate_capability_score(self.agent1, context)

        self.assertLess(score, 0.5)

    def test_load_score(self):
        """测试负载评分"""
        self.agent1.metrics.load = 0.0
        self.agent2.metrics.load = 1.0

        score1 = self.router._calculate_load_score(self.agent1)
        score2 = self.router._calculate_load_score(self.agent2)

        self.assertEqual(score1, 1.0)
        self.assertEqual(score2, 0.0)

    def test_latency_score(self):
        """测试延迟评分"""
        self.agent1.metrics.latency_ms = 50
        self.agent2.metrics.latency_ms = 600

        score1 = self.router._calculate_latency_score(self.agent1)
        score2 = self.router._calculate_latency_score(self.agent2)

        self.assertGreater(score1, 0.8)
        self.assertLess(score2, 0.5)

    def test_success_rate_score(self):
        """测试成功率评分"""
        self.agent1.metrics.success_rate = 0.95

        score = self.router._calculate_success_rate_score(self.agent1)

        self.assertEqual(score, 0.95)

    def test_cost_score_with_budget(self):
        """测试成本评分-有预算"""
        context = RoutingContext(task_type=TaskType.TEXT_PROCESSING, budget=0.02)

        self.agent1.metrics.cost_per_request = 0.01
        self.agent2.metrics.cost_per_request = 0.03

        score1 = self.router._calculate_cost_score(self.agent1, context)
        score2 = self.router._calculate_cost_score(self.agent2, context)

        self.assertEqual(score1, 0.5)
        self.assertEqual(score2, 0.0)

    def test_cost_score_no_budget(self):
        """测试成本评分-无预算"""
        context = RoutingContext(task_type=TaskType.TEXT_PROCESSING, budget=None)

        score = self.router._calculate_cost_score(self.agent1, context)

        self.assertEqual(score, 1.0)

    def test_route_basic(self):
        """测试基础路由"""
        context = RoutingContext(task_type=TaskType.TEXT_PROCESSING)

        result = self.router.route(context)

        self.assertIsNotNone(result)
        self.assertIn(result.agent_id, ["agent_1", "agent_2"])

    def test_route_with_requirements(self):
        """测试带需求的路由"""
        context = RoutingContext(
            task_type=TaskType.TEXT_PROCESSING,
            requirements={"algorithms": ["sentiment", "ner"]},
        )

        result = self.router.route(context)

        self.assertIsNotNone(result)
        self.assertEqual(result.agent_id, "agent_1")

    def test_route_with_budget(self):
        """测试带预算的路由"""
        context = RoutingContext(task_type=TaskType.TEXT_PROCESSING, budget=0.015)

        result = self.router.route(context)

        self.assertIsNotNone(result)
        self.assertEqual(result.agent_id, "agent_1")

    def test_strategy_capability_match(self):
        """测试能力匹配策略"""
        router = SmartRouter(strategy=RoutingStrategy.CAPABILITY_MATCH)
        router.register_agent(self.agent1)
        router.register_agent(self.agent2)

        context = RoutingContext(task_type=TaskType.TEXT_PROCESSING)

        result = router.route(context)

        self.assertIsNotNone(result)
        self.assertEqual(result.agent_id, "agent_1")

    def test_strategy_load_balance(self):
        """测试负载均衡策略"""
        router = SmartRouter(strategy=RoutingStrategy.LOAD_BALANCE)
        router.register_agent(self.agent1)
        router.register_agent(self.agent2)

        context = RoutingContext(task_type=TaskType.TEXT_PROCESSING)

        result = router.route(context)

        self.assertIsNotNone(result)
        self.assertEqual(result.agent_id, "agent_1")

    def test_strategy_latency_min(self):
        """测试延迟最小策略"""
        router = SmartRouter(strategy=RoutingStrategy.LATENCY_MIN)
        router.register_agent(self.agent1)
        router.register_agent(self.agent2)

        context = RoutingContext(task_type=TaskType.TEXT_PROCESSING)

        result = router.route(context)

        self.assertIsNotNone(result)
        self.assertEqual(result.agent_id, "agent_1")

    def test_strategy_cost_optimal(self):
        """测试成本最优策略"""
        router = SmartRouter(strategy=RoutingStrategy.COST_OPTIMAL)
        router.register_agent(self.agent1)
        router.register_agent(self.agent2)

        context = RoutingContext(task_type=TaskType.TEXT_PROCESSING)

        result = router.route(context)

        self.assertIsNotNone(result)
        self.assertEqual(result.agent_id, "agent_1")

    def test_offline_agent_filter(self):
        """测试离线智能体过滤"""
        self.agent1.status = "offline"

        context = RoutingContext(task_type=TaskType.TEXT_PROCESSING)

        candidates = self.router._filter_candidates(context)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].agent_id, "agent_2")

    def test_no_candidates(self):
        """测试无候选智能体"""
        context = RoutingContext(task_type=TaskType.REALTIME)

        result = self.router.route(context)

        self.assertIsNone(result)

    def test_weight_adjustment(self):
        """测试权重调整"""
        router1 = SmartRouter(strategy=RoutingStrategy.CAPABILITY_MATCH)
        router2 = SmartRouter(strategy=RoutingStrategy.LOAD_BALANCE)

        context = RoutingContext(task_type=TaskType.TEXT_PROCESSING)

        weights1 = router1._adjust_weights(context)
        weights2 = router2._adjust_weights(context)

        self.assertGreater(weights1["capability_match"], weights2["capability_match"])
        self.assertGreater(weights2["load_balance"], weights1["load_balance"])


class TestEdgeCases(unittest.TestCase):
    """边界情况测试"""

    def test_zero_load(self):
        """测试零负载"""
        router = SmartRouter()
        agent = AgentInfo(
            agent_id="test",
            name="Test",
            endpoint="http://test",
            capabilities=AgentCapability(service_type="text"),
            metrics=AgentMetrics(load=0.0),
        )

        score = router._calculate_load_score(agent)

        self.assertEqual(score, 1.0)

    def test_negative_load(self):
        """测试负负载"""
        router = SmartRouter()
        agent = AgentInfo(
            agent_id="test",
            name="Test",
            endpoint="http://test",
            capabilities=AgentCapability(service_type="text"),
            metrics=AgentMetrics(load=-0.1),
        )

        score = router._calculate_load_score(agent)

        self.assertEqual(score, 0.0)

    def test_zero_latency(self):
        """测试零延迟"""
        router = SmartRouter()
        agent = AgentInfo(
            agent_id="test",
            name="Test",
            endpoint="http://test",
            capabilities=AgentCapability(service_type="text"),
            metrics=AgentMetrics(latency_ms=0),
        )

        score = router._calculate_latency_score(agent)

        self.assertEqual(score, 1.0)

    def test_very_high_latency(self):
        """测试极高延迟"""
        router = SmartRouter()
        agent = AgentInfo(
            agent_id="test",
            name="Test",
            endpoint="http://test",
            capabilities=AgentCapability(service_type="text"),
            metrics=AgentMetrics(latency_ms=10000),
        )

        score = router._calculate_latency_score(agent)

        self.assertEqual(score, 0.0)


if __name__ == "__main__":
    unittest.main()
