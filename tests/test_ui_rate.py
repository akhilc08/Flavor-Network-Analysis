"""Tests for Page 2 — Active Learning Rating (UI-03)."""
import pytest


@pytest.mark.xfail(reason="Wave 0 stub — implement in plan 06-03")
def test_get_uncertain_pairs_returns_five():
    """UI-03: get_uncertain_pairs returns exactly 5 pairs."""
    from app.utils.rate import get_uncertain_pairs_for_display
    assert False


@pytest.mark.xfail(reason="Wave 0 stub — implement in plan 06-03")
def test_submit_ratings_calls_submit_for_each_pair():
    """UI-03: submit_all_ratings calls submit_rating once per pair."""
    from app.utils.rate import submit_all_ratings
    assert False
