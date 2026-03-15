"""
scoring/score.py — Public API stubs for Phase 5 scoring module.

All functions raise NotImplementedError until Wave 1 implements the actual logic.

Locked API (do not change signatures):
    compute_all_pairs(embeddings, co_occurrence, molecule_sets) -> pd.DataFrame
    load_scored_pairs() -> pd.DataFrame
    get_top_pairings(ingredient_name, n=10) -> list[dict]
    get_uncertain_pairs(n=20) -> list[dict]
"""

from __future__ import annotations

import pandas as pd


def compute_all_pairs(
    embeddings: dict,
    co_occurrence: dict,
    molecule_sets: dict,
) -> pd.DataFrame:
    """
    Compute surprise scores for every ingredient pair.

    Args:
        embeddings:     {ingredient_name: np.ndarray of shape (128,)} — GAT embeddings
        co_occurrence:  {(ingredient_a, ingredient_b): int} — recipe co-occurrence counts
        molecule_sets:  {ingredient_name: frozenset[int]} — set of PubChem molecule IDs

    Returns:
        DataFrame with columns:
            ingredient_a, ingredient_b,
            pairing_score, molecular_overlap, recipe_familiarity,
            surprise_score, label
        Sorted by surprise_score descending.

    Raises:
        NotImplementedError: until Wave 1 implementation.
    """
    raise NotImplementedError(
        "compute_all_pairs() is not yet implemented — Wave 1 task (SCORE-01..04)"
    )


def load_scored_pairs() -> pd.DataFrame:
    """
    Load pre-computed scored pairs from disk.

    Returns:
        DataFrame read from scoring/scored_pairs.pkl, sorted by surprise_score descending.

    Raises:
        NotImplementedError: until Wave 1 implementation.
        FileNotFoundError: if scoring/scored_pairs.pkl does not exist.
    """
    raise NotImplementedError(
        "load_scored_pairs() is not yet implemented — Wave 1 task (SCORE-03)"
    )


def get_top_pairings(ingredient_name: str, n: int = 10) -> list[dict]:
    """
    Return the top-n surprising pairings for a given ingredient.

    Args:
        ingredient_name: Name of the ingredient to query.
        n:               Number of top pairings to return (default 10).

    Returns:
        List of dicts, each with keys:
            ingredient_a, ingredient_b, surprise_score, pairing_score,
            molecular_overlap, recipe_familiarity, label
        Sorted by surprise_score descending.

    Raises:
        NotImplementedError: until Wave 1 implementation.
    """
    raise NotImplementedError(
        "get_top_pairings() is not yet implemented — Wave 1 task (SCORE-04)"
    )


def get_uncertain_pairs(n: int = 20) -> list[dict]:
    """
    Return the n ingredient pairs whose pairing_score is closest to 0.5.

    These are the most informative pairs for active learning — the model is
    maximally uncertain about whether they co-occur in recipes.

    Args:
        n: Number of uncertain pairs to return (default 20).

    Returns:
        List of dicts sorted by abs(pairing_score - 0.5) ascending.
        Each dict has keys: ingredient_a, ingredient_b, pairing_score,
        surprise_score, molecular_overlap, recipe_familiarity, label.

    Raises:
        NotImplementedError: until Wave 1 implementation.
    """
    raise NotImplementedError(
        "get_uncertain_pairs() is not yet implemented — Wave 1 task (LEARN-02)"
    )
