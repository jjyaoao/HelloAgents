"""PoC: CWE-22 Path Traversal in DevLogTool via session_id

Demonstrates that a crafted session_id with path traversal characters
causes file writes outside the intended persistence_dir.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from hello_agents.tools.builtin.devlog_tool import DevLogTool


class TestPathTraversalDevLogTool:
    """Tests for CWE-22 path traversal via session_id in DevLogTool."""

    def test_path_traversal_write_escapes_persistence_dir(self):
        """Crafted session_id with '../' escapes persistence_dir when
        a directory named 'devlog-..' exists (e.g. from prior runs or
        attacker-created).

        Before fix: the file is written to project_root/memory/ instead
        of project_root/memory/devlogs/.
        After fix: ValueError is raised on construction.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()
            persistence_dir = project_root / "memory" / "devlogs"
            persistence_dir.mkdir(parents=True)

            # Pre-create directory that enables the traversal
            (persistence_dir / "devlog-..").mkdir(exist_ok=True)

            malicious_session_id = "../../../escaped"

            with pytest.raises(ValueError, match="[Ii]nvalid.*session_id"):
                DevLogTool(
                    session_id=malicious_session_id,
                    agent_name="TestAgent",
                    project_root=str(project_root),
                    persistence_dir="memory/devlogs",
                )

    def test_path_traversal_dotdot_in_session_id(self):
        """session_id containing '..' should be rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="[Ii]nvalid.*session_id"):
                DevLogTool(
                    session_id="../etc/cron.d/backdoor",
                    agent_name="TestAgent",
                    project_root=temp_dir,
                    persistence_dir="devlogs",
                )

    def test_path_traversal_slash_in_session_id(self):
        """session_id containing '/' should be rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="[Ii]nvalid.*session_id"):
                DevLogTool(
                    session_id="foo/bar",
                    agent_name="TestAgent",
                    project_root=temp_dir,
                    persistence_dir="devlogs",
                )

    def test_path_traversal_backslash_in_session_id(self):
        """session_id containing backslash should be rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="[Ii]nvalid.*session_id"):
                DevLogTool(
                    session_id="foo\\bar",
                    agent_name="TestAgent",
                    project_root=temp_dir,
                    persistence_dir="devlogs",
                )

    def test_path_traversal_null_byte_in_session_id(self):
        """session_id containing null byte should be rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="[Ii]nvalid.*session_id"):
                DevLogTool(
                    session_id="session\x00evil",
                    agent_name="TestAgent",
                    project_root=temp_dir,
                    persistence_dir="devlogs",
                )

    def test_valid_session_ids_still_work(self):
        """Normal session_ids should not be affected by the fix."""
        with tempfile.TemporaryDirectory() as temp_dir:
            valid_ids = [
                "s-20250118-143052-a3f2",
                "demo-session-001",
                "test_session_123",
                "abc123",
                "a-b-c_d",
                "session.v2",
            ]
            for sid in valid_ids:
                tool = DevLogTool(
                    session_id=sid,
                    agent_name="TestAgent",
                    project_root=temp_dir,
                    persistence_dir="devlogs",
                )
                assert tool.session_id == sid

                # Verify append + persist works
                response = tool.run({
                    "action": "append",
                    "category": "decision",
                    "content": f"Test log for {sid}",
                })
                assert "日志已记录" in response.text

                # Verify persisted file is inside the persistence dir
                expected_file = Path(temp_dir) / "devlogs" / f"devlog-{sid}.json"
                assert expected_file.exists(), f"File not found for session_id={sid}"

    def test_persist_file_stays_within_persistence_dir(self):
        """After fix, _persist() output must resolve within persistence_dir."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = DevLogTool(
                session_id="safe-session",
                agent_name="TestAgent",
                project_root=temp_dir,
                persistence_dir="devlogs",
            )

            tool.run({
                "action": "append",
                "category": "decision",
                "content": "Test content",
            })

            persistence_dir = Path(temp_dir) / "devlogs"
            devlog_file = persistence_dir / "devlog-safe-session.json"
            assert devlog_file.exists()

            # Verify resolved path is within persistence_dir
            resolved = devlog_file.resolve()
            assert str(resolved).startswith(str(persistence_dir.resolve()))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
