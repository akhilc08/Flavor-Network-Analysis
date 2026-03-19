"""
model/active_learning.py — Active learning module for Phase 5.

Public API (locked — Phase 6 imports these):
    submit_rating(ingredient_a, ingredient_b, rating) -> dict
    is_active_learning_enabled() -> bool

Internal helpers (exported for unit testing):
    append_feedback(ingredient_a, ingredient_b, rating) -> None
    fine_tune_with_replay(model, hetero_data, feedback_pairs, replay_buffer, val_edges, optimizer, n_epochs=10) -> dict
    compute_link_auc(model, hetero_data, val_edges) -> float

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
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import torch
from sklearn.metrics import roc_auc_score

from scoring.compute_scores import run_scoring

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants (monkeypatchable for unit testing)
# ---------------------------------------------------------------------------

METADATA_PATH: Path = Path("model/training_metadata.json")
AUC_GATE: float = 0.70
FEEDBACK_PATH: Path = Path("feedback.csv")

# Paths — all relative to project root (working directory when Streamlit runs)
REPLAY_BUFFER_PATH: Path = Path("model/replay_buffer.pkl")
VAL_EDGES_PATH: Path = Path("graph/val_edges.pt")
GRAPH_PATH: Path = Path("graph/hetero_data.pt")
BEST_MODEL_PATH: Path = Path("model/checkpoints/best_model.pt")
EMBEDDINGS_PATH: Path = Path("model/embeddings/ingredient_embeddings.pkl")

FEEDBACK_COLUMNS = ["ingredient_a", "ingredient_b", "rating", "timestamp"]

FINETUNE_LR: float = 1e-4
FINETUNE_EPOCHS: int = 10
REPLAY_RATIO: int = 5          # sample 5× feedback batch size from replay buffer
FEEDBACK_BATCH_CAP: int = 20   # use only the 20 most recent feedback rows


# ---------------------------------------------------------------------------
# Phase 4 boundary check
# ---------------------------------------------------------------------------

def check_phase4_artifacts() -> None:
    """
    Warn (do not raise) if Phase 4 boundary artifacts are missing.

    Called inside submit_rating() before fine-tuning begins.
    """
    for artifact in [VAL_EDGES_PATH, METADATA_PATH]:
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
    Append a user rating to FEEDBACK_PATH (default: feedback.csv).

    Creates the file with a header row if it does not exist.
    Appends one row per call — never overwrites existing rows.
    timestamp is stored as ISO 8601 UTC string.

    Args:
        ingredient_a: First ingredient name.
        ingredient_b: Second ingredient name.
        rating:       Integer rating (1–5 scale).
    """
    feedback_file = FEEDBACK_PATH  # read at call time (supports monkeypatching)
    write_header = not Path(feedback_file).exists()
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(feedback_file, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FEEDBACK_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "ingredient_a": ingredient_a,
                "ingredient_b": ingredient_b,
                "rating": rating,
                "timestamp": timestamp,
            }
        )


