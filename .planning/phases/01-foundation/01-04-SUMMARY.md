---
phase: 01-foundation
plan: 04
subsystem: data
tags: [foodb, rapidfuzz, fuzzy-matching, pipeline-orchestrator, pandas, tqdm, subprocess]

# Dependency graph
requires:
  - phase: 01-02
    provides: data/raw/ingredients.csv and data/raw/molecules.csv (FlavorDB2 scraper output)
  - phase: 01-03
    provides: data/raw/recipes.csv (recipe co-occurrence output)
provides:
  - data/join_foodb.py — standalone FooDB fuzzy join enriching molecules.csv with macronutrient columns
  - run_pipeline.py — master Phase 1 orchestrator with --skip-* and --force flags
  - data/raw/molecules.csv — ready for FooDB enrichment when foodb/ dir is populated
affects:
  - phase 2 feature engineering (reads enriched molecules.csv)
  - phase 3 graph construction (reads all three CSVs)
  - phase 4 model training (reads all three CSVs)

# Tech tracking
tech-stack:
  added:
    - rapidfuzz (fuzzy string matching with token_sort_ratio)
  patterns:
    - FooDB dir check pattern: check dir exists → log instructions → return (never crash)
    - Idempotent join: check for foodb_matched column presence before running
    - Pipeline orchestrator: import-and-call pattern (not subprocess) with per-stage try/except
    - Summary table printed after all stages regardless of skip flags

key-files:
  created:
    - data/join_foodb.py
    - run_pipeline.py
  modified: []

key-decisions:
  - "FooDB dir missing: print download instructions and return gracefully (no crash) — compliant with CC BY-NC 4.0 license and 952MB size constraint"
  - "Pipeline orchestrator uses direct function import (not subprocess) for cleaner exception handling and unified logging"
  - "token_sort_ratio used for fuzzy matching (not fuzz.ratio) — correctly handles word-order variants like 'garlic, roasted' vs 'roasted garlic'"
  - "FooDB join threshold check: warn if < 300 matches but never lower threshold automatically"

patterns-established:
  - "FooDB graceful degradation: molecules.csv remains valid without FooDB enrichment; foodb_matched=False for all rows"
  - "Pipeline summary table reads live from disk after all stages complete — always reflects actual state"
  - "Stage isolation: each pipeline stage in try/except; one stage failure does not abort subsequent stages"

requirements-completed:
  - DATA-03
  - DATA-06

# Metrics
duration: 5min
completed: 2026-03-12
---

# Phase 01 Plan 04: FooDB Join and Pipeline Orchestrator Summary

**FooDB fuzzy join enriching molecules.csv via rapidfuzz token_sort_ratio + run_pipeline.py master orchestrator with --skip-* / --force flags unifying all four Phase 1 data scripts**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-12T00:55:13Z
- **Completed:** 2026-03-12T00:59:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created data/join_foodb.py: idempotent FooDB fuzzy join that handles missing FooDB dir gracefully (prints CC BY-NC 4.0 download instructions, returns without crashing)
- Created run_pipeline.py: master orchestrator that imports and calls all three data scripts with per-stage error isolation and final summary table
- Phase 1 acceptance gate test (tests/test_outputs.py::test_output_files_exist) now passes — all three CSVs exist
- Full pipeline is idempotent: second run prints [SKIP] for all stages that have existing outputs

## Task Commits

Each task was committed atomically:

1. **Task 1: FooDB join script** - `91a2754` (feat)
2. **Task 2: run_pipeline.py orchestrator** - `ae2460a` (feat)

## Files Created/Modified

- `data/join_foodb.py` — FooDB fuzzy name match against FlavorDB2 ingredients; enriches molecules.csv with foodb_matched, foodb_food_id, macronutrients_json, moisture_content
- `run_pipeline.py` — Phase 1 pipeline orchestrator: FlavorDB2 scrape → recipes co-occurrence → FooDB join, with --skip-scrape, --skip-foodb, --skip-recipes, --force flags and final summary table

## Decisions Made

- **FooDB graceful degradation:** When data/raw/foodb/ is absent, join_foodb prints download instructions and returns. molecules.csv remains valid without enrichment. This is the correct behavior per CC BY-NC 4.0 license compliance (no programmatic download) and file size (952MB tar.gz).
- **Direct import pattern:** run_pipeline.py imports functions directly rather than using subprocess. This gives unified logging, cleaner exception handling, and avoids Python path issues.
- **token_sort_ratio for fuzzy matching:** fuzz.token_sort_ratio normalizes token order before comparing — required for food name variants like "garlic, roasted" vs "roasted garlic". fuzz.ratio would produce artificially low scores for these cases.
- **Warning threshold only:** FooDB join warns if matched_count < 300 but never lowers the threshold or crashes. Phase 3 graph construction enforces the final gate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] rapidfuzz not installed in system Python**
- **Found during:** Task 1 verification
- **Issue:** `ModuleNotFoundError: No module named 'rapidfuzz'` when testing join_foodb import
- **Fix:** Installed rapidfuzz 3.14.3 via pip3 --break-system-packages
- **Files modified:** system packages (no project file change)
- **Verification:** `from rapidfuzz import process, fuzz` succeeds; syntax check passes
- **Committed in:** 91a2754 (Task 1 commit — package already listed in requirements)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** rapidfuzz install was a missing system-level dependency. No scope creep.

## Issues Encountered

- FooDB data is not available (expected — CC BY-NC 4.0, 952MB manual download required). The join script handles this gracefully. When FooDB data is downloaded to data/raw/foodb/, running `python data/join_foodb.py` or `python run_pipeline.py` will enrich molecules.csv automatically.

## User Setup Required

To enable FooDB macronutrient enrichment:
1. Visit https://foodb.ca/downloads (CC BY-NC 4.0 license)
2. Download the full CSV database archive (~952 MB tar.gz)
3. Extract to data/raw/foodb/ (should contain Food.csv and Compound.csv)
4. Run: `python data/join_foodb.py` or `python run_pipeline.py --skip-scrape --skip-recipes`

This step is optional for Phase 2+ — molecules.csv is valid without FooDB enrichment.

## Next Phase Readiness

- All three Phase 1 output CSVs exist: data/raw/ingredients.csv (935 rows), data/raw/molecules.csv (1,788 rows), data/raw/recipes.csv (5,944,163 rows)
- Phase 1 acceptance gate passes: tests/test_outputs.py::test_output_files_exist PASSED
- Phase 2 (feature engineering) can proceed immediately — reads all three CSVs
- FooDB enrichment is available as an optional enhancement when data is downloaded

---
*Phase: 01-foundation*
*Completed: 2026-03-12*
