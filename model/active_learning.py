"""
model/active_learning.py — Active learning stubs for Phase 5.

Public API (locked — Phase 6 imports these):
    submit_rating(ingredient_a, ingredient_b, rating) -> dict
    is_active_learning_enabled() -> bool

Internal helpers (exported for unit testing):
    append_feedback(ingredient_a, ingredient_b, rating) -> None
    fine_tune_with_replay(model, hetero_data, feedback_pairs, replay_buffer, val_edges, optimizer, n_epochs=10) -> dict

Module-level constants:
    METADATA_PATH: Path to model/training_metadata.json (monkeypatchable in tests)
    AUC_GATE: float — minimum best_val_auc required to enable active learning (0.70)
    FEEDBACK_PATH: Path to feedback.csv (monkeypatchable in tests)

Phase 4 boundary artifacts:
    graph/val_edges.pt and model/training_metadata.json
    Missing artifacts log a WARNING (not raise) inside check_phase4_artifacts().
    check_phase4_artifacts() is called inside submit_rating() before fine-tuning.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants (monkeypatchable for unit testing)
# ---------------------------------------------------------------------------

METADATA_PATH: Path = Path("model/training_metadata.json")
AUC_GATE: float = 0.70
FEEDBACK_PATH: Path = Path("feedback.csv")

# Internal state: tracks how many fine-tune rounds have been completed
_finetune_round: int = 0


# ---------------------------------------------------------------------------
# Phase 4 boundary check
# ---------------------------------------------------------------------------

def check_phase4_artifacts() -> None:
    """
    Warn (do not raise) if Phase 4 boundary artifacts are missing.

    Called inside submit_rating() before fine-tuning begins.
    """
    for artifact in [Path("graph/val_edges.pt"), METADATA_PATH]:
        if not artifact.exists():
            logger.warning(
                "Phase 4 artifact missing: %s — active learning may degrade gracefully.",
                artifact,
            )


# ---------------------------------------------------------------------------
# Internal helpers (exported for unit testing)
# ---------------------------------------------------------------------------

def append_feedback(ingredient_a: str, ingredient_b: str, rating: int) -> None:
    """
    Append a user rating to feedback.csv.

    Creates the file with a header row if it does not exist.
    Appends a row {ingredient_a, ingredient_b, rating} atomically.

    Args:
        ingredient_a: First ingredient name.
        ingredient_b: Second ingredient name.
        rating:       Integer rating (1–5 scale).

    Raises:
        NotImplementedError: until Wave 2 implementation.
    """
    raise NotImplementedError(
        "append_feedback() is not yet implemented — Wave 2 task (LEARN-01)"
    )


def fine_tune_with_replay(
    model,
    hetero_data,
    feedback_pairs: list[dict],
    replay_buffer: dict,
    val_edges,
    optimizer,
    n_epochs: int = 10,
) -> dict:
    """
    Fine-tune the model with experience replay to prevent catastrophic forgetting.

    Experience replay explanation: GNN weight updates shift embeddings globally.
    Replaying a buffer of high-quality training pairs alongside new feedback
    prevents the model from forgetting learned flavor relationships when adapting
    to user preferences (catastrophic forgetting mitigation).

    Args:
        model:          A PyTorch GNN model (e.g., FlavorGAT) already loaded.
        hetero_data:    HeteroData graph used during Phase 4 training.
        feedback_pairs: List of dicts {ingredient_a, ingredient_b, rating} from user.
        replay_buffer:  Dict {ingredient_pairs: [(a_idx, b_idx), ...], labels: [1, ...]}.
                        If missing or empty, fine-tunes on feedback_pairs only.
        val_edges:      Validation edge index tensor for AUC computation.
        optimizer:      Optimizer for model parameters (LR should be ~1e-4, 10× lower than base).
        n_epochs:       Number of fine-tune epochs (default 10).

    Returns:
        Dict with at minimum {"val_auc": float} — AUC after fine-tuning.

    Raises:
        NotImplementedError: until Wave 2 implementation.
    """
    raise NotImplementedError(
        "fine_tune_with_replay() is not yet implemented — Wave 2 task (LEARN-03)"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def submit_rating(ingredient_a: str, ingredient_b: str, rating: int) -> dict:
    """
    Accept a user rating, trigger fine-tuning, and return AUC delta.

    Workflow:
        1. check_phase4_artifacts() — warn if Phase 4 outputs missing.
        2. append_feedback(ingredient_a, ingredient_b, rating).
        3. Load best_model.pt, replay_buffer.pkl, and val_edges.pt.
        4. Save pre-finetune checkpoint to model/checkpoints/pre_finetune_round_{N}.pt.
        5. Compute AUC before fine-tuning.
        6. fine_tune_with_replay() for 10 epochs.
        7. Full re-score: overwrite scoring/scored_pairs.pkl.
        8. Return {"auc_before": float, "auc_after": float}.

    Args:
        ingredient_a: First ingredient name.
        ingredient_b: Second ingredient name.
        rating:       Integer rating (1–5 scale).

    Returns:
        Dict with keys "auc_before" and "auc_after" as floats.

    Raises:
        NotImplementedError: until Wave 2 implementation.
    """
    check_phase4_artifacts()
    raise NotImplementedError(
        "submit_rating() is not yet implemented — Wave 2 task (LEARN-04, LEARN-06)"
    )


def is_active_learning_enabled() -> bool:
    """
    Check whether the active learning loop should be enabled.

    Returns True only if:
        - model/training_metadata.json exists, and
        - best_val_auc in that file is >= AUC_GATE (0.70).

    Uses METADATA_PATH module constant (monkeypatchable for unit testing).

    Args:
        None

    Returns:
        bool — True if active learning is enabled, False otherwise.

    Raises:
        NotImplementedError: until Wave 2 implementation.
    """
    raise NotImplementedError(
        "is_active_learning_enabled() is not yet implemented — Wave 2 task (LEARN-05)"
    )
