"""Utilities for the active learning rating page (UI-03)."""
from __future__ import annotations


def get_uncertain_pairs_for_display(pairs: list, n: int = 5) -> list:
    """Return the n pairs most uncertain (pairing_score closest to 0.5)."""
    try:
        from scoring.score import get_uncertain_pairs
        return get_uncertain_pairs(pairs, n)
    except ImportError:
        # Fallback if Phase 5 not yet built
        return sorted(pairs, key=lambda p: abs(getattr(p, "pairing_score", 0.5) - 0.5))[:n]


def submit_all_ratings(ratings_map: dict, pairs: list) -> dict:
    """
    Submit ratings for each rated pair.
    ratings_map: {pair_key: int(1-5)} where pair_key = f"{a}|{b}"
    Returns last submit_rating result dict or {"auc_before": None, "auc_after": None}.
    """
    from model.active_learning import submit_rating

    result = {"auc_before": None, "auc_after": None}
    pair_lookup = {f"{p.ingredient_a}|{p.ingredient_b}": p for p in pairs}

    for pair_key, rating in ratings_map.items():
        if rating == 0:
            continue
        pair = pair_lookup.get(pair_key)
        if pair is None:
            continue
        try:
            result = submit_rating(pair.ingredient_a, pair.ingredient_b, rating)
        except Exception as e:
            # Log but don't crash; return partial result
            import streamlit as st
            st.error(f"Fine-tuning failed: {e}")
            break

    return result
