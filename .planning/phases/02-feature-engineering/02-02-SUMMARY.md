---
phase: 02-feature-engineering
plan: 02
subsystem: data
tags: [pubchem, smiles, httpx, asyncio, flavordb2, json-cache, pipeline]

# Dependency graph
requires:
  - phase: 01-02
    provides: data/raw/ingredients.csv with molecules_json column containing SMILES
  - phase: 01-04
    provides: data/raw/molecules.csv with pubchem_id column; run_pipeline.py orchestrator pattern
provides:
  - data/fetch_smiles.py — SMILES extractor with FlavorDB2 primary + PubChem async fallback
  - data/raw/pubchem_cache.json — complete SMILES cache {pubchem_id_str: smiles_or_null}, 1788 entries
affects:
  - phase 02-03 (build_features.py reads pubchem_cache.json as gate input)
  - phase 02-04 (build_features.py requires complete cache before RDKit processing)

# Tech tracking
tech-stack:
  added:
    - httpx (async HTTP client for PubChem PUG-REST)
    - asyncio.Semaphore(5) for rate limiting at ≤5 req/sec
  patterns:
    - FlavorDB2-first SMILES extraction: parse molecules_json → PubChem only for gaps
    - Skip-if-exists gate with set equality completeness check (not just row count)
    - 4xx → null (not found), 5xx → raise (do NOT store as null)
    - String keys in JSON (json.dump converts int keys to strings; compare str(id))

key-files:
  created:
    - data/fetch_smiles.py
    - data/raw/pubchem_cache.json
  modified:
    - run_pipeline.py

key-decisions:
  - "FlavorDB2 molecules_json is the primary SMILES source (1788/1788 coverage); PubChem is gap-fill only — happy path completes with zero network calls"
  - "4xx responses stored as null (legitimate miss); 5xx raises exception to prevent non-deterministic null entries"
  - "Cache keys are strings (json.dump int→str conversion); set equality gate uses str(id) comparison"
  - "Deduplication in FlavorDB2 extraction: first non-null smile wins when same pubchem_id appears in multiple ingredient rows"

patterns-established:
  - "Gate pattern: set(cache.keys()) == set(str(id) for id in all_pubchem_ids) — entry existence not SMILES presence"
  - "Async fetch pattern: asyncio.Semaphore(5) + httpx.AsyncClient + asyncio.as_completed for ordered-irrelevant results"
  - "Skip-if-exists with completeness check: load cache → verify set equality → skip only if complete"

requirements-completed: [FEAT-01]

# Metrics
duration: 3min
completed: 2026-03-12
---

# Phase 02 Plan 02: SMILES Fetch Summary

**SMILES extraction from FlavorDB2 molecules_json with async PubChem gap-fill, writing 1788-entry pubchem_cache.json as the gate artifact for Phase 2 feature engineering**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-12T02:18:00Z
- **Completed:** 2026-03-12T02:21:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created data/fetch_smiles.py: FlavorDB2 molecules_json extraction as primary source, async httpx PubChem gap-fill, skip-if-exists gate with set equality completeness check
- Generated data/raw/pubchem_cache.json: 1788 entries, 1788 with SMILES (0 nulls) — 100% coverage from FlavorDB2 alone (zero PubChem queries needed)
- Wired fetch_smiles into run_pipeline.py as Phase 2 stage with --skip-smiles flag and summary table row
- Both tests xpassed: test_smiles_cache_coverage and test_smiles_missing_logged

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement fetch_smiles.py with FlavorDB2 extraction and PubChem fallback** - `c3f1a1c` (feat)
2. **Task 2: Wire fetch_smiles into run_pipeline.py as Phase 2 stage** - `f4ad607` (feat)

## Files Created/Modified

- `data/fetch_smiles.py` — SMILES extractor: FlavorDB2 molecules_json parsing → PubChem async gap-fill → pubchem_cache.json with gate check and summary log
- `data/raw/pubchem_cache.json` — Complete SMILES cache: 1788 entries, all non-null (100% FlavorDB2 coverage)
- `run_pipeline.py` — Added Phase 2 SMILES fetch stage: --skip-smiles flag, try/except isolation, summary table smiles_fetch row

## Decisions Made

- **FlavorDB2-first strategy:** Research confirmed 1788/1788 molecules already have SMILES in ingredients.csv molecules_json column. The PubChem fetch is a gap-filler; in the happy path it completes with zero network calls.
- **4xx vs 5xx distinction:** 404 (molecule not in PubChem) is stored as null — a legitimate permanent miss. 5xx/network errors raise exceptions — these are transient and must not be stored as null (would break determinism).
- **String key normalization:** JSON serialization converts int keys to strings. The gate check compares `set(cache.keys())` (strings) against `set(str(id) for id in all_pubchem_ids)` to avoid type mismatch.

## Deviations from Plan

None - plan was executed exactly as written in a prior session. This execution verified all done criteria are met and created the SUMMARY.md.

## Issues Encountered

None. FlavorDB2 SMILES coverage was 100% as predicted by research — zero PubChem queries were needed.

## User Setup Required

None - no external service configuration required. PubChem queries are automatic if any gap IDs exist (none do for this dataset).

## Next Phase Readiness

- data/raw/pubchem_cache.json exists with 1788 entries, 100% SMILES coverage
- Gate check verified: set(cache.keys()) == set(str(id) for id in all pubchem_ids)
- Re-running fetch_smiles.py prints [SKIP] immediately (idempotent)
- Phase 2 Plans 03-04 (build_features.py) can proceed — cache gate will pass immediately

---
*Phase: 02-feature-engineering*
*Completed: 2026-03-12*
