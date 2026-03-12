---
phase: 04-model-training
verified: 2026-03-12T20:00:00Z
status: gaps_found
score: 3/5 must-haves verified
gaps:
  - truth: "Best validation AUC is logged to console; checkpoint is saved only when AUC improves"
    status: failed
    reason: "Training was never executed. model/checkpoints/best_model.pt does not exist. No training_metrics.csv exists. Pipeline log shows no Phase 4 training run."
    artifacts:
      - path: "model/checkpoints/best_model.pt"
        issue: "MISSING — directory exists with only .gitkeep"
      - path: "logs/training_metrics.csv"
        issue: "MISSING — logs/ directory has only pipeline.log (Phase 1-3 output)"
    missing:
      - "Execute `python model/train_gat.py` to completion (200 epochs)"
      - "Confirm best_model.pt is written to model/checkpoints/"
      - "Confirm training_metrics.csv is written to logs/ with 200 data rows"
  - truth: "model/embeddings/ingredient_embeddings.pkl exists and contains a 128-dim vector for every ingredient in the graph"
    status: failed
    reason: "model/embeddings/ directory exists with only .gitkeep — ingredient_embeddings.pkl is absent. Training was never run so export_embeddings() was never called."
    artifacts:
      - path: "model/embeddings/ingredient_embeddings.pkl"
        issue: "MISSING — directory has .gitkeep only"
    missing:
      - "Run training end-to-end so export_embeddings() writes ingredient_embeddings.pkl"
      - "Verify pkl contains 935 string keys (one per ingredient) each mapping to np.ndarray of shape (128,)"
  - truth: "Validation AUC >= 0.70 is reached (required gate before active learning is enabled)"
    status: failed
    reason: "No training run has been executed. There is zero evidence of any AUC value achieved. This is the primary phase goal and is unverifiable without a completed training run."
    artifacts: []
    missing:
      - "Run model/train_gat.py to completion"
      - "Confirm best_auc from training_metrics.csv or console output reaches >= 0.70"
      - "If AUC < 0.70, investigate: co_occurs edge match rate is 0.6% (Phase 3 warning), which may starve recipe loss supervision signal"
human_verification:
  - test: "Run `python model/train_gat.py --epochs 200` from project root and monitor console"
    expected: "200 epoch log lines each with format 'Epoch NNN/200 | AUC: X.XXX | Loss: ...'; best_auc line at end >= 0.70; files model/checkpoints/best_model.pt, logs/training_metrics.csv, model/embeddings/ingredient_embeddings.pkl all exist after completion"
    why_human: "Requires full training run on Apple Silicon MPS — estimated hours on CPU, cannot run in static verification"
  - test: "Check training_metrics.csv after training — confirm InfoNCE loss column (nce_loss) has non-zero values distinct from mol_loss and rec_loss each epoch"
    expected: "Three separate columns with different values — not a merged total"
    why_human: "Requires the training CSV file to exist, which depends on running the model"
---

# Phase 4: Model Training Verification Report

**Phase Goal:** A trained GAT checkpoint exists that achieves validation AUC >= 0.70, with 128-dim ingredient embeddings exported and ready for scoring.
**Verified:** 2026-03-12T20:00:00Z
**Status:** GAPS FOUND
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Training completes 200 epochs without OOM crash on Apple Silicon MPS | ? UNCERTAIN | Script implements OOM handler and MPS device selection; not yet run |
| 2 | Best validation AUC is logged to console; checkpoint saved only when AUC improves | FAILED | No training run. best_model.pt absent. training_metrics.csv absent. |
| 3 | InfoNCE loss is logged as a separate component (not merged into combined loss number) | VERIFIED | train_gat.py prints `(mol=X.XXX, rec=X.XXX, nce=X.XXX)` format; CSV has separate nce_loss column |
| 4 | model/embeddings/ingredient_embeddings.pkl exists and contains a 128-dim vector for every ingredient | FAILED | File does not exist — only .gitkeep in model/embeddings/ |
| 5 | Validation AUC >= 0.70 is reached | FAILED | No training run. No AUC evidence anywhere. |

**Score:** 1/5 truths fully verified, 1 uncertain (requires human), 3 failed

---

## Required Artifacts

### Plan 04-01 Artifacts (Test Scaffold)

| Artifact | Status | Details |
|----------|--------|---------|
| `tests/test_model.py` | VERIFIED | 189 lines; 9 named test functions present (test_gat_output_shape through test_embedding_export) |
| `tests/conftest.py` | VERIFIED | tiny_hetero_graph and tiny_link_labels fixtures defined (lines 14, 74) |

### Plan 04-02 Artifacts (FlavorGAT)

