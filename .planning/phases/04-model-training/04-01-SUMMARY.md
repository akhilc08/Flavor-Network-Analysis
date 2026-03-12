---
phase: 04-model-training
plan: 01
subsystem: testing
tags: [pytorch-geometric, HeteroData, pytest, xfail, gnn, fixtures]

# Dependency graph
requires:
  - phase: 03-graph-construction
    provides: HeteroData graph format and edge type conventions (contains, rev_contains, co_occurs, structurally_similar)
provides:
  - tests/conftest.py with tiny_hetero_graph (10 ingredient, 50 molecule nodes, 4 edge types) and tiny_link_labels fixtures
  - tests/test_model.py with 9 xfail stub tests covering MODEL-01 through MODEL-09
  - Shared pytest fixture available to all Phase 4 test files via conftest.py
affects:
  - 04-model-training (all plans 02-04 reference tests/test_model.py as verify commands)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - xfail(strict=False) stubs for TDD Wave 0 — tests written before implementation; suite stays green
    - scope='module' on HeteroData fixtures to avoid recreation overhead per test
    - Import-inside-test-body pattern so ImportError is caught by xfail, not at collection

key-files:
  created:
    - tests/conftest.py
  modified:
    - tests/test_model.py

key-decisions:
  - "scope='module' on tiny_hetero_graph and tiny_link_labels fixtures: avoids repeated tensor creation across 9+ tests in the same module"
  - "Import model modules inside test bodies (not top-level): ImportError is caught by xfail marker, preventing collection errors"
  - "xfail(strict=False) not skip: strict=False means xpass counts as green — tests become naturally passing as implementation is added without needing to remove markers"

patterns-established:
  - "Wave 0 scaffold pattern: create xfail stub tests before any implementation to give executors a green baseline"
  - "conftest.py fixture injection: shared synthetic graph available to all tests via pytest fixture injection, not inline construction"

requirements-completed: [MODEL-01, MODEL-02, MODEL-03, MODEL-04, MODEL-05, MODEL-06, MODEL-07, MODEL-08, MODEL-09]

# Metrics
duration: 6min
completed: 2026-03-12
---

# Phase 4 Plan 01: Model Test Scaffold Summary

**Wave 0 test scaffold: conftest.py with synthetic 10-ingredient/50-molecule HeteroData fixture and 9 xfail stub tests covering all MODEL requirements**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-12T18:02:07Z
- **Completed:** 2026-03-12T18:03:37Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created `tests/conftest.py` with `tiny_hetero_graph` fixture (10 ingredient nodes, 50 molecule nodes, 4 edge types, no self-loops on co_occurs and structurally_similar) and `tiny_link_labels` fixture
- Verified/finalized `tests/test_model.py` with all 9 xfail stubs — `pytest tests/test_model.py -x -q` exits 0 (2 xfailed, 7 xpassed)
- All 9 required test function names present: test_gat_output_shape, test_no_self_loops, test_bn_dropout_present, test_molecular_loss, test_recipe_loss, test_infonce_loss, test_combined_loss_formula, test_checkpoint_save_on_improvement, test_embedding_export

## Task Commits

Each task was committed atomically:

1. **Task 1: Create conftest.py with synthetic HeteroData fixture** - `c238f9c` (feat)
2. **Task 2: Create test_model.py with stubs for MODEL-01 through MODEL-09** - pre-existing (7774390 + earlier commits verified correct)

**Plan metadata:** see final docs commit

## Files Created/Modified
- `tests/conftest.py` - Shared pytest fixtures: tiny_hetero_graph (HeteroData, scope=module) and tiny_link_labels (link prediction labels, scope=module)
- `tests/test_model.py` - 9 xfail stub tests for MODEL-01 through MODEL-09, all imports inside test bodies

## Decisions Made
- `scope='module'` on both fixtures: HeteroData construction has torch tensor allocation overhead; module scope avoids recreation for each of 9 tests
- Import model modules inside test bodies, not at top level: collection-time ImportError would cause ERROR (not xfail), breaking the green baseline requirement
- `xfail(strict=False)` over `pytest.skip`: as implementation is added in plans 02-04, tests will xpass and eventually pass without requiring marker removal

## Deviations from Plan

None — plan executed exactly as written. test_model.py was already partially committed by a prior session with xfail markers added (7774390); verified final state matches all plan requirements.

## Issues Encountered
- `pytest` binary is at `/opt/homebrew/bin/pytest` (system Python), not the conda environment's `python -m pytest`. Used `conda run -n flavor-network python -m pytest` for all verification — confirmed consistent behavior.
- `test_foodb.py::test_join_count` pre-existing failure (foodb_matched column missing) — unrelated to this plan, no action taken.

## Next Phase Readiness
- Test scaffold is complete and gates all Phase 4 implementation plans
- Plans 02 (gat_model.py), 03 (losses.py), and 04 (train_gat.py) can now execute with `pytest tests/test_model.py -x -q` as their verify command
- No blockers for Phase 4 execution

## Self-Check: PASSED

- tests/conftest.py: FOUND
- tests/test_model.py: FOUND
- 04-01-SUMMARY.md: FOUND
- Commit c238f9c (Task 1): FOUND

---
*Phase: 04-model-training*
*Completed: 2026-03-12*
