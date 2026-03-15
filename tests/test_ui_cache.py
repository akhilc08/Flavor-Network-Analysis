"""Tests for caching behavior (UI-06)."""
import pytest


@pytest.mark.xfail(reason="Wave 0 stub — implement in plan 06-02/03")
def test_invalidate_scored_pairs_clears_only_scored_pairs():
    """UI-06: invalidate_scored_pairs() does not clear embeddings cache."""
    from app.utils.cache import invalidate_scored_pairs, load_embeddings_cached
    assert False


@pytest.mark.xfail(reason="Wave 0 stub — implement in plan 06-02/03")
def test_require_scored_pairs_returns_list_when_file_present(tmp_path, monkeypatch):
    """UI-06: require_scored_pairs returns data when scored_pairs.pkl exists."""
    from app.utils import cache
    assert False
