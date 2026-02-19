"""pytest 共享 fixture：Mock LLM 等"""

from typing import Iterator
import pytest


class MockLLM:
    """用于测试的假 LLM，不发起真实 API 调用。"""

    def __init__(self, response: str = "Mock response", provider: str = "mock"):
        self.response = response
        self.provider = provider
        self.model = "mock-model"

    def invoke(self, messages: list, **kwargs) -> str:
        return self.response

    def stream_invoke(self, messages: list, **kwargs) -> Iterator[str]:
        for char in self.response:
            yield char


@pytest.fixture
def mock_llm() -> MockLLM:
    """提供 MockLLM 实例。"""
    return MockLLM(response="Hello from mock LLM.")
