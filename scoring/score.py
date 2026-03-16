"""
scoring/score.py — Vectorized all-pairs scoring for the Flavor Network.

Public API (signatures locked — Phase 6 imports these):
    compute_all_pairs    — Vectorized all-pairs surprise scoring
    load_scored_pairs    — Load scored_pairs.pkl from disk
    get_top_pairings     — Top-n pairings for a given ingredient
    get_uncertain_pairs  — Pairs with pairing_score closest to 0.5
    save_scored_pairs    — Atomic write of scored DataFrame to disk
"""

from __future__ import annotations

from pathlib import Path
import os
import logging

import numpy as np
import pandas as pd
import torch

SCORED_PAIRS_PATH = Path("scoring/scored_pairs.pkl")
LABEL_NAMES = ["Classic", "Unexpected", "Surprising"]

logger = logging.getLogger(__name__)


def compute_all_pairs(
    embeddings: dict,
    co_occurrence: dict,
    molecule_sets: dict,
) -> pd.DataFrame:
    """
    Compute surprise scores for every ingredient pair using vectorized matmul.

    Args:
        embeddings:     {ingredient_name: np.ndarray of shape (128,)} — GAT embeddings
        co_occurrence:  {(ingredient_a, ingredient_b): count} — recipe co-occurrence counts
                        (symmetric; either key order may be present)
        molecule_sets:  {ingredient_name: set of int pubchem_ids}

    Returns:
        DataFrame with columns:
            ingredient_a, ingredient_b, surprise_score, pairing_score,
            molecular_overlap, recipe_familiarity, label
        Sorted by surprise_score descending.
    """
    names = list(embeddings.keys())
    n = len(names)

    if n < 2:
        return pd.DataFrame(columns=[
            "ingredient_a", "ingredient_b", "surprise_score",
            "pairing_score", "molecular_overlap", "recipe_familiarity", "label",
        ])

    # 1. Build (n, 128) float32 CPU tensor from embeddings dict
    emb_matrix = torch.tensor(
        np.stack([embeddings[name].astype(np.float32) for name in names]),
        dtype=torch.float32,
    )

    # 2. sim = emb @ emb.T  (~3.8 MB at n=1000)
    sim = emb_matrix @ emb_matrix.T  # (n, n)

    # 3. Upper-triangle indices (no self-pairs, no duplicates)
    rows, cols = torch.triu_indices(n, n, offset=1)

    # 4. pairing_scores via sigmoid — MUST use sigmoid per locked decision
    pairing_scores = torch.sigmoid(sim[rows, cols]).numpy()  # shape (n_pairs,)

    rows_np = rows.numpy()
    cols_np = cols.numpy()
    n_pairs = len(rows_np)

    # 5. molecular_overlap: Jaccard similarity per pair
    mol_overlap = np.zeros(n_pairs, dtype=np.float32)
    for k in range(n_pairs):
        r, c = rows_np[k], cols_np[k]
        set_a = molecule_sets.get(names[r], set())
        set_b = molecule_sets.get(names[c], set())
        if set_a or set_b:
            intersection = len(set_a & set_b)
            union = len(set_a | set_b)
            mol_overlap[k] = intersection / union if union > 0 else 0.0
        # else: both empty → overlap = 0.0 (already initialized)

    # 6. recipe_familiarity: co_occurrence / max_co_occurrence
    max_cooc = max(co_occurrence.values(), default=0)
    recipe_fam = np.zeros(n_pairs, dtype=np.float32)
    for k in range(n_pairs):
        r, c = rows_np[k], cols_np[k]
        count = max(
            co_occurrence.get((names[r], names[c]), 0),
            co_occurrence.get((names[c], names[r]), 0),
        )
        recipe_fam[k] = count / max(max_cooc, 1)

    # 7. surprise_score formula
    surprise_scores = pairing_scores * (1 - recipe_fam) * (1 - mol_overlap * 0.5)

    # 8. Build DataFrame with all 7 columns
    df = pd.DataFrame({
        "ingredient_a": [names[r] for r in rows_np],
        "ingredient_b": [names[c] for c in cols_np],
        "surprise_score": surprise_scores.astype(np.float64),
        "pairing_score": pairing_scores.astype(np.float64),
        "molecular_overlap": mol_overlap.astype(np.float64),
        "recipe_familiarity": recipe_fam.astype(np.float64),
    })

    # Apply percentile-based label bins so labels are evenly distributed
    p33 = df["surprise_score"].quantile(0.33)
    p67 = df["surprise_score"].quantile(0.67)
    label_bins = [df["surprise_score"].min() - 0.001, p33, p67, df["surprise_score"].max() + 0.001]
    df["label"] = pd.cut(
        df["surprise_score"],
        bins=label_bins,
        labels=LABEL_NAMES,
    )

    # Sort by surprise_score descending and reset index
    df = df.sort_values("surprise_score", ascending=False).reset_index(drop=True)

    logger.debug(
        "compute_all_pairs: produced %d pairs for %d ingredients", len(df), n
    )
    return df


def save_scored_pairs(df: pd.DataFrame) -> None:
    """
    Atomically write scored pairs DataFrame to scoring/scored_pairs.pkl.

    Uses a tmp file + os.replace for POSIX atomicity.
    """
    SCORED_PAIRS_PATH.parent.mkdir(exist_ok=True)
    tmp = SCORED_PAIRS_PATH.with_suffix(".pkl.tmp")
    df.to_pickle(tmp)
    os.replace(tmp, SCORED_PAIRS_PATH)  # atomic on POSIX
    logger.info("Saved scored pairs to %s", SCORED_PAIRS_PATH)


def load_scored_pairs() -> pd.DataFrame:
    """
    Load pre-computed scored pairs from scoring/scored_pairs.pkl.

    Returns:
        DataFrame sorted by surprise_score descending.
    """
    return pd.read_pickle(SCORED_PAIRS_PATH)


def get_top_pairings(ingredient_name: str, n: int = 10) -> list[dict]:
    """
    Return the top-n surprising pairings for a given ingredient.

    Args:
        ingredient_name: Name of the ingredient to query.
        n:               Number of top pairings to return (default 10).

    Returns:
        List of dicts sorted by surprise_score descending (inherited from disk sort).
    """
    df = load_scored_pairs()
    mask = (df["ingredient_a"] == ingredient_name) | (df["ingredient_b"] == ingredient_name)
    return df[mask].head(n).to_dict(orient="records")


def get_uncertain_pairs(n: int = 20) -> list[dict]:
    """
    Return the n ingredient pairs whose pairing_score is closest to 0.5.

    These are the most informative pairs for active learning — the model is
    maximally uncertain about whether they co-occur in recipes.

    Args:
        n: Number of uncertain pairs to return (default 20).

    Returns:
        List of dicts sorted by abs(pairing_score - 0.5) ascending.
    """
    df = load_scored_pairs()
    df = df.copy()
    df["_unc"] = (df["pairing_score"] - 0.5).abs()
    return df.nsmallest(n, "_unc").drop(columns="_unc").to_dict(orient="records")
