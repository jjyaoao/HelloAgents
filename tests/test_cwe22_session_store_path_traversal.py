"""Test: Path traversal in SessionStore is blocked (CWE-22).

The SessionStore.save(), SessionStore.delete(), and SessionStore.load()
methods must reject path traversal sequences in session names and file paths.
"""

import json
import os
import tempfile
import shutil
from pathlib import Path

import pytest

from hello_agents.core.session_store import SessionStore


class TestCWE22SessionStorePathTraversal:
    """Test that path traversal via session_name is blocked."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.store = SessionStore(session_dir=self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _save_kwargs(self, session_name):
        return dict(
            agent_config={"name": "test"},
            history=[],
            tool_schema_hash="abc",
            read_cache={},
            metadata={},
            session_name=session_name,
        )

    # ---- save() path traversal ----

    def test_save_rejects_dot_dot_slash(self):
        """save() must not write outside the session directory."""
        with pytest.raises(ValueError):
            self.store.save(**self._save_kwargs("../../tmp/evil"))

    def test_save_rejects_absolute_path(self):
        """save() must not accept an absolute path as session_name."""
        with pytest.raises(ValueError):
            self.store.save(**self._save_kwargs("/tmp/evil"))

    def test_save_rejects_backslash_traversal(self):
        """save() must reject Windows-style path traversal."""
        with pytest.raises(ValueError):
            self.store.save(**self._save_kwargs("..\\..\\tmp\\evil"))

    def test_save_rejects_encoded_traversal(self):
        """save() must reject URL-encoded traversal characters."""
        with pytest.raises(ValueError):
            self.store.save(**self._save_kwargs("..%2f..%2ftmp%2fevil"))

    def test_save_allows_legitimate_name(self):
        """save() must still work with valid session names."""
        filepath = self.store.save(**self._save_kwargs("my-session_2024"))
        assert Path(filepath).exists()
        assert Path(filepath).resolve().parent == Path(self.temp_dir).resolve()

    def test_save_allows_dotted_name(self):
        """save() must work with names containing dots (but not ..)."""
        filepath = self.store.save(**self._save_kwargs("v1.2.3-backup"))
        assert Path(filepath).exists()

    # ---- delete() path traversal ----

    def test_delete_rejects_dot_dot_slash(self):
        """delete() must not delete files outside the session directory."""
        with pytest.raises(ValueError):
            self.store.delete("../../tmp/evil")

    def test_delete_rejects_absolute_path(self):
        with pytest.raises(ValueError):
            self.store.delete("/tmp/evil")

    # ---- load() path traversal ----

    def test_load_rejects_path_outside_session_dir(self):
        """load() must refuse to open files outside the session directory."""
        outside_file = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        )
        json.dump({"session_id": "test"}, outside_file)
        outside_file.close()
        try:
            with pytest.raises(ValueError):
                self.store.load(outside_file.name)
        finally:
            os.unlink(outside_file.name)

    def test_load_allows_file_within_session_dir(self):
        """load() must still work for files inside the session directory."""
        filepath = self.store.save(**self._save_kwargs("legit"))
        data = self.store.load(filepath)
        assert data["agent_config"]["name"] == "test"
