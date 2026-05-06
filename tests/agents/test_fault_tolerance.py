"""
智能体网络容错机制测试

测试目标：
1. 故障检测正确性
2. 故障切换正确性
3. 状态恢复正确性
"""

import unittest
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from enum import Enum
import time


# ===== 待测试模块 =====
class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"


class FaultType(Enum):
    NONE = "none"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "conn"
    HIGH_FAILURE_RATE = "high_fail"
    RESOURCE_EXHAUSTED = "resources"
    UNKNOWN = "unknown"


@dataclass
class AgentHealth:
    agent_id: str
    status: HealthStatus = HealthStatus.HEALTHY
    fault_type: FaultType = FaultType.NONE
    failure_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    last_heartbeat: float = 0.0
    last_failure_time: float = 0.0


@dataclass
class BackupConfig:
    primary_id: str
    backup_ids: List[str]
    sync_enabled: bool = True
    sync_interval: int = 5
    failover_threshold: int = 3


# ===== 故障检测器 =====
class FaultDetector:
    def __init__(
        self,
        failure_threshold: int = 3,
        timeout_threshold: float = 5.0,
        heartbeat_interval: float = 10.0,
    ):
        self.failure_threshold = failure_threshold
        self.timeout_threshold = timeout_threshold
        self.heartbeat_interval = heartbeat_interval

    def check_health(self, health: AgentHealth, current_time: float) -> HealthStatus:
        if health.consecutive_failures >= self.failure_threshold:
            return HealthStatus.FAILED

        if current_time - health.last_heartbeat > self.heartbeat_interval:
            return HealthStatus.UNHEALTHY

        total = health.failure_count + health.success_count
        if total > 0:
            failure_rate = health.failure_count / total
            if failure_rate > 0.5:
                return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY


# ===== 故障切换管理器 =====
class FailoverManager:
    def __init__(self, detector: FaultDetector):
        self.detector = detector
        self.backups: Dict[str, BackupConfig] = {}
        self.health: Dict[str, AgentHealth] = {}

    def register_primary_with_backup(self, primary_id: str, backup_ids: List[str]):
        self.backups[primary_id] = BackupConfig(
            primary_id=primary_id, backup_ids=backup_ids
        )
        self.health[primary_id] = AgentHealth(agent_id=primary_id)

    def record_request(self, agent_id: str, success: bool, current_time: float):
        if agent_id not in self.health:
            self.health[agent_id] = AgentHealth(agent_id=agent_id)

        health = self.health[agent_id]
        health.last_heartbeat = current_time

        if success:
            health.success_count += 1
            health.consecutive_failures = 0
        else:
            health.failure_count += 1
            health.consecutive_failures += 1
            health.last_failure_time = current_time

    def get_failover_target(
        self, primary_id: str, current_time: float
    ) -> Optional[str]:
        if primary_id not in self.backups:
            return None

        health = self.health.get(primary_id)
        if not health:
            return None

        status = self.detector.check_health(health, current_time)
        if status == HealthStatus.HEALTHY:
            return None

        config = self.backups[primary_id]
        for backup_id in config.backup_ids:
            backup_health = self.health.get(backup_id)
            if not backup_health:
                return backup_id

            status = self.detector.check_health(backup_health, current_time)
            if status == HealthStatus.HEALTHY:
                return backup_id

        return None


# ===== 状态恢复管理器 =====
class RecoveryManager:
    def __init__(self):
        self.state_snapshots: Dict[str, Any] = {}
        self.checkpoints: Dict[str, List[float]] = {}

    def save_checkpoint(self, agent_id: str, state: Any):
        self.state_snapshots[agent_id] = state
        if agent_id not in self.checkpoints:
            self.checkpoints[agent_id] = []
        self.checkpoints[agent_id].append(time.time())

    def get_latest_checkpoint(self, agent_id: str) -> Optional[Any]:
        return self.state_snapshots.get(agent_id)

    def recover_state(self, from_agent_id: str, to_agent_id: str) -> bool:
        checkpoint = self.get_latest_checkpoint(from_agent_id)
        if not checkpoint:
            return False
        self.save_checkpoint(to_agent_id, checkpoint)
        return True


