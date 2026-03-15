"""Tests for caching behavior (UI-06)."""
import pickle
import pytest


def test_invalidate_scored_pairs_clears_only_scored_pairs(monkeypatch):
    """UI-06: invalidate_scored_pairs() does not clear embeddings cache."""
    from app.utils import cache

    scored_clear_called = []
    embeddings_clear_called = []

    monkeypatch.setattr(cache.load_scored_pairs_cached, "clear",
                        lambda: scored_clear_called.append(True))
    monkeypatch.setattr(cache.load_embeddings_cached, "clear",
                        lambda: embeddings_clear_called.append(True))

    cache.invalidate_scored_pairs()

    assert len(scored_clear_called) == 1, "load_scored_pairs_cached.clear() should be called once"
    assert len(embeddings_clear_called) == 0, "load_embeddings_cached.clear() must NOT be called"


def test_require_scored_pairs_returns_list_when_file_present(tmp_path, monkeypatch):
    """UI-06: require_scored_pairs returns data when scored_pairs.pkl exists."""
    import app.utils.cache as cache_module

    # Write a real pickle to a temp file
    fake_pairs = [{"ingredient_a": "strawberry", "ingredient_b": "vanilla"}]
    pkl_path = tmp_path / "scored_pairs.pkl"
    pkl_path.write_bytes(pickle.dumps(fake_pairs))

    # Patch the PATH constant and bypass the @st.cache_resource cache
    monkeypatch.setattr(cache_module, "SCORED_PAIRS_PATH", pkl_path)

    # Clear st.cache_resource state so load_scored_pairs_cached re-runs
    cache_module.load_scored_pairs_cached.clear()

    result = cache_module.require_scored_pairs()

    assert isinstance(result, list)
    assert len(result) == 1
