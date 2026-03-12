---
phase: 02-feature-engineering
plan: 01
subsystem: testing
tags: [pytest, xfail, rdkit, tanimoto, morgan-fingerprint, feature-engineering, parquet]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: data/raw/molecules.csv, data/raw/ingredients.csv, data/raw/recipes.csv pipeline outputs
provides:
  - tests/test_features.py with 13 test functions covering FEAT-01 through FEAT-09
  - Phase 2 Nyquist scaffold: automated verify commands in Plans 02-04 reference these exact function names
affects:
  - 02-02-PLAN (fetch_smiles.py — tests test_smiles_cache_coverage, test_smiles_missing_logged)
  - 02-03-PLAN (build_features.py — FEAT-02 through FEAT-08 tests)
  - 02-04-PLAN (integration parquets — FEAT-09 tests)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "importorskip pattern: imports inside test bodies via pytest.importorskip to avoid collection-time ImportError"
    - "xfail with strict=False: tests register as xfail/skipped before implementation, never error"
    - "prefix-check pattern for schema: assert column prefix exists rather than exact column name for multi-column feature groups"

key-files:
  created:
    - tests/test_features.py
  modified: []

key-decisions:
  - "Used pytest.importorskip() for module-existence gating rather than try/except to keep test bodies clean"
  - "Used strict=False on xfail markers so tests show as SKIPPED (via importorskip) or XFAIL without failing the suite"
  - "test_ingredients_parquet_schema uses prefix matching (texture_, temperature_, etc.) since column count is implementation detail"

patterns-established:
  - "Wave 1 test scaffold: create all test stubs before any implementation so verify commands in later plans reference existing functions"
  - "importorskip at top of test body: data.fetch_smiles and data.build_features are skipped gracefully until modules exist"

requirements-completed: [FEAT-01, FEAT-02, FEAT-03, FEAT-04, FEAT-05, FEAT-06, FEAT-07, FEAT-08, FEAT-09]

# Metrics
duration: 2min
completed: 2026-03-12
---

# Phase 2 Plan 01: Feature Engineering Test Scaffold Summary

**pytest scaffold with 13 xfail test functions covering all FEAT-01 through FEAT-09 requirements, using importorskip pattern for zero-error collection before any implementation exists**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-12T02:11:57Z
- **Completed:** 2026-03-12T02:13:57Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created tests/test_features.py with exactly 13 test functions, all named as specified in the plan
- All 13 collected by pytest in 0.63s with 0 errors, 0 failures
- Tests show as XFAIL or SKIPPED (via importorskip) before implementation — never error on collection
- Plans 02-02 through 02-04 can now reference these exact function names in their verify commands

## Task Commits

1. **Task 1: Create test_features.py scaffold with all 13 test stubs** - `97d3f96` (test)

## Files Created/Modified

- `tests/test_features.py` - 13 test functions for FEAT-01 through FEAT-09 feature engineering requirements

## Decisions Made

- Used `pytest.importorskip("data.build_features")` inside each test body to gate on module existence; this produces SKIPPED (not XFAIL) when the module is absent, which is acceptable — no collection errors
- Used `strict=False` on `@pytest.mark.xfail` so tests that would xfail due to missing files (FEAT-09 parquet tests) show as XFAIL rather than ERROR
- `test_ingredients_parquet_schema` uses column prefix matching (`texture_`, `temperature_`, `cultural_context_`, `flavor_profile_`) because the exact column count is an implementation detail of build_features.py

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Test scaffold is ready; Plans 02-02 (fetch_smiles.py), 02-03 (build_features.py), and 02-04 (integration parquets) can proceed
- All 13 test function names match exactly what those plans reference in their verify commands
- No blockers

---
*Phase: 02-feature-engineering*
*Completed: 2026-03-12*
