---
phase: 04-model-training
plan: "04"
subsystem: training
tags: [pytorch, torch-geometric, gat, argparse, tqdm, sklearn, csv-logging, checkpointing, embeddings]

# Dependency graph
requires:
  - phase: 04-02
    provides: FlavorGAT HeteroConv model with forward() returning ingredient/molecule embeddings
  - phase: 04-03
    provides: molecular_bce_loss, recipe_bce_loss, info_nce_loss, combined_loss
  - phase: 03-04
    provides: graph/hetero_data.pt with train/val/test HeteroData splits and index maps
provides:
  - model/train_gat.py: complete end-to-end training script
  - save_checkpoint / save_checkpoint_if_improved: importable checkpoint helpers
  - export_embeddings: CPU-first ingredient embedding export to pkl
  - logs/training_metrics.csv: per-epoch CSV logging (epoch, mol_loss, rec_loss, nce_loss, total_loss, val_auc, lr)
  - model/checkpoints/best_model.pt: saved on AUC improvement
  - model/embeddings/ingredient_embeddings.pkl: 128-dim numpy array per ingredient ID
affects:
  - phase-05-scoring
  - phase-06-api

# Tech tracking
tech-stack:
  added: [sklearn.metrics.roc_auc_score, tqdm, csv.DictWriter, torch.optim.lr_scheduler.CosineAnnealingLR]
  patterns:
    - argparse with all 12 hyperparameter flags and locked defaults
    - CPU-first embedding export to avoid MPS double-spike OOM
    - save_checkpoint_if_improved returns bool for testability
    - OOM handler wrapping epoch block with torch.mps.empty_cache() and clean exit
    - sys.path.insert(0, PROJECT_ROOT) for direct script invocation from project root

key-files:
  created:
    - model/train_gat.py
  modified:
    - tests/test_model.py (removed xfail from MODEL-08, MODEL-09)

key-decisions:
  - "train_gat.py adds project root to sys.path so python model/train_gat.py works without PYTHONPATH"
  - "save_checkpoint_if_improved wraps the conditional logic and returns bool — makes MODEL-08 test clean without manual if-guards in test body"
  - "export_embeddings moves both data and model to CPU before forward pass — prevents MPS OOM from double-resident tensors during embedding export"
  - "torch.compile wrapped in try/except RuntimeError — silently disabled on MPS without failing the run"

patterns-established:
  - "CPU-first pattern for GPU->CPU tensor extraction: model.to('cpu') then forward, then model.to(device)"
  - "Checkpoint dict structure: model_state_dict, optimizer_state_dict, scheduler_state_dict, epoch, best_auc"
  - "Per-epoch log format: Epoch 045/200 | AUC: 0.742up | Loss: 0.312 (mol=0.128, rec=0.115, nce=0.069) | LR: 8.3e-4"

requirements-completed: [MODEL-07, MODEL-08, MODEL-09]

# Metrics
duration: 15min
completed: 2026-03-12
---

# Phase 4 Plan 04: Training Script Summary

**Complete FlavorGAT end-to-end training script with argparse, CosineAnnealingLR, per-epoch CSV logging, best+periodic checkpointing, and CPU-first ingredient embedding export to pkl.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-12T18:10:00Z
- **Completed:** 2026-03-12T18:25:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Implemented `model/train_gat.py` (330 lines): argparse entry point, `get_device()`, `load_graph()`, `build_pos_edge_index()`, `evaluate()`, `export_embeddings()`, `save_checkpoint()`, `save_checkpoint_if_improved()`, and `main()` training loop
- `save_checkpoint_if_improved()` returns bool — MODEL-08 test passes concretely without xfail
- `export_embeddings()` moves model+data to CPU before inference — MODEL-09 test passes concretely without xfail
- All 9 model tests pass (2 concretely, 7 xpassed from prior plans)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement training loop with checkpoint management** - `043bb3a` (feat)
2. **Task 2: Green the remaining test stubs** - `40b12ff` (feat)

## Files Created/Modified

- `/Users/sickle/Coding/Flavor-Network-Analysis/model/train_gat.py` - Full training script with argparse, training loop, checkpoint logic, embedding export
- `/Users/sickle/Coding/Flavor-Network-Analysis/tests/test_model.py` - Removed xfail decorators from test_checkpoint_save_on_improvement and test_embedding_export

## Decisions Made

- `save_checkpoint_if_improved()` added as a higher-level wrapper (vs just `save_checkpoint`) so the test can call it without duplicating the conditional — the existing test stub's API was authoritative and used this signature, not the plan's Task 2 code sample
- `sys.path.insert(0, PROJECT_ROOT)` added to the script header so `python model/train_gat.py --help` works when invoked directly from project root without PYTHONPATH set
- `torch.compile` call wrapped in `try/except RuntimeError` — disabled silently on MPS/CPU backends that don't support it

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used existing test API (save_checkpoint_if_improved) not plan's Task 2 code sample**
- **Found during:** Task 2 (Green test stubs)
- **Issue:** Existing test stubs used `save_checkpoint_if_improved(state, current_auc, best_auc, path)` returning bool. Plan's Task 2 code sample showed a different test calling `save_checkpoint()` with manual conditional. The existing stubs are authoritative.
- **Fix:** Implemented `save_checkpoint_if_improved()` with the existing test's exact signature. Also kept `save_checkpoint()` as a thin wrapper used internally.
- **Files modified:** model/train_gat.py
- **Verification:** MODEL-08 test passes concretely
- **Committed in:** 043bb3a (Task 1 commit)

**2. [Rule 3 - Blocking] Added sys.path fix for direct script invocation**
- **Found during:** Task 1 verification (`python model/train_gat.py --help`)
- **Issue:** `from model.gat_model import FlavorGAT` fails when script is invoked directly (not as module) because project root is not on sys.path
- **Fix:** Added `sys.path.insert(0, Path(__file__).parent.parent)` at script top
- **Files modified:** model/train_gat.py
- **Verification:** `python model/train_gat.py --help` shows all 12+ flags
- **Committed in:** 043bb3a (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 API alignment, 1 blocking import fix)
**Impact on plan:** Both essential for test correctness and script usability. No scope creep.

## Issues Encountered

- Pre-existing `tests/test_foodb.py::test_join_count` failure (molecules.csv missing `foodb_matched` column from Phase 1 pipeline). This is out of scope — logged to deferred items. All Phase 4 model tests pass cleanly.

## Next Phase Readiness

- Phase 4 complete: FlavorGAT architecture (04-02), loss functions (04-03), and training script (04-04) all implemented and tested
- `python model/train_gat.py` will train end-to-end when `graph/hetero_data.pt` is available
- Phase 5 (scoring/recommendations) can consume `model/embeddings/ingredient_embeddings.pkl` directly

---
*Phase: 04-model-training*
*Completed: 2026-03-12*
