"""Default pytest is local; opt in to marked service tests with --run-live."""

import ipaddress
import os
import socket

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="运行标记为 live 的真实模型服务测试（可能产生费用）",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: calls a configured external model service; requires --run-live",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-live"):
        skip = pytest.mark.skip(reason="真实服务测试需显式 --run-live")
        for item in items:
            if item.get_closest_marker("live"):
                item.add_marker(skip)


@pytest.fixture
def live_llm_config():
    missing = [
        key
        for key in ("LLM_MODEL_ID", "LLM_API_KEY", "LLM_BASE_URL")
        if not os.getenv(key)
    ]
    if missing:
        pytest.fail("真实测试缺少配置：" + ", ".join(missing))
    return {
        "model": os.environ["LLM_MODEL_ID"],
        "api_key": os.environ["LLM_API_KEY"],
        "base_url": os.environ["LLM_BASE_URL"],
        "provider": os.getenv("LLM_PROVIDER", "openai"),
    }


@pytest.fixture(autouse=True)
def local_test_environment(request, monkeypatch):
    if request.node.get_closest_marker("live"):
        return
    # Constructor-only tests can run without local credentials. Tests may override
    # these values explicitly; service calls remain blocked below.
    for key, value in {
        "LLM_API_KEY": "offline-test-key",
        "LLM_MODEL_ID": "offline-test-model",
        "LLM_BASE_URL": "http://127.0.0.1:9/v1",
        "LLM_PROVIDER": "openai",
    }.items():
        monkeypatch.setenv(key, value)
    original_resolve, original_connect, original_connect_ex = (
        socket.getaddrinfo,
        socket.socket.connect,
        socket.socket.connect_ex,
    )

    def allowed(host):
        if isinstance(host, bytes):
            host = host.decode("ascii")
        if host in (None, "", "localhost"):
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def resolve(host, *args, **kwargs):
        if not allowed(host):
            raise RuntimeError(
                "本地测试禁止外部网络；真实服务用例必须标记 live 并显式启用"
            )
        return original_resolve(host, *args, **kwargs)

    def guard(method):
        def connect(sock, address):
            if isinstance(address, tuple) and not allowed(address[0]):
                raise RuntimeError("本地测试禁止外部网络")
            return method(sock, address)

        return connect

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    monkeypatch.setattr(socket.socket, "connect", guard(original_connect))
    monkeypatch.setattr(socket.socket, "connect_ex", guard(original_connect_ex))
