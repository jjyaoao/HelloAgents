import importlib
import sys
import types
from pathlib import Path


def _load_qdrant_store_class():
    """Load the storage module without importing unrelated package exports."""
    package_root = Path(__file__).resolve().parents[1] / "hello_agents"
    packages = {
        "_hello_agents_qdrant_test": package_root,
        "_hello_agents_qdrant_test.memory": package_root / "memory",
        "_hello_agents_qdrant_test.memory.storage": package_root / "memory" / "storage",
    }
    for name, path in packages.items():
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module

    module = importlib.import_module(
        "_hello_agents_qdrant_test.memory.storage.qdrant_store"
    )
    return module.QdrantVectorStore


QdrantVectorStore = _load_qdrant_store_class()


def _uninitialized_store():
    store = object.__new__(QdrantVectorStore)
    store.vector_size = 3
    store.collection_name = "test"
    store.client = None
    return store


def test_add_vectors_rejects_mismatched_metadata_before_zip_truncation():
    store = _uninitialized_store()

    assert store.add_vectors(
        vectors=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
        metadata=[{"content": "only one metadata item"}],
        ids=["point-1", "point-2"],
    ) is False


def test_add_vectors_rejects_mismatched_ids_before_zip_truncation():
    store = _uninitialized_store()

    assert store.add_vectors(
        vectors=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
        metadata=[{"content": "first"}, {"content": "second"}],
        ids=["point-1"],
    ) is False
