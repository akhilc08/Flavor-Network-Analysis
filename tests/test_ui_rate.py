"""Tests for Page 2 — Active Learning Rating (UI-03)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest


def _make_pair(a: str, b: str, score: float, label: str = "test"):
    """Create a mock scored pair with the expected attribute interface."""
    return SimpleNamespace(
        ingredient_a=a,
        ingredient_b=b,
        pairing_score=score,
        label=label,
    )


def test_get_uncertain_pairs_returns_five():
    """UI-03: get_uncertain_pairs_for_display returns exactly 5 pairs, closest to 0.5 first."""
    from app.utils.rate import get_uncertain_pairs_for_display

    # Build 10 mock pairs with varying distances from 0.5
    # Pairs closest to 0.5 (uncertainty ~ 0) should be returned first
    pairs = [
        _make_pair("a", "b", 0.50),   # uncertainty 0.00 — most uncertain
        _make_pair("c", "d", 0.51),   # uncertainty 0.01
        _make_pair("e", "f", 0.49),   # uncertainty 0.01
        _make_pair("g", "h", 0.55),   # uncertainty 0.05
        _make_pair("i", "j", 0.45),   # uncertainty 0.05
        _make_pair("k", "l", 0.70),   # uncertainty 0.20
        _make_pair("m", "n", 0.30),   # uncertainty 0.20
        _make_pair("o", "p", 0.80),   # uncertainty 0.30
        _make_pair("q", "r", 0.20),   # uncertainty 0.30
        _make_pair("s", "t", 0.90),   # uncertainty 0.40
    ]

    result = get_uncertain_pairs_for_display(pairs, 5)

    assert len(result) == 5
    # First result should be the pair with pairing_score closest to 0.5
    assert result[0].ingredient_a == "a"
    assert result[0].ingredient_b == "b"


def test_submit_ratings_calls_submit_for_each_pair():
    """UI-03: submit_all_ratings calls submit_rating once per rated pair."""
    from app.utils.rate import submit_all_ratings

    pairs = [
        _make_pair("basil", "tomato", 0.51),
        _make_pair("mint", "chocolate", 0.49),
        _make_pair("garlic", "lemon", 0.52),
    ]

    ratings_map = {
        "basil|tomato": 4,
        "mint|chocolate": 5,
        "garlic|lemon": 3,
    }

    mock_result = {"auc_before": 0.72, "auc_after": 0.75}

    with patch("model.active_learning.submit_rating", return_value=mock_result) as mock_submit:
        result = submit_all_ratings(ratings_map, pairs)

    assert mock_submit.call_count == 3
    assert result["auc_before"] == 0.72
    assert result["auc_after"] == 0.75


def test_submit_ratings_skips_zero_ratings():
    """submit_all_ratings skips pairs with rating == 0."""
    from app.utils.rate import submit_all_ratings

    pairs = [
        _make_pair("basil", "tomato", 0.51),
        _make_pair("mint", "chocolate", 0.49),
    ]

    ratings_map = {
        "basil|tomato": 0,  # should be skipped
        "mint|chocolate": 3,
    }

    mock_result = {"auc_before": 0.71, "auc_after": 0.72}

    with patch("model.active_learning.submit_rating", return_value=mock_result) as mock_submit:
        result = submit_all_ratings(ratings_map, pairs)

    assert mock_submit.call_count == 1
    assert result["auc_after"] == 0.72


def test_submit_ratings_returns_empty_result_if_no_pairs_rated():
    """submit_all_ratings returns {auc_before: None, auc_after: None} when all ratings are 0."""
    from app.utils.rate import submit_all_ratings

    pairs = [_make_pair("basil", "tomato", 0.51)]
    ratings_map = {"basil|tomato": 0}

    with patch("model.active_learning.submit_rating") as mock_submit:
        result = submit_all_ratings(ratings_map, pairs)

    mock_submit.assert_not_called()
    assert result == {"auc_before": None, "auc_after": None}
