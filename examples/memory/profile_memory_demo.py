"""A correction survives a new session without exposing another user's profile."""

import json
from tempfile import TemporaryDirectory
from pathlib import Path
from pydantic import Field

from hello_agents import SimpleAgent
from hello_agents.context import ContextBuilder
from hello_agents.memory import ProfileModel, ProfileStore, ProfileContextProvider
from examples._support import demo_llm, response


class TravelProfile(ProfileModel):
    walking_km: int = Field(ge=0, le=30)
    interests: list[str] = Field(default_factory=list)


def main():
    with TemporaryDirectory(prefix="hello-profile-") as folder:
        path = str(Path(folder) / "memory.sqlite")

        def open_profile(user="alice"):
            return ProfileStore(
                path, user_id=user, namespace="travel", schema=TravelProfile
            )

        store = open_profile()
        first = store.put(
            {"walking_km": 8, "interests": ["history", "nature"]},
            source="user:initial-preference",
            expected_revision=0,
        )
        store.patch(
            {"walking_km": 5},
            source="user:corrected-preference",
            expected_revision=first.revision,
        )
        reopened = open_profile()
        assert open_profile("bob").get() is None
        llm = demo_llm([response('{"walking_km": 5}')])
        agent = SimpleAgent(
            "travel",
            llm,
            context_builder=ContextBuilder(),
            context_providers=[ProfileContextProvider(reopened)],
        )
        answer = agent.run(
            "Read the saved profile. Output only JSON with the current walking_km integer. No code fences."
        )
        assert json.loads(answer)["walking_km"] == 5
        print(answer)
        print(
            "Reopened profile uses 5 km; old 8 km is audit history only; Bob has no profile."
        )


if __name__ == "__main__":
    main()
