"""Tests for Page 1 — Ingredient Search (UI-01, UI-02)."""
import pytest

# Utility functions under test are extracted from pages into app/utils/
# so they can be tested without running the Streamlit server.


@pytest.mark.xfail(reason="Wave 0 stub — implement in plan 06-02")
def test_get_top_pairings_returns_10():
    """UI-01: get_top_pairings(ingredient, pairs) returns exactly 10 results."""
    from app.utils.search import get_top_pairings
    # Stub: will implement when 1_Search.py + search utils are built
    assert False


@pytest.mark.xfail(reason="Wave 0 stub — implement in plan 06-02")
def test_radar_chart_has_two_traces():
    """UI-01: build_radar_chart returns Figure with exactly 2 Scatterpolar traces."""
    from app.utils.search import build_radar_chart
    assert False


@pytest.mark.xfail(reason="Wave 0 stub — implement in plan 06-02")
def test_why_it_works_lists_shared_molecules():
    """UI-02: format_why_it_works returns string mentioning each shared molecule name."""
    from app.utils.search import format_why_it_works
    assert False
