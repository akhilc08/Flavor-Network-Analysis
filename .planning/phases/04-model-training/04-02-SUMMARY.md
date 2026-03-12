---
phase: 04-model-training
plan: 02
subsystem: model
tags: [pytorch, torch_geometric, HeteroConv, GATConv, heterogeneous-gnn, attention]

# Dependency graph
requires:
  - phase: 03-graph-construction
    provides: HeteroData object with 4 edge types (contains, rev_contains, co_occurs, structurally_similar)
  - phase: 04-01
    provides: test scaffold (tests/test_model.py with xfail stubs, tests/conftest.py with tiny_hetero_graph fixture)
provides:
  - FlavorGAT class in model/gat_model.py: 3-layer HeteroConv GAT with per-node-type projections to 128-dim embeddings
  - All 3 model-structure tests passing (test_gat_output_shape, test_no_self_loops, test_bn_dropout_present)
affects:
  - 04-03 (losses module uses FlavorGAT forward pass output)
  - 04-04 (training loop imports FlavorGAT)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HeteroConv wrapping GATConv per edge type — add_self_loops=False on all, concat=True with out_channels=hidden//heads"
    - "ModuleDict per-node-type projections (proj, bn, embed_proj) for clean heterogeneous parameter management"
    - "Fallback pattern in forward pass: x_dict.get(node_type, prev_x_dict.get(node_type)) for sparse test graphs"

key-files:
  created:
    - model/gat_model.py
  modified:
    - tests/test_model.py

key-decisions:
  - "Store both self.dropout_p and self.dropout as attributes — satisfies plan spec (dropout_p) and existing test stub (model.dropout > 0)"
  - "out_channels = hidden_channels // heads in GATConv — prevents concat=True dimension explosion (avoids dim*heads output)"
  - "Fallback x_dict.get(node_type, prev_x_dict.get(node_type)) in forward — allows model to run on synthetic mini-graphs where some edge types are absent"

patterns-established:
  - "FlavorGAT(hidden_channels=64, embed_dim=128, heads=4, dropout=0.0) is the test-fixture instantiation pattern"
  - "No activation after embed_proj — raw embeddings for dot-product scoring in Phase 5"

requirements-completed: [MODEL-01, MODEL-02, MODEL-03]

# Metrics
duration: 6min
completed: 2026-03-12
---

# Phase 4 Plan 2: FlavorGAT Model Implementation Summary

**3-layer HeteroConv GAT with per-node-type lazy Linear projections, BatchNorm1d between layers, and 128-dim embedding output via PyTorch Geometric**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-12T04:50:16Z
- **Completed:** 2026-03-12T04:56:00Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- FlavorGAT class instantiates and runs a forward pass on a synthetic HeteroData graph with all 4 edge types
- Output ingredient embeddings have shape (N_ingredients, 128) — verified by test
- All GATConv layers set add_self_loops=False — verified by test
- BatchNorm1d applied per node type per layer (6 total entries in self.bn) — verified by test
- Model handles sparse mini-graphs (fallback pattern for absent node types post-conv)

## Task Commits

Each task was committed atomically:

1. **[Rule 3 - Blocking] Fix test_model.py xfail markers** - `7774390` (test)
2. **Task 1: Implement FlavorGAT model class (GREEN)** - `2ba7df1` (feat)

_Note: TDD — RED phase confirmed 3 target tests were xfail before implementation; GREEN phase made all 3 xpass._

## Files Created/Modified
- `model/gat_model.py` - FlavorGAT class: 3-layer HeteroConv GAT with per-type projections and 128-dim output
- `tests/test_model.py` - Added missing @pytest.mark.xfail markers to MODEL-04 through MODEL-07 loss tests

## Decisions Made
- Stored both `self.dropout_p` and `self.dropout` attributes: plan spec says `dropout_p`, but existing test stub checks `model.dropout`. Storing both satisfies both without changing the test.
- `out_channels = hidden_channels // heads` in all GATConv layers: prevents the concat=True dimension explosion documented in research (Pitfall 1).
- Fallback for absent node types in `forward()`: `x_dict.get(node_type, prev_x_dict.get(node_type))` allows the model to run correctly on the 10-node synthetic test fixture where some edge types may produce no output for certain node types.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing xfail markers on MODEL-04 through MODEL-07 loss tests**
- **Found during:** Setup (before Task 1)
- **Issue:** Tests `test_molecular_loss`, `test_recipe_loss`, `test_infonce_loss`, `test_combined_loss_formula` in tests/test_model.py had no `@pytest.mark.xfail` markers. Since `model/losses.py` was absent, these tests produced FAILED (not xfailed), breaking the suite and preventing the RED phase from being green.
- **Fix:** Added `@pytest.mark.xfail(reason="model/losses.py not yet implemented", strict=False)` to all four tests.
- **Files modified:** tests/test_model.py
- **Verification:** `pytest tests/test_model.py -q` exits 0 with 5 xfailed, 4 xpassed
- **Committed in:** `7774390`

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking issue)
**Impact on plan:** Required fix to allow TDD RED phase to be green. No scope creep.

## Issues Encountered
- Plan 04-01 (test scaffold) had not been executed before plan 04-02 was invoked. Both conftest.py and test_model.py already existed on disk (partially committed), but test_model.py had 4 tests without xfail markers that blocked the suite. Fixed inline via Rule 3.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `model/gat_model.py` is importable and exports `FlavorGAT`
- Plan 04-03 (losses: molecular BCE + recipe BCE + InfoNCE) can proceed immediately
- Plan 04-04 (training loop) depends on both 04-02 and 04-03

---
*Phase: 04-model-training*
*Completed: 2026-03-12*
