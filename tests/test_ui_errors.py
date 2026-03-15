"""Tests for friendly error handling (UI-07)."""
import pytest


@pytest.mark.xfail(reason="Wave 0 stub — implement in plan 06-02 onward")
def test_require_scored_pairs_stops_when_missing(monkeypatch):
    """UI-07: require_scored_pairs calls st.stop() when scored_pairs.pkl missing."""
    import streamlit as st
    from app.utils.cache import require_scored_pairs
    assert False


@pytest.mark.xfail(reason="Wave 0 stub — implement in plan 06-02 onward")
def test_missing_embeddings_shows_warning(monkeypatch):
    """UI-07: load_embeddings_cached returns None (not exception) when file absent."""
    from app.utils.cache import load_embeddings_cached
    assert False
