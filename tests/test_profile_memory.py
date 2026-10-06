from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import Field, ValidationError

from hello_agents.memory import (
    ProfileModel,
    ProfileStore,
    ProfileConflict,
    ProfileContextProvider,
)


class TravelProfile(ProfileModel):
    walking_km: int = Field(ge=0, le=50)
    interests: list[str] = Field(default_factory=list)


def store(tmp_path, **kwargs):
    return ProfileStore(
        str(tmp_path / "memory.sqlite"),
        schema=TravelProfile,
        user_id=kwargs.pop("user_id", "alice"),
        namespace=kwargs.pop("namespace", "travel"),
        **kwargs,
    )


def test_profile_corrections_persistence_scope_and_context(tmp_path):
    s = store(tmp_path)
    first = s.put(
        {"walking_km": 8, "interests": ["history"]},
        source="message:1",
        expected_revision=0,
    )
    second = s.patch(
        {"walking_km": 5}, source="message:2", expected_revision=first.revision
    )
    assert second.sources == {"walking_km": "message:2", "interests": "message:1"}
    reopened = store(tmp_path)
    assert reopened.get().data == {"walking_km": 5, "interests": ["history"]}
    assert store(tmp_path, user_id="bob").get() is None
    assert store(tmp_path, namespace="work").get() is None
    provider = ProfileContextProvider(reopened)
    assert "5" in provider.get_context("")[0].content
    assert reopened.history()[1].data["walking_km"] == 8
    forgotten = reopened.forget(source="message:3", expected_revision=2)
    assert forgotten.status == "forgotten" and provider.get_context("") == []
    assert reopened.get(include_inactive=True).revision == 3
    with pytest.raises(ProfileConflict):
        reopened.put({"walking_km": 10}, source="stale", expected_revision=0)
    with pytest.raises(ValueError):
        forgotten.to_context_packet()


@pytest.mark.parametrize(
    "data",
    [
        {"walking_km": "8"},
        {"walking_km": True},
        {"walking_km": -1},
        {"walking_km": 8, "unknown": 1},
    ],
)
def test_strict_schema_does_not_commit_invalid_writes(tmp_path, data):
    s = store(tmp_path)
    with pytest.raises(ValidationError):
        s.put(data, source="message", expected_revision=0)
    assert s.get() is None


def test_concurrent_update_has_exactly_one_winner(tmp_path):
    s = store(tmp_path)
    s.put({"walking_km": 8}, source="1", expected_revision=0)

    def write(n):
        try:
            store(tmp_path).patch({"walking_km": n}, source=str(n), expected_revision=1)
            return True
        except ProfileConflict:
            return False

    with ThreadPoolExecutor(2) as executor:
        assert sum(executor.map(write, [3, 5])) == 1
    assert len(s.history()) == 2


def test_schema_change_and_budget_are_explicit(tmp_path):
    s = store(tmp_path)
    s.put({"walking_km": 8}, source="1", expected_revision=0)

    class Changed(ProfileModel):
        walking_km: str

    other = ProfileStore(
        str(s.path), user_id="alice", namespace="travel", schema=Changed
    )
    with pytest.raises(ValueError, match="schema changed"):
        other.get()
    with pytest.raises(ValueError, match="max_bytes"):
        store(tmp_path, max_bytes=10).patch(
            {"interests": ["x" * 100]}, source="2", expected_revision=1
        )
    assert s.get().revision == 1


def test_patch_restores_strict_json_types(tmp_path):
    from datetime import date
    from enum import Enum

    class Language(str, Enum):
        ZH = "zh"

    class TypedProfile(ProfileModel):
        birthday: date
        coordinates: tuple[int, int]
        language: Language
        city: str

    s = ProfileStore(
        str(tmp_path / "typed.sqlite"),
        user_id="a",
        namespace="typed",
        schema=TypedProfile,
    )
    s.put(
        {
            "birthday": date(2000, 1, 1),
            "coordinates": (1, 2),
            "language": Language.ZH,
            "city": "A",
        },
        source="1",
        expected_revision=0,
    )
    updated = s.patch({"city": "B"}, source="2", expected_revision=1)
    assert updated.data == {
        "birthday": "2000-01-01",
        "coordinates": [1, 2],
        "language": "zh",
        "city": "B",
    }


def test_invalid_schema_default_is_not_persisted(tmp_path):
    class BrokenDefaults(ProfileModel):
        steps: int = "not an integer"

    s = ProfileStore(
        str(tmp_path / "defaults.sqlite"),
        user_id="a",
        namespace="typed",
        schema=BrokenDefaults,
    )
    with pytest.raises(ValidationError):
        s.put({}, source="1", expected_revision=0)
    assert s.get() is None
