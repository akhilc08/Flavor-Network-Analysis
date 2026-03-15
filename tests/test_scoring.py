"""
Test stubs for Phase 5 scoring module (Wave 0 scaffold).

Requirements: SCORE-01, SCORE-02, SCORE-03, SCORE-04, LEARN-02

All unit tests (not guarded by skipif) are expected to FAIL with NotImplementedError
until Wave 1 implements the actual scoring logic in scoring/score.py.
Integration tests are SKIPPED until Phase 4 artifacts are present.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from scoring.score import (
    compute_all_pairs,
    load_scored_pairs,
    get_top_pairings,
    get_uncertain_pairs,
)


# ---------------------------------------------------------------------------
# SCORE-01: Surprise formula correctness
# ---------------------------------------------------------------------------

def test_surprise_formula():
    """
    SCORE-01: Verify surprise_score = pairing_score × (1 - recipe_familiarity) × (1 - molecular_overlap × 0.5)

    Uses a synthetic DataFrame with 3 rows of known values and checks the
    formula output within 1e-6 tolerance.
    Expected to FAIL with NotImplementedError until Wave 1.
    """
    rows = [
        {"pairing_score": 0.8, "recipe_familiarity": 0.2, "molecular_overlap": 0.4},
        {"pairing_score": 0.5, "recipe_familiarity": 0.5, "molecular_overlap": 0.0},
        {"pairing_score": 1.0, "recipe_familiarity": 0.0, "molecular_overlap": 1.0},
    ]
    df = pd.DataFrame(rows)

    # Expected: ps × (1 - rf) × (1 - mo × 0.5)
    expected = [
        0.8 * (1 - 0.2) * (1 - 0.4 * 0.5),   # 0.8 × 0.8 × 0.8 = 0.512
        0.5 * (1 - 0.5) * (1 - 0.0 * 0.5),   # 0.5 × 0.5 × 1.0 = 0.25
        1.0 * (1 - 0.0) * (1 - 1.0 * 0.5),   # 1.0 × 1.0 × 0.5 = 0.5
    ]

    # compute_all_pairs must produce surprise_score matching the formula.
    # At Wave 0 this raises NotImplementedError — test correctly fails.
    embeddings = {
        "a": np.random.randn(128).astype(np.float32),
        "b": np.random.randn(128).astype(np.float32),
        "c": np.random.randn(128).astype(np.float32),
    }
    molecule_sets = {
        "a": frozenset({1, 2, 3}),
        "b": frozenset({2, 4}),
        "c": frozenset({5}),
    }
    co_occurrence = {("a", "b"): 10, ("b", "c"): 3, ("a", "c"): 0}

    result_df = compute_all_pairs(embeddings, co_occurrence, molecule_sets)

    # Verify formula for a known row in result_df
    for _, row in result_df.iterrows():
        computed = row["pairing_score"] * (1 - row["recipe_familiarity"]) * (1 - row["molecular_overlap"] * 0.5)
        assert abs(row["surprise_score"] - computed) < 1e-6, (
            f"surprise_score mismatch: got {row['surprise_score']:.6f}, "
            f"expected {computed:.6f} from formula"
        )


# ---------------------------------------------------------------------------
# SCORE-02: Score component ranges
# ---------------------------------------------------------------------------

def test_score_components():
    """
    SCORE-02: All score component columns must be in [0, 1].

    Uses 4 synthetic ingredients with random 128-dim embeddings.
    Expected to FAIL with NotImplementedError until Wave 1.
    """
    np.random.seed(0)
    embeddings = {
        "a": np.random.randn(128).astype(np.float32),
        "b": np.random.randn(128).astype(np.float32),
        "c": np.random.randn(128).astype(np.float32),
        "d": np.random.randn(128).astype(np.float32),
    }
    molecule_sets = {
        "a": frozenset({1, 2, 3}),
        "b": frozenset({2, 4}),
        "c": frozenset({5}),
        "d": frozenset(),
    }
    co_occurrence = {("a", "b"): 10, ("b", "c"): 3, ("a", "d"): 0}

    result_df = compute_all_pairs(embeddings, co_occurrence, molecule_sets)

    assert "pairing_score" in result_df.columns
    assert "molecular_overlap" in result_df.columns
    assert "recipe_familiarity" in result_df.columns

    assert result_df["pairing_score"].between(0, 1).all(), "pairing_score out of [0, 1]"
    assert result_df["molecular_overlap"].between(0, 1).all(), "molecular_overlap out of [0, 1]"
    assert result_df["recipe_familiarity"].between(0, 1).all(), "recipe_familiarity out of [0, 1]"


# ---------------------------------------------------------------------------
# SCORE-03: Scored pairs file existence and sort order
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not Path("model/embeddings/ingredient_embeddings.pkl").exists(),
    reason="Requires Phase 4 outputs (ingredient_embeddings.pkl not found)",
)
def test_scored_pairs_file():
    """
    SCORE-03: scored_pairs.pkl must exist and be sorted by surprise_score descending.

    SKIP until Phase 4 integration artifacts are present.
    """
    scored_path = Path("scoring/scored_pairs.pkl")
    assert scored_path.exists(), "scoring/scored_pairs.pkl not found"

    df = load_scored_pairs()
    assert isinstance(df, pd.DataFrame), "load_scored_pairs() must return a DataFrame"
    assert "surprise_score" in df.columns, "DataFrame must have surprise_score column"

    # Must be sorted descending
    assert df["surprise_score"].is_monotonic_decreasing, (
        "scored_pairs must be sorted by surprise_score descending"
    )


# ---------------------------------------------------------------------------
# SCORE-04: Label column validity
# ---------------------------------------------------------------------------

def test_labels():
    """
    SCORE-04: label column must contain only {'Surprising', 'Unexpected', 'Classic'} with no NaN.

    Expected to FAIL with NotImplementedError until Wave 1.
    """
    np.random.seed(1)
    embeddings = {
        f"ing_{i}": np.random.randn(128).astype(np.float32)
        for i in range(5)
    }
    molecule_sets = {f"ing_{i}": frozenset({i, i + 1}) for i in range(5)}
    co_occurrence = {(f"ing_{i}", f"ing_{j}"): i + j for i in range(5) for j in range(i + 1, 5)}

    result_df = compute_all_pairs(embeddings, co_occurrence, molecule_sets)

    assert "label" in result_df.columns, "DataFrame must have a label column"
    valid_labels = {"Surprising", "Unexpected", "Classic"}
    invalid = set(result_df["label"].unique()) - valid_labels
    assert not invalid, f"Invalid labels found: {invalid}"
    assert result_df["label"].notna().all(), "label column must not contain NaN"


# ---------------------------------------------------------------------------
# LEARN-02: Uncertain pairs selection
# ---------------------------------------------------------------------------

def test_uncertain_pairs(monkeypatch):
    """
    LEARN-02: get_uncertain_pairs(n) must return n dicts with pairing_score closest to 0.5.

    The result must be sorted so abs(item['pairing_score'] - 0.5) is non-decreasing.
    Uses monkeypatch to inject a synthetic scored_pairs DataFrame.
    Expected to FAIL with NotImplementedError until Wave 1.
    """
    import scoring.score as score_module

    # Build a 20-row synthetic DataFrame with pairing_score spanning [0.1, 0.9]
    pairing_scores = np.linspace(0.1, 0.9, 20)
    fake_df = pd.DataFrame({
        "ingredient_a": [f"a{i}" for i in range(20)],
        "ingredient_b": [f"b{i}" for i in range(20)],
        "pairing_score": pairing_scores,
        "surprise_score": pairing_scores * 0.5,
        "molecular_overlap": np.zeros(20),
        "recipe_familiarity": np.zeros(20),
        "label": ["Classic"] * 20,
    })

    monkeypatch.setattr(score_module, "load_scored_pairs", lambda: fake_df)

    result = get_uncertain_pairs(n=5)

    assert isinstance(result, list), "get_uncertain_pairs must return a list"
    assert len(result) == 5, f"Expected 5 items, got {len(result)}"
    assert all(isinstance(item, dict) for item in result), "Each item must be a dict"

    # Verify non-decreasing distance to 0.5
    distances = [abs(item["pairing_score"] - 0.5) for item in result]
    for i in range(len(distances) - 1):
        assert distances[i] <= distances[i + 1] + 1e-9, (
            f"Distances not non-decreasing at index {i}: {distances}"
        )
