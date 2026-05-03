"""Config model helper tests."""

import warnings

from hello_agents.core.config import Config


def test_to_dict_uses_model_dump_no_deprecated_warning() -> None:
    """Config.to_dict should use Pydantic v2 serializer without deprecated dict()."""

    config = Config()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        data = config.to_dict()

    if hasattr(config, "model_dump"):
        assert data == config.model_dump()
    else:
        assert data == config.dict()

    assert all(
        "use `model_dump`" not in str(w.message)
        for w in caught
    )