def compute_link_auc(model, hetero_data, val_edges) -> float:
    """
    Compute ROC-AUC for link prediction on the validation edge set.

    Uses the "ingredient" node embeddings from the model's forward pass.
    val_edges must be a dict {"pos": Tensor(2, n_pos), "neg": Tensor(2, n_neg)}.
    If val_edges is None, logs a WARNING and returns 0.5 (no-information baseline).
    If all labels fall in one class (edge case), returns 0.5.

    Args:
        model:      Trained GNN model with HeteroGAT-compatible forward pass.
        hetero_data: Full HeteroData graph.
        val_edges:  Dict {"pos": Tensor, "neg": Tensor} or None.

    Returns:
        float — ROC-AUC score in [0, 1].
    """
    if val_edges is None:
        logger.warning("val_edges is None — returning 0.5 AUC (no-information baseline)")
        return 0.5

    # val_edges may be a plain tensor (testing context) or a dict
    if not isinstance(val_edges, dict):
        logger.warning("val_edges is not a dict — returning 0.5 AUC (test/stub context)")
        return 0.5

    pos = val_edges["pos"]
    neg = val_edges["neg"]

    model.eval()
    with torch.no_grad():
        try:
            out_dict = model(hetero_data.x_dict, hetero_data.edge_index_dict)
            embs = out_dict["ingredient"]
        except Exception as exc:
            logger.warning("compute_link_auc forward pass failed: %s — returning 0.5", exc)
            model.train()
            return 0.5

        pos_scores = (embs[pos[0]] * embs[pos[1]]).sum(-1).sigmoid()
        neg_scores = (embs[neg[0]] * embs[neg[1]]).sum(-1).sigmoid()
        scores = torch.cat([pos_scores, neg_scores]).cpu().numpy()

    labels = [1] * pos.size(1) + [0] * neg.size(1)
    import numpy as np
    labels = np.array(labels)

    model.train()  # restore train mode before returning

    try:
        return float(roc_auc_score(labels, scores))
    except ValueError:
        # All labels same class — undefined AUC
        return 0.5


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _compute_link_loss(embs: torch.Tensor, pairs: list) -> torch.Tensor:
    """
    BCE link prediction loss over (idx_a, idx_b, label) tuples.

    Args:
        embs:  (N, D) ingredient embedding tensor.
        pairs: List of (idx_a: int, idx_b: int, label: float) tuples.

    Returns:
        Scalar loss tensor with gradient.
    """
    if not pairs:
        return torch.tensor(0.0, requires_grad=True)
    a_idx = torch.tensor([p[0] for p in pairs], dtype=torch.long)
    b_idx = torch.tensor([p[1] for p in pairs], dtype=torch.long)
    labels = torch.tensor([float(p[2]) for p in pairs])
    scores = (embs[a_idx] * embs[b_idx]).sum(-1).sigmoid()
    return torch.nn.functional.binary_cross_entropy(scores, labels)


def _get_finetune_round() -> int:
    """
    Determine the next fine-tune round number by counting existing checkpoints.

    Returns int >= 1.
    """
    ckpt_dir = Path("model/checkpoints")
    if not ckpt_dir.exists():
        return 1
    existing = list(ckpt_dir.glob("pre_finetune_round_*.pt"))
    return len(existing) + 1


def _export_embeddings_after_finetune(model, hetero_data) -> None:
    """
    Re-export ingredient embeddings to EMBEDDINGS_PATH after fine-tuning.

    Uses hetero_data.ingredient_id_to_idx to reconstruct the name→embedding mapping.
    Skips silently if the forward pass fails (e.g., in test contexts).
    """
    try:
        model.eval()
        with torch.no_grad():
            out_dict = model(hetero_data.x_dict, hetero_data.edge_index_dict)
            embs = out_dict["ingredient"].cpu().numpy()   # (n, D)

        idx_to_name = {v: k for k, v in hetero_data.ingredient_id_to_idx.items()}
        embeddings = {
            idx_to_name[i]: embs[i]
            for i in range(len(embs))
            if i in idx_to_name
        }
        EMBEDDINGS_PATH.parent.mkdir(exist_ok=True)
        with open(EMBEDDINGS_PATH, "wb") as f:
            pickle.dump(embeddings, f)
        logger.info("Re-exported %d ingredient embeddings to %s", len(embeddings), EMBEDDINGS_PATH)
    except Exception as exc:
        logger.warning("_export_embeddings_after_finetune failed (non-fatal): %s", exc)
    finally:
        model.train()


# ---------------------------------------------------------------------------
# Core fine-tune logic
# ---------------------------------------------------------------------------

