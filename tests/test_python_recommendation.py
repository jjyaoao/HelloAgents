from types import SimpleNamespace
from io import StringIO

import pytest
from hello_agents import _python_version


@pytest.mark.parametrize("version,visible", [((3, 12, 0), True), ((3, 13, 0), False)])
def test_recommendation_is_informational_and_does_not_use_stdout(monkeypatch, capsys, version, visible):
    output = StringIO()
    monkeypatch.setattr(_python_version, "sys", SimpleNamespace(version_info=version, stderr=output))
    _python_version.show_recommendation()
    assert bool(output.getvalue()) == visible
    if visible:
        assert "继续运行" in output.getvalue()
        assert "Python 3.13" in output.getvalue()
    assert capsys.readouterr().out == ""