# ===== 测试用例 =====
class TestFaultDetector(unittest.TestCase):
    """故障检测器测试"""

    def setUp(self):
        self.detector = FaultDetector(failure_threshold=3)
        self.current_time = time.time()
        # 初始化健康状态，避免心跳超时
        self.health = AgentHealth(agent_id="test")
        self.health.last_heartbeat = self.current_time

    def test_detect_consecutive_failures(self):
        """测试连续失败检测"""
        health = AgentHealth(agent_id="test")
        health.consecutive_failures = 3
        health.last_heartbeat = self.current_time

        status = self.detector.check_health(health, self.current_time)

        self.assertEqual(status, HealthStatus.FAILED)

    def test_detect_heartbeat_timeout(self):
        """测试心跳超时检测"""
        health = AgentHealth(agent_id="test")
        health.last_heartbeat = self.current_time - 20

        status = self.detector.check_health(health, self.current_time)

        self.assertEqual(status, HealthStatus.UNHEALTHY)

    def test_detect_high_failure_rate(self):
        """测试高失败率检测"""
        health = AgentHealth(agent_id="test")
        health.failure_count = 6
        health.success_count = 4
        health.last_heartbeat = self.current_time

        status = self.detector.check_health(health, self.current_time)

        self.assertEqual(status, HealthStatus.DEGRADED)

    def test_healthy_status(self):
        """测试健康状态"""
        health = AgentHealth(agent_id="test")
        health.success_count = 10
        health.last_heartbeat = self.current_time

        status = self.detector.check_health(health, self.current_time)

        self.assertEqual(status, HealthStatus.HEALTHY)

    def test_boundary_consecutive_failures_2(self):
        """测试边界：连续失败2次"""
        health = AgentHealth(agent_id="test")
        health.consecutive_failures = 2
        health.last_heartbeat = self.current_time

        status = self.detector.check_health(health, self.current_time)

        self.assertEqual(status, HealthStatus.HEALTHY)

    def test_boundary_consecutive_failures_3(self):
        """测试边界：连续失败3次"""
        health = AgentHealth(agent_id="test")
        health.consecutive_failures = 3
        health.last_heartbeat = self.current_time

        status = self.detector.check_health(health, self.current_time)

        self.assertEqual(status, HealthStatus.FAILED)