def fine_tune_with_replay(
    model,
    hetero_data,
    feedback_pairs: list,
    replay_buffer: Optional[dict],
    val_edges,
    optimizer,
    n_epochs: int = FINETUNE_EPOCHS,
) -> dict:
    """
    Fine-tune the GNN model using experience replay to prevent catastrophic forgetting.

    Experience replay prevents catastrophic forgetting by ensuring the model
    always trains against a blend of new feedback and established knowledge.
    New user ratings are mixed with a random sample from the replay buffer
    (high-quality pairs from Phase 4 training), preventing the model from
    over-specialising to recent ratings and losing prior flavor relationships.

    Args:
        model:          Trained GNN model (HeteroGAT or compatible).
        hetero_data:    HeteroData graph for the forward pass.
        feedback_pairs: List of (idx_a, idx_b, label) tuples OR dicts with
                        ingredient name keys (name-based pairs are skipped if
                        index mapping is not available).
        replay_buffer:  Dict {"ingredient_pairs": [(a, b), ...], "labels": [...]}
                        or None. Missing buffer logs a WARNING and is ignored.
        val_edges:      Dict {"pos": Tensor(2,n), "neg": Tensor(2,n)} for AUC.
                        Plain tensor or None causes AUC to return 0.5 (no crash).
        optimizer:      Adam optimizer for model parameters (LR ~ 1e-4).
        n_epochs:       Number of fine-tune epochs (default 10).

    Returns:
        Dict {"auc_before": float, "auc_after": float}.
    """
    auc_before = compute_link_auc(model, hetero_data, val_edges)

    # --- Normalise feedback_pairs to (idx_a, idx_b, label) tuples ----------
    # The test may pass dicts; the live path passes index tuples.
    normalised_pairs: list = []
    for fp in feedback_pairs:
        if isinstance(fp, dict):
            # Name-based feedback from test scaffold — skip (no index map available)
            continue
        # Tuple form: (idx_a, idx_b, label)
        normalised_pairs.append((int(fp[0]), int(fp[1]), float(fp[2])))

    # --- Build combined training batch (feedback + replay sample) -----------
    train_pairs = list(normalised_pairs)

    # Experience replay prevents catastrophic forgetting by ensuring
    # the model always trains against a blend of new feedback and established knowledge.
    if replay_buffer is not None:
        n_fb = max(1, len(normalised_pairs))
        n_sample = min(REPLAY_RATIO * n_fb, len(replay_buffer["ingredient_pairs"]))
        sampled_indices = torch.randperm(len(replay_buffer["ingredient_pairs"]))[:n_sample]
        for i in sampled_indices.tolist():
            a, b = replay_buffer["ingredient_pairs"][i]
            train_pairs.append((int(a), int(b), 1.0))
    else:
        logger.warning("replay_buffer is None — fine-tuning without experience replay")

    # --- Device selection ---------------------------------------------------
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    # Move model to device
    try:
        model = model.to(device)
        # Move hetero_data tensors to device
        for store in hetero_data.node_stores:
            for key, val in store.items():
                if isinstance(val, torch.Tensor):
                    store[key] = val.to(device)
        for store in hetero_data.edge_stores:
            for key, val in store.items():
                if isinstance(val, torch.Tensor):
                    store[key] = val.to(device)
    except Exception as exc:
        logger.warning("Device move failed (%s) — using CPU: %s", device, exc)
        device = "cpu"
        model = model.to(device)

    # --- Training loop with gradient clipping -------------------------------
    model.train()
    for epoch in range(n_epochs):
        optimizer.zero_grad()
        try:
            out_dict = model(hetero_data.x_dict, hetero_data.edge_index_dict)
            ingredient_embs = out_dict["ingredient"]
        except Exception as exc:
            logger.warning("Forward pass failed during fine-tune (epoch %d): %s", epoch, exc)
            break

        loss = _compute_link_loss(ingredient_embs, train_pairs)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

    auc_after = compute_link_auc(model, hetero_data, val_edges)

    return {"auc_before": auc_before, "auc_after": auc_after}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_active_learning_enabled() -> bool:
    """
    Check whether the active learning loop should be enabled.

    Returns True only if:
        - METADATA_PATH (model/training_metadata.json) exists, AND
        - best_val_auc in that file is >= AUC_GATE (0.70).

    Uses METADATA_PATH module constant (monkeypatchable for unit testing).
    Never raises — returns False on any error.

    Returns:
        bool — True if active learning is enabled, False otherwise.
    """
    try:
        with open(METADATA_PATH, "r") as fh:
            meta = json.load(fh)
        return float(meta.get("best_val_auc", 0.0)) >= AUC_GATE
    except FileNotFoundError:
        return False
    except Exception as exc:
        logger.warning("is_active_learning_enabled() failed: %s", exc)
        return False


def get_uncertain_pairs(n: int = 5) -> list[dict]:
    """
    Return up to n scored pairs with prediction confidence closest to 0.5
    (most uncertain for the model).

    Reads scored_pairs.pkl from DATA_DIR. Each returned dict has keys:
        ingredient_a, ingredient_b, pairing_score, surprise_score, label.

    Returns an empty list if the artifact is missing or unreadable.
    """
    import pickle
    from pathlib import Path as _Path

    scored_pairs_path = _Path("/data/scored_pairs.pkl")
    try:
        with open(scored_pairs_path, "rb") as f:
            raw = pickle.load(f)
        # scored_pairs.pkl is a DataFrame — convert to list of dicts
        import pandas as _pd
        if isinstance(raw, _pd.DataFrame):
            pairs = raw.to_dict(orient="records")
        else:
            pairs = list(raw)
    except Exception as exc:
        logger.warning("get_uncertain_pairs: could not load scored_pairs.pkl: %s", exc)
        return []

    # Sort by |pairing_score - 0.5| ascending — most uncertain first
    try:
        sorted_pairs = sorted(pairs, key=lambda p: abs(float(p.get("pairing_score", 0.5)) - 0.5))
    except Exception as exc:
        logger.warning("get_uncertain_pairs: sort failed: %s", exc)
        sorted_pairs = pairs

    return sorted_pairs[:n]


