"""Utilities for the active learning rating page (UI-03)."""
from __future__ import annotations


def get_uncertain_pairs_for_display(pairs: list, n: int = 5) -> list:
    """Return the n pairs most uncertain (pairing_score closest to 0.5)."""
    from types import SimpleNamespace
    from pathlib import Path
    try:
        from scoring.score import get_uncertain_pairs
        records = get_uncertain_pairs(n)

        # scored_pairs uses integer ingredient IDs — resolve to names
        try:
            import pandas as pd
            ing_path = Path("data/processed/ingredients.parquet")
            if ing_path.exists():
                ing_df = pd.read_parquet(ing_path, columns=["ingredient_id", "name"])
                id_to_name = dict(zip(ing_df["ingredient_id"], ing_df["name"]))
                for d in records:
                    d["ingredient_a"] = id_to_name.get(d["ingredient_a"], str(d["ingredient_a"]))
                    d["ingredient_b"] = id_to_name.get(d["ingredient_b"], str(d["ingredient_b"]))
        except Exception:
            pass

        return [SimpleNamespace(**d) for d in records]
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
