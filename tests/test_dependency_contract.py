"""Guard dependency boundaries and the install graph shipped to readers."""
from pathlib import Path
import re
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_every_direct_dependency_and_python_have_bounds():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    groups = [config["build-system"]["requires"], config["project"]["dependencies"],
              *config["project"]["optional-dependencies"].values(),
              *config.get("dependency-groups", {}).values()]
    ranges = [SpecifierSet(config["project"]["requires-python"])]
    ranges += [Requirement(entry).specifier for group in groups for entry in group]
    for bounds in ranges:
        operators = {s.operator for s in bounds}
        assert operators & {">=", ">", "=="}, str(bounds)
        assert operators & {"<=", "<", "=="}, str(bounds)


def test_supported_python_matches_recommended_runtime():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    supported = SpecifierSet(config["project"]["requires-python"])
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.13"
    assert "3.13" in supported and "3.13.1" in supported
    assert "3.12" in supported
    assert "3.11" not in supported and "3.14" not in supported


def test_exports_pin_the_lock_and_cover_every_extra():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    normalize = lambda name: re.sub(r"[-_.]+", "-", name).lower()
    versions = {}
    for package in lock["package"]:
        versions.setdefault(normalize(package["name"]), set()).add(package["version"])
    exports = [(ROOT / "requirements.txt", [])]
    extras = config["project"]["optional-dependencies"]
    exports += [(ROOT / "requirements" / f"{name}.txt", group) for name, group in extras.items()]
    exports += [(ROOT / "requirements/all.txt", [d for group in extras.values() for d in group])]
    for path, additional in exports:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                 if line.strip() and not line.startswith("#")]
        assert "-e ." in lines, path
        found = {}
        for line in lines:
            if line == "-e .":
                continue
            req = Requirement(line)
            pins = list(req.specifier)
            assert len(pins) == 1 and pins[0].operator == "==", line
            assert pins[0].version in versions[normalize(req.name)], line
            found.setdefault(normalize(req.name), []).append(Version(pins[0].version))
        for declaration in config["project"]["dependencies"] + additional:
            req = Requirement(declaration)
            assert normalize(req.name) in found, (path, declaration)
            assert all(v in req.specifier for v in found[normalize(req.name)]), declaration


@pytest.mark.parametrize("module,adapter_name,url", [
    ("openai", "OpenAIAdapter", "https://example.invalid/v1"),
    ("anthropic", "AnthropicAdapter", "https://api.anthropic.com"),
    ("google.genai", "GeminiAdapter", "https://generativelanguage.googleapis.com"),
])
def test_locked_sdk_client_constructors(module, adapter_name, url):
    # Actual SDK initialization, without sending prompts or opening a connection.
    pytest.importorskip(module)
    from hello_agents.core import llm_adapters
    adapter = getattr(llm_adapters, adapter_name)("offline-test-key", url, 10, "test-model")
    client = adapter.create_client()
    assert client is not None
    client.close()
