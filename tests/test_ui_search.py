"""Tests for Page 1 — Ingredient Search (UI-01, UI-02)."""
import pytest


def _make_mock_pair(ingredient_a, ingredient_b, surprise_score=0.5, pairing_score=0.6,
                    label="Classic", shared_molecules=None, flavor_profile_a=None,
                    flavor_profile_b=None):
    """Build a simple namespace object mimicking a scored pair."""
    from types import SimpleNamespace
    return SimpleNamespace(
        ingredient_a=ingredient_a,
        ingredient_b=ingredient_b,
        surprise_score=surprise_score,
        pairing_score=pairing_score,
        label=label,
        shared_molecules=shared_molecules or [],
        flavor_profile_a=flavor_profile_a or {},
        flavor_profile_b=flavor_profile_b or {},
    )


def test_get_top_pairings_returns_10():
    """UI-01: get_top_pairings(ingredient, pairs) returns exactly 10 results."""
    from app.utils.search import get_top_pairings

    # Build 15 strawberry pairs with distinct surprise scores
    pairs = [
        _make_mock_pair("strawberry", f"ingredient_{i}", surprise_score=i * 0.05)
        for i in range(15)
    ]
    # Add some non-strawberry pairs to ensure filtering works
    pairs += [_make_mock_pair("lemon", f"other_{i}") for i in range(5)]

    results = get_top_pairings("strawberry", pairs)
    assert len(results) == 10


def test_get_top_pairings_sorted_by_surprise_score():
    """UI-01: results are sorted by surprise_score descending."""
    from app.utils.search import get_top_pairings

    pairs = [
        _make_mock_pair("strawberry", f"ingredient_{i}", surprise_score=i * 0.05)
        for i in range(15)
    ]
    results = get_top_pairings("strawberry", pairs)
    scores = [p.surprise_score for p in results]
    assert scores == sorted(scores, reverse=True)


def test_get_top_pairings_returns_empty_on_no_match():
    """UI-01: get_top_pairings returns [] when no ingredient matches."""
    from app.utils.search import get_top_pairings

    pairs = [_make_mock_pair("lemon", "basil")]
    results = get_top_pairings("strawberry", pairs)
    assert results == []


def test_radar_chart_has_two_traces():
    """UI-01: build_radar_chart returns Figure with exactly 2 Scatterpolar traces."""
    from app.utils.search import build_radar_chart

    profile_a = {"sweet": 0.8, "sour": 0.3, "umami": 0.1, "bitter": 0.05, "floral": 0.6, "smoky": 0.0}
    profile_b = {"sweet": 0.2, "sour": 0.5, "umami": 0.4, "bitter": 0.2, "floral": 0.1, "smoky": 0.3}

    fig = build_radar_chart("Strawberry", profile_a, "Lemon", profile_b)
    assert len(fig.data) == 2


def test_radar_chart_trace_names():
    """UI-01: traces are named after the two ingredients."""
    from app.utils.search import build_radar_chart

    profile = {"sweet": 0.5, "sour": 0.5, "umami": 0.0, "bitter": 0.0, "floral": 0.5, "smoky": 0.0}
    fig = build_radar_chart("Strawberry", profile, "Lemon", profile)
    names = [trace.name for trace in fig.data]
    assert "Strawberry" in names
    assert "Lemon" in names


def test_why_it_works_lists_shared_molecules():
    """UI-02: format_why_it_works returns string mentioning each shared molecule name."""
    from app.utils.search import format_why_it_works

    result = format_why_it_works(["Linalool", "Furaneol"])
    assert "Linalool" in result
    assert "Furaneol" in result


def test_why_it_works_empty_returns_fallback():
    """UI-02: format_why_it_works returns fallback string when no molecules."""
    from app.utils.search import format_why_it_works

    result = format_why_it_works([])
    assert "No shared flavor molecules found." in result
