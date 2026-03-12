---
phase: 01-foundation
plan: 02
subsystem: data
tags: [flavordb, requests-cache, sqlite, tqdm, pandas, scraping]

# Dependency graph
requires:
  - phase: 01-01
    provides: project skeleton, logs/ and data/raw/ directory structure, test stubs

provides:
  - FlavorDB2 scraper (data/scrape_flavordb.py) with SQLite cache and idempotent execution
  - data/raw/ingredients.csv — 935 rows, columns: ingredient_id, name, category, molecules_json
  - data/raw/molecules.csv — 1788 deduplicated molecules, columns: pubchem_id, common_name, flavor_profile
  - data/raw/flavordb_cache.sqlite — 81MB SQLite cache of all HTTP responses (200 + 404)

affects:
  - 01-03 (FooDB join reads ingredients.csv)
  - 02-feature-engineering (reads ingredients.csv, molecules.csv for SMILES enrichment)
  - 03-graph-construction (molecule co-occurrence edges based on molecules.csv)

# Tech tracking
tech-stack:
  added:
    - requests-cache 1.3.1 (SQLite-backed HTTP cache, allowable_codes=[200,404])
    - tqdm 4.67.3 (progress bars with logging_redirect_tqdm)
    - pandas 3.0.1 (DataFrame I/O for CSV output)
  patterns:
    - Idempotent stage pattern: check output file existence, skip if present, --force to override
    - Cache-all-responses pattern: cache 404s alongside 200s since entity gaps are permanent
    - Consecutive-404 early-stop: break after 10 consecutive 404s to avoid tail thrashing
    - Content-Type validation guard: detect HTML-response-on-wrong-URL pitfall at startup

key-files:
  created:
    - data/scrape_flavordb.py
    - data/raw/ingredients.csv
    - data/raw/molecules.csv
    - data/raw/flavordb_cache.sqlite
  modified:
    - tests/test_flavordb.py (removed pytest.skip decorators — tests now active)

key-decisions:
  - "Cache 404 responses alongside 200s: FlavorDB2 entity gaps are permanent, no benefit to re-fetching"
  - "Stop after 10 consecutive 404s at entity 988: avoids 112 wasted requests at tail of ID range"
  - "Store molecules_json as JSON string in ingredients.csv: preserves full molecule list per ingredient without normalizing at scrape time"
  - "Deduplicate molecules by pubchem_id in memory during scrape: avoids post-processing step"

patterns-established:
  - "Idempotent stage: check output file, skip with [SKIP] log message, --force flag overrides"
  - "Summary line format: 'FlavorDB: N scraped, M failed (404)' at end of each data script"
  - "tqdm + logging_redirect_tqdm: keeps log messages aligned with progress bar output"

requirements-completed: [DATA-01, DATA-02]

# Metrics
duration: 7min
completed: 2026-03-12
---

# Phase 1 Plan 02: FlavorDB2 Scraper Summary

**FlavorDB2 standalone scraper using requests_cache SQLite backend, producing 935-ingredient and 1788-molecule CSV datasets in one network pass**

## Performance

- **Duration:** 7 min (5 min scraping + 2 min setup/verify)
- **Started:** 2026-03-12T00:23:42Z
- **Completed:** 2026-03-12T00:30:44Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Scraped 935 ingredients from FlavorDB2 entity IDs 1-988 (stopped after 10 consecutive 404s)
- Collected 1788 unique molecules deduplicated by pubchem_id
- SQLite cache (81MB) captures all 200 and 404 responses — re-runs are instant (<1 second)
- Both test_flavordb.py tests activated and passing (previously skipped)

## Task Commits

Each task was committed atomically:

1. **Task 1: FlavorDB2 scraper** - `31e5dcd` (feat)
2. **Task 2: Run scraper and verify outputs** - `7c991b8` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `data/scrape_flavordb.py` - Standalone FlavorDB2 scraper with requests_cache, tqdm, idempotent execution, Content-Type guard
- `data/raw/ingredients.csv` - 935 rows: ingredient_id, name, category, molecules_json
- `data/raw/molecules.csv` - 1788 rows: pubchem_id, common_name, flavor_profile
- `data/raw/flavordb_cache.sqlite` - 81MB SQLite cache (never expires, caches 200+404)
- `tests/test_flavordb.py` - Removed pytest.skip decorators; tests are now active and passing

## Decisions Made

- Installed requests-cache and tqdm via pip3 with --break-system-packages since no conda environment was active on the execution machine; the environment.yml specifies the canonical environment for project use.
- Content-Type validation checks on first fetch to catch the RESEARCH.md pitfall (HTML returned on wrong URL path). Allows "text/javascript" alongside "application/json" since some CDNs serve JSON with that content type.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed requests-cache and tqdm via pip3**
- **Found during:** Task 1 (scraper creation)
- **Issue:** conda environment (flavor-network) was not available on the execution machine; requests_cache and tqdm were missing from system Python
- **Fix:** Ran `pip3 install requests-cache tqdm --break-system-packages` to enable script execution
- **Files modified:** None (system pip only)
- **Verification:** `python3 -c "import requests_cache, tqdm, pandas; print('all imports OK')"` succeeded
- **Committed in:** Not committed (system install, not source change)

---

**Total deviations:** 1 auto-fixed (1 blocking — missing dependency)
**Impact on plan:** Required to run the scraper at all. No scope creep.

## Issues Encountered

- No conda environment active on execution machine — resolved by installing packages directly via pip3 (see deviation above).
- FlavorDB2 entity coverage: actual scrape yielded 935 ingredients (plan specified >= 900 as minimum), stopping at entity 988 after 10 consecutive 404s. This is within expected range per RESEARCH.md (~936 valid ingredients expected in 1-1000 range).

## Next Phase Readiness

- data/raw/ingredients.csv (935 rows) ready for Plan 01-03 FooDB join
- data/raw/molecules.csv (1788 rows) ready for Phase 2 SMILES enrichment
- SQLite cache in place — any FlavorDB re-queries in Phase 2 will be instant
- test_flavordb.py gate is active and passing

---
*Phase: 01-foundation*
*Completed: 2026-03-12*
