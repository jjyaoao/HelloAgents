"""GraphRAG 数据约定与具有明确限制的操作。"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Protocol, Literal

from pydantic import BaseModel, ConfigDict, Field


class GraphError(RuntimeError):
    pass


class GraphBudgetError(GraphError):
    """操作无法在配置的预算内覆盖全部输入。"""


class GraphIntegrityError(GraphError):
    """抽取证据或生成的引用与输入不一致。"""


class GraphBuildConflict(GraphError):
    """本次构建期间，其他构建器已发布新版本。"""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_default=True)


class EntityMention(StrictModel):
    key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    kind: Literal[
        "person",
        "organization",
        "location",
        "facility",
        "service",
        "event",
        "artifact",
        "other",
    ]
    scope: str = Field(default="", max_length=200)
    aliases: List[str] = Field(default_factory=list, max_length=30)
    description: str = Field(min_length=1, max_length=1500)
    quote: str = Field(min_length=1)


class RelationMention(StrictModel):
    source: str = Field(min_length=1, max_length=80)
    target: str = Field(min_length=1, max_length=80)
    predicate: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1500)
    quote: str = Field(min_length=1)


class Extraction(StrictModel):
    entities: List[EntityMention]
    relations: List[RelationMention]


class SupportedClaim(StrictModel):
    text: str = Field(min_length=1, max_length=4000)
    citations: List[str] = Field(min_length=1, max_length=100)


class CommunityDraft(StrictModel):
    title: str = Field(min_length=1, max_length=300)
    claims: List[SupportedClaim] = Field(max_length=100)


class AnswerDraft(StrictModel):
    claims: List[SupportedClaim] = Field(max_length=100)


SCHEMAS = {
    "extract": Extraction,
    "report": CommunityDraft,
    "map": AnswerDraft,
    "reduce": AnswerDraft,
}


class GraphModel(Protocol):
    """自定义适配器必须标明模型及提示词、配置的版本。"""

    model_id: str

    def generate(
        self,
        stage: str,
        payload: Dict[str, Any],
        *,
        max_input_tokens: int,
        max_output_tokens: int,
    ) -> Dict[str, Any]: ...


@dataclass(frozen=True)
class GraphConfig:
    max_input_tokens: int = 12000
    max_output_tokens: int = 3000
    max_entities_per_chunk: int = 50
    max_relations_per_chunk: int = 100
    max_quote_chars: int = 2000
    max_reports: int = 1000
    max_reduce_rounds: int = 12
    levels: int = 2
    resolution: float = 1.0
    seed: int = 42
    seed_limit: int = 5
    hops: int = 2

    def __post_init__(self):
        for name in (
            "max_input_tokens",
            "max_output_tokens",
            "max_entities_per_chunk",
            "max_relations_per_chunk",
            "max_quote_chars",
            "max_reports",
            "max_reduce_rounds",
            "levels",
            "seed_limit",
        ):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.max_input_tokens < 3000:
            raise ValueError(
                "max_input_tokens must leave at least 3000 tokens for schema and instructions"
            )
        if self.levels > 8 or type(self.hops) is not int or not 0 <= self.hops <= 5:
            raise ValueError("levels must be <=8 and hops an integer in 0..5")
        if self.seed_limit > 100:
            raise ValueError("seed_limit must be <=100")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        import math

        if (
            isinstance(self.resolution, bool)
            or not isinstance(self.resolution, (int, float))
            or not math.isfinite(self.resolution)
            or self.resolution <= 0
        ):
            raise ValueError("resolution must be positive and finite")

    @property
    def payload_tokens(self):
        return self.max_input_tokens - 2200


@dataclass(frozen=True)
class BuildReport:
    generation: str
    revision: int
    chunks: int
    entities: int
    relations: int
    communities: int
    reports: int
    extraction_cache_hits: int
    report_cache_hits: int
    ambiguous_aliases: Dict[str, List[str]]
    reused_generation: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class GraphAnswer:
    answer: str
    status: str
    claims: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    coverage: Dict[str, Any]
    diagnostics: Dict[str, Any]

    def to_dict(self):
        return asdict(self)