| Artifact | Status | Details |
|----------|--------|---------|
| `model/gat_model.py` | VERIFIED | 158 lines; FlavorGAT class with HeteroConv, ModuleDict, BatchNorm1d, add_self_loops=False on all GATConv layers |

### Plan 04-03 Artifacts (Losses)

| Artifact | Status | Details |
|----------|--------|---------|
| `model/losses.py` | VERIFIED | 190 lines; exports molecular_bce_loss, recipe_bce_loss, info_nce_loss, combined_loss |

### Plan 04-04 Artifacts (Training Script + Outputs)

| Artifact | Status | Details |
|----------|--------|---------|
| `model/train_gat.py` | VERIFIED | 492 lines; argparse, training loop, export_embeddings, save_checkpoint, save_checkpoint_if_improved all present |
| `logs/training_metrics.csv` | MISSING | File does not exist. logs/ contains only pipeline.log from Phase 1-3. |
| `model/checkpoints/best_model.pt` | MISSING | model/checkpoints/ has only .gitkeep. No training run executed. |
| `model/embeddings/ingredient_embeddings.pkl` | MISSING | model/embeddings/ has only .gitkeep. Training never ran. |

---

## Key Link Verification

### Plan 04-02 Key Links (FlavorGAT)

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| model/gat_model.py | torch_geometric.nn.HeteroConv | HeteroConv({edge_type: GATConv(...)}) | WIRED | Line 19: `from torch_geometric.nn import HeteroConv, GATConv, Linear`; HeteroConv constructed in _build_hetero_conv() |
| model/gat_model.py | torch_geometric.nn.Linear | nn.ModuleDict per-node-type projection | WIRED | Lines 93-96 and 112-115: ModuleDict with PyG Linear(-1, hidden_channels) and Linear(hidden_channels, embed_dim) |

### Plan 04-03 Key Links (Losses)

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| model/losses.py | torch_geometric.utils.negative_sampling | negative_sampling(edge_index, num_nodes, ...) | WIRED | Line 15 import; called at line 49 in _bce_link_pred_loss |
| model/losses.py | torch.nn.functional.normalize | F.normalize(z, dim=-1) inside info_nce_loss | WIRED | Line 148: `z_norm = F.normalize(z, dim=-1)` |

### Plan 04-04 Key Links (Training Script)

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| model/train_gat.py | model/gat_model.py | from model.gat_model import FlavorGAT | WIRED | Line 38 import; used in main() at line 337 |
| model/train_gat.py | model/losses.py | from model.losses import molecular_bce_loss, recipe_bce_loss, info_nce_loss, combined_loss | WIRED | Line 39 import; all 4 called in training loop |
| model/train_gat.py | graph/hetero_data.pt | torch.load('graph/hetero_data.pt') | WIRED | Line 126; load_graph() handles missing file with sys.exit(1) |
| model/train_gat.py | model/checkpoints/best_model.pt | torch.save() when val_auc > best_auc | WIRED | Line 455: save_checkpoint called when val_auc > best_auc; BUT best_model.pt does not exist because training was never run |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| MODEL-01 | 04-01, 04-02 | GAT: 3 layers, 8 heads, 256 hidden, 128-dim embeddings | SATISFIED | gat_model.py implements; test_gat_output_shape xpassed |
| MODEL-02 | 04-01, 04-02 | GATConv add_self_loops=False on all bipartite edge types | SATISFIED | All 4 GATConv instances in _build_hetero_conv() have add_self_loops=False; test_no_self_loops xpassed |
| MODEL-03 | 04-01, 04-02 | BatchNorm1d and dropout (0.3) applied between layers | SATISFIED | self.bn ModuleDict with 6 BatchNorm1d entries; dropout_p stored; test_bn_dropout_present xpassed |
| MODEL-04 | 04-01, 04-03 | Molecular BCE loss on ingredient pairs sharing >5 molecules | SATISFIED | molecular_bce_loss() implemented; test_molecular_loss xpassed |
| MODEL-05 | 04-01, 04-03 | Recipe BCE loss on ingredient pairs co-occurring in >10 recipes | SATISFIED | recipe_bce_loss() implemented; test_recipe_loss xpassed |
| MODEL-06 | 04-01, 04-03 | InfoNCE with temperature tau starting 0.1-0.2; gradient clipping; logged separately | SATISFIED (partial) | info_nce_loss() with tau=0.15 default; clip_grad_norm_(max_norm=1.0) in train_gat.py line 406; logged separately in print format; but never executed in training |
| MODEL-07 | 04-01, 04-03, 04-04 | Combined loss: 0.4*mol + 0.4*rec + 0.2*nce; alpha/beta/gamma tunable | SATISFIED | combined_loss() implemented; argparse flags --alpha/--beta/--gamma; test_combined_loss_formula xpassed |
| MODEL-08 | 04-01, 04-04 | 200 epochs, Adam lr=1e-3, cosine LR, MPS backend; checkpoint on AUC improvement | BLOCKED | Training script is correct and importable; training was never run; no checkpoint exists |
| MODEL-09 | 04-01, 04-04 | 128-dim embeddings to model/embeddings/ingredient_embeddings.pkl | BLOCKED | export_embeddings() is correctly implemented and tested; pkl file does not exist (training never run) |

