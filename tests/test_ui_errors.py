"""Tests for friendly error handling (UI-07)."""
import pytest


def test_require_scored_pairs_stops_when_missing(monkeypatch):
    """UI-07: require_scored_pairs calls st.stop() when scored_pairs.pkl missing."""
    from pathlib import Path
    import app.utils.cache as cache_module
    import streamlit as st

    # Ensure a non-existent path
    monkeypatch.setattr(cache_module, "SCORED_PAIRS_PATH", Path("/nonexistent/scored_pairs.pkl"))
    # Clear cache so the function re-evaluates with the new path
    cache_module.load_scored_pairs_cached.clear()

    stop_calls = []
    warning_calls = []

    monkeypatch.setattr(st, "warning", lambda *a, **kw: warning_calls.append(a))
    monkeypatch.setattr(st, "stop", lambda: stop_calls.append(True))

    # require_scored_pairs calls st.stop() — with monkeypatched stop it won't actually halt
    cache_module.require_scored_pairs()

    assert len(stop_calls) == 1, "st.stop() should be called exactly once"
    assert len(warning_calls) == 1, "st.warning() should be called with the missing-file message"


def test_missing_embeddings_shows_warning(monkeypatch):
    """UI-07: load_embeddings_cached returns None (not exception) when file absent."""
    from pathlib import Path
    import app.utils.cache as cache_module

    monkeypatch.setattr(cache_module, "EMBEDDINGS_PATH", Path("/nonexistent/embeddings.pkl"))
    cache_module.load_embeddings_cached.clear()

    result = cache_module.load_embeddings_cached()

    assert result is None
