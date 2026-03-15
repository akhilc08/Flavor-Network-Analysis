"""
Test stubs for Phase 5 active learning module (Wave 0 scaffold).

Requirements: LEARN-01, LEARN-03, LEARN-04, LEARN-05, LEARN-06

All unit tests (not guarded by skipif) are expected to FAIL with NotImplementedError
until Wave 2 implements the actual active learning logic in model/active_learning.py.
Integration tests are SKIPPED until Phase 4 artifacts are present.
"""

from pathlib import Path

import pandas as pd
import pytest
import torch

from model.active_learning import (
    submit_rating,
    is_active_learning_enabled,
    append_feedback,
    fine_tune_with_replay,
    METADATA_PATH,
    AUC_GATE,
)


# ---------------------------------------------------------------------------
# LEARN-01: Feedback CSV append
# ---------------------------------------------------------------------------

def test_feedback_csv(tmp_path):
    """
    LEARN-01: append_feedback() must write ('apple', 'chocolate', 4) to feedback.csv.

    Uses tmp_path to avoid polluting project root.
    Expected to FAIL with NotImplementedError until Wave 2.
    """
    feedback_path = tmp_path / "feedback.csv"

    # Monkeypatch FEEDBACK_PATH inside active_learning module
    import model.active_learning as al_module

    original = getattr(al_module, "FEEDBACK_PATH", None)
    al_module.FEEDBACK_PATH = feedback_path

    try:
        append_feedback("apple", "chocolate", 4)
        assert feedback_path.exists(), "feedback.csv was not created"

        df = pd.read_csv(feedback_path)
        assert len(df) >= 1, "feedback.csv must have at least one row"

        last_row = df.iloc[-1]
        assert last_row["ingredient_a"] == "apple", f"ingredient_a mismatch: {last_row['ingredient_a']}"
        assert last_row["ingredient_b"] == "chocolate", f"ingredient_b mismatch: {last_row['ingredient_b']}"
        assert int(last_row["rating"]) == 4, f"rating mismatch: {last_row['rating']}"
    finally:
        if original is not None:
            al_module.FEEDBACK_PATH = original


# ---------------------------------------------------------------------------
# LEARN-03: Fine-tune loop execution
# ---------------------------------------------------------------------------

def test_finetune_loop():
    """
    LEARN-03: fine_tune_with_replay() must run 10 epochs and return a dict.

    Uses a minimal 1-layer GATConv synthetic model (not best_model.pt) so no
    Phase 4 artifacts are required.
    Expected to FAIL with NotImplementedError until Wave 2.
    """
    from torch_geometric.nn import GATConv
    import torch.nn as nn

    class TinyGAT(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = GATConv(4, 4, heads=1, concat=False)

        def forward(self, x, edge_index):
            return self.conv(x, edge_index)

    tiny_model = TinyGAT()
    optimizer = torch.optim.Adam(tiny_model.parameters(), lr=1e-4)

    # Minimal HeteroData-like structure: just enough for fine_tune_with_replay
    from torch_geometric.data import HeteroData
    data = HeteroData()
    data["ingredient"].x = torch.randn(6, 4)
    data["ingredient", "co_occurs", "ingredient"].edge_index = torch.tensor(
        [[0, 1, 2, 3], [1, 2, 3, 4]], dtype=torch.long
    )

    feedback_pairs = [
        {"ingredient_a": "apple", "ingredient_b": "chocolate", "rating": 4},
        {"ingredient_a": "garlic", "ingredient_b": "vanilla", "rating": 1},
    ]
    replay_buffer = {
        "ingredient_pairs": [(0, 1), (2, 3), (4, 5)],
        "labels": [1, 1, 1],
    }
    val_edges = torch.tensor([[0, 1], [1, 2]], dtype=torch.long)

    result = fine_tune_with_replay(
        model=tiny_model,
        hetero_data=data,
        feedback_pairs=feedback_pairs,
        replay_buffer=replay_buffer,
        val_edges=val_edges,
        optimizer=optimizer,
        n_epochs=10,
    )

    assert isinstance(result, dict), "fine_tune_with_replay must return a dict"


# ---------------------------------------------------------------------------
# LEARN-04: Checkpoint and rescore after submit_rating
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not Path("model/embeddings/ingredient_embeddings.pkl").exists(),
    reason="Requires Phase 4 outputs (ingredient_embeddings.pkl not found)",
)
def test_checkpoint_and_rescore():
    """
    LEARN-04: submit_rating() must save a pre-finetune checkpoint before training.

    SKIP until Phase 4 integration artifacts are present.
    """
    import model.active_learning as al_module

    # Reset round counter for predictable checkpoint name
    al_module._finetune_round = 0

    submit_rating("apple", "chocolate", 4)

    checkpoint = Path("model/checkpoints/pre_finetune_round_1.pt")
    assert checkpoint.exists(), f"Pre-finetune checkpoint not found: {checkpoint}"


# ---------------------------------------------------------------------------
# LEARN-05: AUC gate check
# ---------------------------------------------------------------------------

def test_auc_gate(tmp_path, monkeypatch):
    """
    LEARN-05: is_active_learning_enabled() must check AUC >= AUC_GATE (0.70).

    (a) Returns False when training_metadata.json does not exist.
    (b) Returns False when best_val_auc = 0.65 (below gate).
    (c) Returns True  when best_val_auc = 0.75 (above gate).

    Expected to FAIL with NotImplementedError until Wave 2.
    """
    import json
    import model.active_learning as al_module

    # (a) File does not exist — use a path in tmp_path that has no file
    no_file_path = tmp_path / "no_metadata.json"
    monkeypatch.setattr(al_module, "METADATA_PATH", no_file_path)
    assert is_active_learning_enabled() is False, (
        "is_active_learning_enabled() must return False when metadata file is missing"
    )

    # (b) AUC below gate
    low_auc_path = tmp_path / "metadata_low.json"
    low_auc_path.write_text(json.dumps({"best_val_auc": 0.65}))
    monkeypatch.setattr(al_module, "METADATA_PATH", low_auc_path)
    assert is_active_learning_enabled() is False, (
        "is_active_learning_enabled() must return False when best_val_auc=0.65 < 0.70"
    )

    # (c) AUC above gate
    high_auc_path = tmp_path / "metadata_high.json"
    high_auc_path.write_text(json.dumps({"best_val_auc": 0.75}))
    monkeypatch.setattr(al_module, "METADATA_PATH", high_auc_path)
    assert is_active_learning_enabled() is True, (
        "is_active_learning_enabled() must return True when best_val_auc=0.75 >= 0.70"
    )


# ---------------------------------------------------------------------------
# LEARN-06: submit_rating return contract
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not Path("model/embeddings/ingredient_embeddings.pkl").exists(),
    reason="Requires Phase 4 outputs (ingredient_embeddings.pkl not found)",
)
def test_submit_rating_return():
    """
    LEARN-06: submit_rating() must return a dict with 'auc_before' and 'auc_after' as floats.

    SKIP until Phase 4 integration artifacts are present.
    """
    result = submit_rating("apple", "chocolate", 4)

    assert isinstance(result, dict), "submit_rating must return a dict"
    assert "auc_before" in result, "Return dict must have 'auc_before' key"
    assert "auc_after" in result, "Return dict must have 'auc_after' key"
    assert isinstance(result["auc_before"], float), "'auc_before' must be a float"
    assert isinstance(result["auc_after"], float), "'auc_after' must be a float"