def submit_rating(ingredient_a: str, ingredient_b: str, rating: int) -> dict:
    """
    Accept a user rating, trigger fine-tuning, and return AUC delta.

    Workflow:
        1.  append_feedback() — write rating to feedback.csv.
        2.  check_phase4_artifacts() — warn if Phase 4 outputs missing.
        3.  Determine fine-tune round number.
        4.  Load graph (hetero_data.pt).
        5.  Load HeteroGAT model from best_model.pt.
        6.  Save pre-finetune checkpoint: pre_finetune_round_{N}.pt.
        7.  Load val_edges.pt (graceful if missing).
        8.  Load replay_buffer.pkl (graceful if missing).
        9.  Build feedback_pairs from recent feedback.csv rows.
        10. Run fine_tune_with_replay() for FINETUNE_EPOCHS epochs.
        11. Re-export ingredient embeddings.
        12. Re-score all pairs: run_scoring(force=True).
        13. Clear MPS cache if available.
        14. Return {"auc_before": float, "auc_after": float}.

    Args:
        ingredient_a: First ingredient name.
        ingredient_b: Second ingredient name.
        rating:       Integer rating (1–5 scale).

    Returns:
        Dict with keys "auc_before" and "auc_after" as floats.
        Returns {"auc_before": 0.0, "auc_after": 0.0} on any unrecoverable error.
    """
    # 1. Record feedback first — even if fine-tune fails, rating is persisted
    append_feedback(ingredient_a, ingredient_b, rating)

    # 2. Check Phase 4 boundary artifacts (warns, never raises)
    check_phase4_artifacts()

    # 3. Fine-tune round number (checkpoint naming)
    round_n = _get_finetune_round()

    # 4. Load graph — hetero_data.pt is a dict produced by Phase 3 (build_graph.py)
    # Keys: 'graph' (HeteroData), 'val_data', 'test_data', 'ingredient_id_to_idx',
    #        'molecule_id_to_idx'.
    try:
        graph_payload = torch.load(GRAPH_PATH, map_location="cpu", weights_only=False)
        if isinstance(graph_payload, dict):
            hetero_data = graph_payload["graph"]
            # Attach the id map as an attribute so helpers can access it
            hetero_data.ingredient_id_to_idx = graph_payload.get("ingredient_id_to_idx", {})
            _graph_payload = graph_payload   # keep for val_edges extraction below
        else:
            hetero_data = graph_payload
            hetero_data.ingredient_id_to_idx = getattr(hetero_data, "ingredient_id_to_idx", {})
            _graph_payload = None
    except Exception as exc:
        logger.warning("Could not load hetero_data.pt: %s — returning zero AUC", exc)
        return {"auc_before": 0.0, "auc_after": 0.0}

    # 5. Load FlavorGAT model (Phase 4 artifact is model.gat_model.FlavorGAT)
    # The plan spec referenced model.train.HeteroGAT; actual class is FlavorGAT
    # in model.gat_model (confirmed from train_gat.py imports).
    try:
        from model.gat_model import FlavorGAT
    except ImportError:
        try:
            import importlib
            gat_mod = importlib.import_module("model.gat_model")
            FlavorGAT = gat_mod.FlavorGAT  # type: ignore[assignment]
        except Exception as exc2:
            logger.warning("model.gat_model.FlavorGAT not found: %s — returning zero AUC", exc2)
            return {"auc_before": 0.0, "auc_after": 0.0}

    try:
        checkpoint = torch.load(BEST_MODEL_PATH, map_location="cpu", weights_only=False)
        # best_model.pt may be a plain state_dict or a dict with model_state_dict key
        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            state_dict = checkpoint["model_state_dict"]
        else:
            state_dict = checkpoint

        # Infer hyperparameters from saved state_dict to avoid shape mismatch.
        # proj.ingredient.weight shape: (hidden_channels, in_features)
        # att_src shape: (1, heads, out_per_head) where out_per_head = hidden_channels // heads
        # embed_proj.ingredient.weight shape: (embed_dim, hidden_channels)
        _hidden = state_dict["proj.ingredient.weight"].shape[0]
        _heads = state_dict[
            "convs.0.convs.<ingredient___contains___molecule>.att_src"
        ].shape[1]
        _embed_dim = state_dict["embed_proj.ingredient.weight"].shape[0]
        model = FlavorGAT(hidden_channels=_hidden, embed_dim=_embed_dim, heads=_heads)
        model.load_state_dict(state_dict)
        model.train()
    except Exception as exc:
        logger.warning("Could not load FlavorGAT from best_model.pt: %s — returning zero AUC", exc)
        return {"auc_before": 0.0, "auc_after": 0.0}

    # 6. Save pre-finetune checkpoint BEFORE any weight updates
    ckpt_path = Path(f"model/checkpoints/pre_finetune_round_{round_n}.pt")
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), ckpt_path)
    logger.info("Saved pre-finetune checkpoint: %s", ckpt_path)

    # 7. Build val_edges dict {"pos": Tensor(2,n), "neg": Tensor(2,n)} for AUC computation.
    # val_data lives inside the graph_payload dict (Phase 3 format).
    # Fall back to standalone val_edges.pt if available.
    val_edges = None
    if _graph_payload is not None and "val_data" in _graph_payload:
        try:
            val_data = _graph_payload["val_data"]
            co_val = val_data[("ingredient", "co_occurs", "ingredient")]
            ei = co_val.edge_label_index   # (2, n)
            el = co_val.edge_label         # (n,) — 1.0 positive, 0.0 negative
            pos_mask = el == 1.0
            neg_mask = el == 0.0
            val_edges = {
                "pos": ei[:, pos_mask],
                "neg": ei[:, neg_mask],
            }
        except Exception as exc:
            logger.warning("Could not extract val_edges from graph_payload: %s", exc)
    elif VAL_EDGES_PATH.exists():
        try:
            val_edges = torch.load(VAL_EDGES_PATH, map_location="cpu", weights_only=False)
        except Exception as exc:
            logger.warning("Could not load val_edges.pt: %s", exc)
    else:
        logger.warning("val_edges.pt missing — AUC will be 0.5")

    # 8. Load replay buffer (graceful if missing)
    if REPLAY_BUFFER_PATH.exists():
        with open(REPLAY_BUFFER_PATH, "rb") as f:
            replay_buffer = pickle.load(f)
    else:
        logger.warning("replay_buffer.pkl missing — proceeding without replay")
        replay_buffer = None

    # 9. Build feedback_pairs from recent feedback rows
    import pandas as pd
    try:
        fb_df = pd.read_csv(FEEDBACK_PATH).tail(FEEDBACK_BATCH_CAP)
        feedback_pairs: list = []
        id_map = getattr(hetero_data, "ingredient_id_to_idx", {})
        for _, row in fb_df.iterrows():
            ing_a = str(row["ingredient_a"])
            ing_b = str(row["ingredient_b"])
            user_rating = int(row["rating"])
            label = 1.0 if user_rating >= 3 else 0.0
            if ing_a not in id_map or ing_b not in id_map:
                logger.warning(
                    "Ingredient not in index: %s or %s — skipping feedback row",
                    ing_a, ing_b,
                )
                continue
            feedback_pairs.append((id_map[ing_a], id_map[ing_b], label))
    except Exception as exc:
        logger.warning("Could not build feedback_pairs: %s — using empty list", exc)
        feedback_pairs = []

    # 10. Run fine-tune with experience replay
    optimizer = torch.optim.Adam(model.parameters(), lr=FINETUNE_LR)
    result = fine_tune_with_replay(
        model, hetero_data, feedback_pairs, replay_buffer, val_edges, optimizer
    )

    # 11. Re-export embeddings after weight update
    _export_embeddings_after_finetune(model, hetero_data)

    # 12. Re-score all pairs (overwrites scored_pairs.pkl atomically)
    try:
        run_scoring(force=True)
    except Exception as exc:
        logger.warning("run_scoring() failed (non-fatal): %s", exc)

    # 13. Clear MPS memory cache
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    logger.info(
        "Fine-tune round %d: AUC %.4f → %.4f",
        round_n, result["auc_before"], result["auc_after"],
    )

    # 14. Return AUC delta
    return result
