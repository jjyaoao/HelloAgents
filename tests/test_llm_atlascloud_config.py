"""Atlas Cloud environment fallback tests."""

import os
from unittest.mock import MagicMock, patch

from hello_agents.core.llm import HelloAgentsLLM


@patch("hello_agents.core.llm.create_adapter")
def test_atlascloud_key_uses_openai_compatible_defaults(create_adapter: MagicMock):
    with patch.dict(
        os.environ,
        {"ATLASCLOUD_API_KEY": "atlas-key"},
        clear=True,
    ):
        llm = HelloAgentsLLM()

    assert llm.api_key == "atlas-key"
    assert llm.base_url == "https://api.atlascloud.ai/v1"
    assert llm.model == "deepseek-ai/deepseek-v4-pro"
    create_adapter.assert_called_once_with(
        api_key="atlas-key",
        base_url="https://api.atlascloud.ai/v1",
        timeout=60,
        model="deepseek-ai/deepseek-v4-pro",
    )


@patch("hello_agents.core.llm.create_adapter")
def test_atlas_cloud_aliases_override_atlas_defaults(create_adapter: MagicMock):
    with patch.dict(
        os.environ,
        {
            "ATLAS_CLOUD_API_KEY": "atlas-key",
            "ATLAS_CLOUD_BASE_URL": "https://atlas.example/v1",
            "ATLAS_CLOUD_MODEL": "qwen/qwen3.5-flash",
        },
        clear=True,
    ):
        llm = HelloAgentsLLM()

    assert llm.api_key == "atlas-key"
    assert llm.base_url == "https://atlas.example/v1"
    assert llm.model == "qwen/qwen3.5-flash"


@patch("hello_agents.core.llm.create_adapter")
def test_generic_llm_environment_keeps_priority(create_adapter: MagicMock):
    with patch.dict(
        os.environ,
        {
            "LLM_API_KEY": "generic-key",
            "LLM_BASE_URL": "https://generic.example/v1",
            "LLM_MODEL_ID": "generic-model",
            "ATLASCLOUD_API_KEY": "atlas-key",
            "ATLASCLOUD_BASE_URL": "https://api.atlascloud.ai/v1",
            "ATLASCLOUD_MODEL": "deepseek-ai/deepseek-v4-pro",
        },
        clear=True,
    ):
        llm = HelloAgentsLLM()

    assert llm.api_key == "generic-key"
    assert llm.base_url == "https://generic.example/v1"
    assert llm.model == "generic-model"
