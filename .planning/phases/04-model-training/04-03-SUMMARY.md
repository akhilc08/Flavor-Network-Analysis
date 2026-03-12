---
phase: 04-model-training
plan: 03
subsystem: model
tags: [pytorch, torch_geometric, bce_loss, info_nce, contrastive_learning, link_prediction]

requires:
  - phase: 03-graph-construction
    provides: "hetero_data.pt with ingredient/molecule nodes and co_occurs edge_label_index"
  - phase: 04-01
    provides: "tests/test_model.py stubs and tests/conftest.py tiny_hetero_graph fixture"

provides:
  - "model/losses.py with 4 exported loss functions: molecular_bce_loss, recipe_bce_loss, info_nce_loss, combined_loss"
  - "tests/test_model.py: 9 named test stubs (MODEL-01..MODEL-09), loss tests active"
  - "tests/conftest.py: tiny_hetero_graph and tiny_link_labels fixtures"
  - "model/__init__.py: Python package marker"

affects: [04-04, model-training]

tech-stack:
  added: []
  patterns:
    - "Shared _bce_link_pred_loss helper for molecular and recipe BCE functions"
    - "F.normalize inside info_nce_loss — does not mutate caller's tensor"
    - "Empty pos_pairs guard: return torch.tensor(0.0, requires_grad=True)"
    - "combined_loss never calls .item() — gradient graph preserved for backprop"

key-files:
  created:
    - model/losses.py
    - model/__init__.py
    - tests/test_model.py
  modified:
    - tests/conftest.py

key-decisions:
  - "_bce_link_pred_loss shared helper: molecular_bce_loss and recipe_bce_loss are semantically separate but structurally identical — helper avoids duplication while keeping separate public API"
  - "xfail(strict=False) on loss tests: a pre-commit hook added xfail markers; xpassed outcome accepted per plan (plan says 'xpassed or passed')"
  - "F.normalize returns new tensor inside info_nce_loss — input z never mutated in-place; masked_fill_ on sim matrix copy is safe"

patterns-established:
  - "Loss functions are stateless pure functions — no model state, no side effects"
  - "negative_sampling receives pos_edge_index as edge_index arg to avoid sampling existing positive edges"
  - "combined_loss keeps gradient graph intact by avoiding .item() before return"

requirements-completed: [MODEL-04, MODEL-05, MODEL-06, MODEL-07]

duration: 10min
completed: 2026-03-12
---

# Phase 4 Plan 3: Loss Functions Summary

**BCE link-prediction and InfoNCE contrastive loss functions in model/losses.py — 4 xpassed tests, gradient graph preserved throughout**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-12T17:57:43Z
- **Completed:** 2026-03-12T18:07:00Z
- **Tasks:** 1 (TDD: RED commit + GREEN commit)
- **Files modified:** 4

## Accomplishments

- Implemented `molecular_bce_loss` and `recipe_bce_loss` via shared `_bce_link_pred_loss` helper using `negative_sampling` from torch_geometric
- Implemented `info_nce_loss` with F.normalize (non-mutating), diagonal masking with -inf, and empty-pairs guard
- Implemented `combined_loss` as a pure weighted sum preserving the autograd graph
- Created `tests/test_model.py` with all 9 MODEL test stubs and `model/__init__.py` package marker
- All 4 loss function tests pass (xpassed)

## Task Commits

Each task was committed atomically:

1. **TDD RED: test stubs** - `583d8e1` (test)
2. **TDD GREEN: model/losses.py** - `ff8ffe4` (feat)

**Note:** Commit `c238f9c` created conftest.py (from a prior partial run); commit `7774390` added xfail markers to loss tests via pre-commit hook.

## Files Created/Modified

- `model/losses.py` — 4 exported loss functions: molecular_bce_loss, recipe_bce_loss, info_nce_loss, combined_loss
- `model/__init__.py` — Python package marker (empty)
- `tests/test_model.py` — 9 test stubs for MODEL-01..MODEL-09
- `tests/conftest.py` — tiny_hetero_graph and tiny_link_labels fixtures (scope=module)

## Decisions Made

- Shared `_bce_link_pred_loss` helper: both BCE losses are structurally identical but semantically separate (training script logs them independently). A private helper avoids code duplication while preserving distinct public API names.
- `F.normalize` inside `info_nce_loss` returns a new tensor, so the caller's `z` is never mutated. `masked_fill_` on the similarity matrix copy is safe since the matrix was created fresh via `torch.mm`.
- xfail tests with `strict=False`: a pre-commit hook added `@pytest.mark.xfail` decorators to the 4 loss tests. The plan specifies "xpassed or passed" as acceptable outcomes, so all 4 `xpassed` results satisfy the done criteria.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created tests/conftest.py and model/__init__.py as prerequisites**
- **Found during:** Task 1 (TDD RED)
- **Issue:** Plan 04-03 depends_on 04-01 (which would have created these), but 04-01 had not been executed. conftest.py and model/__init__.py were missing.
- **Fix:** Created both files as part of TDD setup; conftest.py was already present from a partial prior run (c238f9c); model/__init__.py created fresh.
- **Files modified:** tests/conftest.py, model/__init__.py
- **Verification:** Import succeeds; pytest collects all 9 tests
- **Committed in:** 583d8e1

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking prerequisite)
**Impact on plan:** Necessary to unblock execution. No scope creep.

## Issues Encountered

- Pre-commit hook auto-committed xfail markers to test_model.py (commit 7774390). Tests still pass as xpassed which the plan accepts.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `model/losses.py` is complete and importable; all 4 loss functions verified correct
- Plan 04-04 (training script) can import both `model/gat_model.py` (from 04-02) and `model/losses.py` (this plan)
- Plan 04-02 (FlavorGAT model) should be executed before 04-04 if not yet done

## Self-Check: PASSED

- FOUND: model/losses.py
- FOUND: tests/test_model.py
- FOUND: model/__init__.py
- FOUND commit: 583d8e1 (TDD RED)
- FOUND commit: ff8ffe4 (TDD GREEN)

---
*Phase: 04-model-training*
*Completed: 2026-03-12*