---

## Test Suite Status

All 9 tests pass when run under the flavor-network conda environment:

```
2 passed, 7 xpassed, 1 warning in 2.34s
```

- test_checkpoint_save_on_improvement: PASSED (concrete, no xfail)
- test_embedding_export: PASSED (concrete, no xfail)
- test_gat_output_shape through test_combined_loss_formula (7 tests): XPASSED (xfail decorator present but implementation works — implementations exist)

Note: The 7 xfail decorators on tests for MODEL-01 through MODEL-07 should have been removed per plan 04-04 Task 2, which only removed decorators from MODEL-08 and MODEL-09. The tests pass despite the stale decorators, but this is a minor cleanliness issue, not a blocker.

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|---------|--------|
| `model/train_gat.py` (line 134) | `_get(payload, "graph")` — expects key "graph" but Phase 3 output structure uses dict with keys: graph, val_data, ingredient_id_to_idx, molecule_id_to_idx | Warning | If Phase 3 saved the payload with a different key name this will KeyError at training start — needs runtime verification |

---

## Human Verification Required

### 1. Execute Full Training Run

**Test:** Run `python model/train_gat.py --epochs 200` from project root (with flavor-network conda env active)
**Expected:** 200 epoch log lines; final line "Training complete | Best AUC: X.XXXX @ epoch N"; three artifact files created: `model/checkpoints/best_model.pt`, `logs/training_metrics.csv`, `model/embeddings/ingredient_embeddings.pkl`
**Why human:** Requires actual model training on Apple Silicon — hours on CPU, cannot run in static verification

### 2. Confirm AUC >= 0.70 Gate

**Test:** After training, check `logs/training_metrics.csv` for the maximum `val_auc` value
**Expected:** max(val_auc) >= 0.70 across all 200 epochs
**Why human:** Depends on data quality from Phases 1-3; the 0.6% co-occurrence match rate warning from Phase 3 may starve the recipe supervision signal and depress AUC
**Fallback if AUC < 0.70:** Investigate co_occurs edge_attr assignment in build_graph.py; may need to lower --recipe-threshold or --mol-threshold

### 3. Verify ingredient_embeddings.pkl Integrity

**Test:** After training, run:
```python
import pickle
with open('model/embeddings/ingredient_embeddings.pkl', 'rb') as f:
    emb = pickle.load(f)
assert len(emb) == 935  # from Phase 3: 935 ingredients
assert all(v.shape == (128,) for v in emb.values())
```
**Expected:** 935 string keys, each value a numpy array of shape (128,)
**Why human:** File does not yet exist

---

## Gaps Summary

The phase produced complete, high-quality source code for all four model components (FlavorGAT, losses, training script, test scaffold). All 9 unit tests pass. All key wiring links are present. The training script is correct and importable.

However, the phase goal is explicitly a runtime outcome: "A **trained** GAT checkpoint exists that achieves validation AUC >= 0.70, with 128-dim ingredient embeddings **exported and ready** for scoring." None of the three runtime artifacts required by that goal exist:

1. `model/checkpoints/best_model.pt` — MISSING
2. `logs/training_metrics.csv` — MISSING
3. `model/embeddings/ingredient_embeddings.pkl` — MISSING

The pipeline log shows Phase 3 completing at 00:41:59 on 2026-03-12 and no subsequent Phase 4 training invocation. The SUMMARY for plan 04-04 documents completion of the training script implementation but does not document an actual training run or AUC result.

**Root cause:** Phase 4 was declared complete after implementing the training infrastructure without actually running training to produce the required artifacts. This is a gap between task completion ("write train_gat.py") and goal achievement ("trained checkpoint with AUC >= 0.70 exists").

**Resolution:** Execute `python model/train_gat.py` to completion. If AUC fails to reach 0.70, debug the co_occurs supervision signal (Phase 3 WARNING: 0.6% name match rate) before re-running.

---

_Verified: 2026-03-12T20:00:00Z_
_Verifier: Claude (gsd-verifier)_