class TestFailoverManager(unittest.TestCase):
    """故障切换管理器测试"""

    def setUp(self):
        self.detector = FaultDetector(failure_threshold=3)
        self.failover = FailoverManager(self.detector)
        self.current_time = time.time()

    def test_failover_to_backup(self):
        """测试故障切换到备份"""
        self.failover.register_primary_with_backup(
            "traffic_manager", ["traffic_backup_1", "traffic_backup_2"]
        )

        health = self.failover.health["traffic_manager"]
        health.consecutive_failures = 3

        target = self.failover.get_failover_target("traffic_manager", self.current_time)

        self.assertEqual(target, "traffic_backup_1")

    def test_failover_no_backup(self):
        """测试无备份情况"""
        self.failover.register_primary_with_backup("traffic_manager", [])

        health = self.failover.health["traffic_manager"]
        health.consecutive_failures = 3

        target = self.failover.get_failover_target("traffic_manager", self.current_time)

        self.assertIsNone(target)

    def test_failover_all_failed(self):
        """测试主备都故障"""
        self.failover.register_primary_with_backup(
            "traffic_manager", ["traffic_backup_1"]
        )

        self.failover.health["traffic_manager"].consecutive_failures = 3
        self.failover.health["traffic_backup_1"] = AgentHealth("traffic_backup_1")
        self.failover.health["traffic_backup_1"].consecutive_failures = 3

        target = self.failover.get_failover_target("traffic_manager", self.current_time)

        self.assertIsNone(target)

    def test_failover_healthy_primary(self):
        """测试主智能体健康"""
        self.failover.register_primary_with_backup(
            "traffic_manager", ["traffic_backup_1"]
        )

        # 设置健康状态，避免心跳超时
        self.failover.health["traffic_manager"].success_count = 10
        self.failover.health["traffic_manager"].last_heartbeat = self.current_time

        target = self.failover.get_failover_target("traffic_manager", self.current_time)

        self.assertIsNone(target)

    def test_failover_unhealthy_primary(self):
        """测试主智能体降级"""
        self.failover.register_primary_with_backup(
            "traffic_manager", ["traffic_backup_1"]
        )

        health = self.failover.health["traffic_manager"]
        health.failure_count = 6
        health.success_count = 4

        target = self.failover.get_failover_target("traffic_manager", self.current_time)

        self.assertEqual(target, "traffic_backup_1")

    def test_record_request_success(self):
        """测试记录成功请求"""
        self.failover.register_primary_with_backup("traffic_manager", ["backup"])

        self.failover.record_request("traffic_manager", True, self.current_time)

        health = self.failover.health["traffic_manager"]
        self.assertEqual(health.success_count, 1)
        self.assertEqual(health.consecutive_failures, 0)

    def test_record_request_failure(self):
        """测试记录失败请求"""
        self.failover.register_primary_with_backup("traffic_manager", ["backup"])

        self.failover.record_request("traffic_manager", False, self.current_time)

        health = self.failover.health["traffic_manager"]
        self.assertEqual(health.failure_count, 1)
        self.assertEqual(health.consecutive_failures, 1)


class TestRecoveryManager(unittest.TestCase):
    """状态恢复管理器测试"""

    def setUp(self):
        self.recovery = RecoveryManager()

    def test_save_checkpoint(self):
        """测试保存检查点"""
        state = {"traffic_light": "green", "speed_limit": 60}

        self.recovery.save_checkpoint("traffic_manager", state)

        checkpoint = self.recovery.get_latest_checkpoint("traffic_manager")

        self.assertEqual(checkpoint, state)

    def test_recover_state(self):
        """测试恢复状态"""
        original_state = {"traffic_light": "green"}
        self.recovery.save_checkpoint("traffic_manager", original_state)

        result = self.recovery.recover_state("traffic_manager", "traffic_backup_1")

        self.assertTrue(result)
        self.assertEqual(
            self.recovery.get_latest_checkpoint("traffic_backup_1"), original_state
        )

    def test_recover_no_checkpoint(self):
        """测试无检查点恢复"""
        result = self.recovery.recover_state("unknown_agent", "backup")

        self.assertFalse(result)

    def test_multiple_checkpoints(self):
        """测试多次检查点"""
        self.recovery.save_checkpoint("agent1", "state1")
        self.recovery.save_checkpoint("agent1", "state2")
        self.recovery.save_checkpoint("agent1", "state3")

        checkpoint = self.recovery.get_latest_checkpoint("agent1")

        self.assertEqual(checkpoint, "state3")


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_full_fault_tolerance_flow(self):
        """测试完整容错流程"""
        detector = FaultDetector(failure_threshold=3)
        failover = FailoverManager(detector)
        recovery = RecoveryManager()
        current_time = time.time()

        failover.register_primary_with_backup("traffic_manager", ["traffic_backup_1"])

        recovery.save_checkpoint("traffic_manager", {"mode": "auto"})

        for i in range(3):
            failover.record_request("traffic_manager", False, current_time)

        fail_target = failover.get_failover_target("traffic_manager", current_time)

        self.assertEqual(fail_target, "traffic_backup_1")

        recovery.recover_state("traffic_manager", fail_target)

        restored_state = recovery.get_latest_checkpoint(fail_target)

        self.assertEqual(restored_state, {"mode": "auto"})


if __name__ == "__main__":
    unittest.main()
