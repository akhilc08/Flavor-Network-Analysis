---
phase: 03-graph-construction
plan: "01"
subsystem: testing
tags: [pytest, torch, torch_geometric, hetero_graph, test_stubs]

# Dependency graph
requires:
  - phase: 02-feature-engineering
    provides: molecule descriptors, Morgan fingerprints, Tanimoto edges, co-occurrence matrix
provides:
  - "tests/test_graph.py with 9 skipped stub tests covering GRAPH-01 through GRAPH-09"
affects: [03-02, 03-03, 03-04, 03-05]

# Tech tracking
tech-stack:
  added: []
  patterns: [skip-guard pattern using os.path.exists before torch.load, _load_payload() helper for DRY skip logic, deferred-import pattern to avoid ModuleNotFoundError before artifact exists]

key-files:
  created: [tests/test_graph.py]
  modified: []

key-decisions:
  - "_load_payload() called before any torch import so pytest.skip fires correctly when hetero_data.pt is absent — avoids ModuleNotFoundError masking the intended skip"
  - "test_validation_gate skips on ImportError only (not .pt absence) — it tests build_graph.run_validation_gate in isolation with a minimal HeteroData"
  - "test_no_leakage checks both (s,d) and (d,s) directions to catch bidirectional leakage"

patterns-established:
  - "Skip-guard pattern: call _load_payload() first, import torch after — ensures skip fires on missing artifact instead of raising ModuleNotFoundError"
  - "test_validation_gate isolation: tests function contract without needing built artifact, skips only on ImportError"

requirements-completed: [GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-05, GRAPH-06, GRAPH-07, GRAPH-08, GRAPH-09]

# Metrics
duration: 5min
completed: 2026-03-11
---

# Phase 3 Plan 01: Graph Test Stubs Summary

**9 pytest stubs covering all GRAPH requirements written as skip-guarded tests that will unskip automatically once graph/hetero_data.pt is built**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-11T21:50:53Z
- **Completed:** 2026-03-11T21:55:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Wrote tests/test_graph.py with all 9 test functions for GRAPH-01 through GRAPH-09
- All 8 artifact-dependent tests skip via `_load_payload()` helper when graph/hetero_data.pt is absent
- test_validation_gate skips only on ImportError from graph.build_graph, enabling isolated function testing
- pytest reports 9 skipped, 0 failed, 0 errors on a clean checkout without any Phase 3 artifacts

## Task Commits

1. **Task 1: Write test_graph.py with 9 skipped stubs** - `95d5328` (test)

## Files Created/Modified
- `tests/test_graph.py` - 9 test stubs for GRAPH-01 through GRAPH-09; all skip until hetero_data.pt exists

## Decisions Made
- Import order: `_load_payload()` must be called before any `import torch` inside test functions so `pytest.skip` fires on a missing artifact instead of raising `ModuleNotFoundError`. This required moving `import torch` to after the `_load_payload()` call in tests that also use torch directly.
- `test_validation_gate` does not use the skip-guard — it tests `run_validation_gate()` in isolation using a minimal `HeteroData` with 10 nodes. It skips only if `graph.build_graph` cannot be imported (Phase 3 not yet started).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed import order to prevent ModuleNotFoundError masking pytest.skip**
- **Found during:** Task 1 (initial verification run)
- **Issue:** Plan example showed `import torch` before `_load_payload()` call; without torch installed, the import raised `ModuleNotFoundError` before `pytest.skip` could fire — causing 1 failure instead of 9 skips
- **Fix:** Moved `import torch` to after `_load_payload()` in test_graph_loads, test_ingredient_features, and test_molecule_features
- **Files modified:** tests/test_graph.py
- **Verification:** pytest reports 9 skipped, 0 failed, 0 errors
- **Committed in:** 95d5328 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary for correct skip behavior when torch is unavailable. No scope creep.

## Issues Encountered
- ModuleNotFoundError for torch caused first pytest run to report 1 failure. Fixed by reordering imports inside the affected test functions.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Test stubs are the Wave 0 prerequisite. Plans 03-02 onward (graph builder, train/val/test split, feature assembly) can now unskip tests as they build the real implementation.
- graph/build_graph.py must export `run_validation_gate(data: HeteroData) -> None` (raises ValueError on invalid graph) for test_validation_gate to fully activate.

---
*Phase: 03-graph-construction*
*Completed: 2026-03-11*
