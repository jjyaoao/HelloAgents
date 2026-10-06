"""持久化后台任务的数据与行为约定，不依赖模型服务。"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


class LeaseLost(RuntimeError):
    """当前执行已失去任务持有权，不得发布结果。"""


class JobConflict(ValueError):
    """同一幂等键被用于不同操作。"""


@dataclass(frozen=True)
class Job:
    job_id: str
    namespace: str
    task: str
    payload: Dict[str, Any]
    status: str
    attempts: int
    max_attempts: int
    available_at: float
    lease_until: Optional[float]
    worker_id: Optional[str]
    lease_token: Optional[str]
    result: Any
    error: Optional[str]
    idempotency_key: Optional[str]
    created_at: float
    updated_at: float
    progress: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JobLease:
    job: Job
    token: str
