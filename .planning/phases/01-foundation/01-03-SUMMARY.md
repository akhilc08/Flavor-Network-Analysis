---
phase: 01-foundation
plan: 03
subsystem: data
tags: [recipenlg, allrecipes, co-occurrence, pandas, beautifulsoup, requests, scraping, huggingface]

# Dependency graph
requires:
  - phase: 01-01
    provides: project scaffold, test infrastructure, data/raw/ directory
provides:
  - data/raw/recipes.csv — 5,944,163 ingredient co-occurrence pairs (ingredient_a, ingredient_b, count)
  - data/raw/recipes_allrecipes.csv — 76 scraped AllRecipes recipes as manual fallback seed
  - data/scrape_recipes.py — standalone runnable streaming RecipeNLG + polite AllRecipes scraper
affects:
  - phase 3 graph construction (co-occurs edge type uses recipes.csv)
  - phase 4 model training (recipe loss component uses recipes.csv)

# Tech tracking
tech-stack:
  added:
    - pandas (CSV streaming with chunksize)
    - requests (HTTP streaming, AllRecipes scraping)
    - beautifulsoup4 (HTML ingredient extraction)
    - tqdm (progress display)
    - huggingface_hub (file URL resolution for dataset mirror)
  patterns:
    - HTTP streaming of large CSV via requests + pandas chunksize (no datasets library required)
    - JSON-LD recipe extraction with @type as list-or-string handling
    - Bot-block detection limited to actual challenge indicators (cf-mitigated, challenge-form, cf_chl_)
    - Idempotent pipeline: skip if output exists unless --force
    - Counter merging: nlg_counter + allrecipes_counter via Python Counter addition

key-files:
  created:
    - data/scrape_recipes.py
    - data/raw/recipes.csv
    - data/raw/recipes_allrecipes.csv
  modified:
    - tests/test_recipes.py (removed pytest.skip)
    - tests/test_allrecipes.py (removed pytest.skip)

key-decisions:
  - "Switch from HuggingFace datasets library to direct HTTP streaming: datasets 2.x and 3.x both incompatible with Python 3.14 due to dill _batch_setitems signature change; used Mahimas/recipenlg CSV mirror instead"
  - "AllRecipes Cloudflare detection false-positive fix: only flag challenge-form/cf_chl_/cf-mitigated=challenge headers, not mere presence of 'cloudflare' string (AllRecipes uses Cloudflare CDN legitimately)"
  - "JSON-LD @type normalization: AllRecipes returns @type as ['Recipe'] list not 'Recipe' string; added _is_recipe_type() helper to handle both"
  - "AllRecipes scraper limited to 76 recipes (some category URLs returned 0 links due to URL structure changes); acceptable as supplemental data — RecipeNLG provides primary 5.9M pairs"

patterns-established:
  - "Streaming pattern: pd.read_csv(response.raw, chunksize=N) for large CSV over HTTP — avoids download to disk and OOM"
  - "Recipe NER field: always use recipe['ner'] (or CSV NER column) for clean ingredient tokens, never raw ingredients strings"
  - "Co-occurrence pair normalization: always store as (min(a, b), max(a, b)) for consistent deduplication"
  - "AllRecipes scraping: JSON-LD first, CSS fallback; handle @type as string or list"

requirements-completed:
  - DATA-04
  - DATA-05

# Metrics
duration: 16min
completed: 2026-03-11
---

# Phase 01 Plan 03: Recipe Co-occurrence Processing Summary

**Streamed 2.2M RecipeNLG recipes via HTTP (Python 3.14-compatible workaround) + scraped 76 AllRecipes recipes, producing 5,944,163 ingredient co-occurrence pairs in recipes.csv**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-03-11T20:36:00Z
- **Completed:** 2026-03-11T20:52:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Streamed full 2.2M RecipeNLG dataset via direct HTTP (pandas chunksize) after discovering HuggingFace datasets library is incompatible with Python 3.14
- Scraped AllRecipes politely (browser-like headers, random delays) with bot-block detection and manual fallback message
- Merged both sources into a single 5,944,163-row co-occurrence table sorted by count descending
- Both test_recipes.py and test_allrecipes.py now pass (skip decorators removed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Recipe co-occurrence script** - `23d6dea` (feat)
2. **Task 2: Run recipe pipeline and verify outputs** - `bf17aaf` (feat)

## Files Created/Modified

- `data/scrape_recipes.py` — Streaming RecipeNLG counter + AllRecipes polite scraper + merge logic
- `data/raw/recipes.csv` — 5,944,163 ingredient co-occurrence pairs (ingredient_a, ingredient_b, count)
- `data/raw/recipes_allrecipes.csv` — 76 scraped AllRecipes recipes (recipe_name, ingredients)
- `tests/test_recipes.py` — Removed pytest.skip; now active acceptance test
- `tests/test_allrecipes.py` — Removed pytest.skip; now active acceptance test

## Decisions Made

- **datasets library bypass:** HuggingFace `datasets` 2.x and 3.x both fail on Python 3.14 due to a `dill._batch_setitems()` API change. Switched to direct HTTP streaming of the Mahimas/recipenlg CSV mirror via `requests` + `pandas.read_csv(chunksize=5000)`. This achieves the same streaming/no-OOM goal without the datasets library.
- **Cloudflare detection fix:** AllRecipes legitimately uses Cloudflare as CDN so their pages always contain "cloudflare" in HTML. The original broad check was a false positive. Fixed to only detect actual challenge pages (challenge-form, cf_chl_ tokens, cf-mitigated: challenge header).
- **JSON-LD @type as list:** AllRecipes returns `"@type": ["Recipe"]` (list) rather than `"@type": "Recipe"` (string). Added `_is_recipe_type()` helper.
- **AllRecipes partial coverage:** Only 4 of 10 category URLs returned recipe links (others returned 0 — URL structure likely changed). Scraped 76 recipes contributing 5,824 new pairs. Acceptable since RecipeNLG is the primary data source.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] HuggingFace datasets library incompatible with Python 3.14**
- **Found during:** Task 2 (running the pipeline)
- **Issue:** `datasets.load_dataset()` fails with `TypeError: Pickler._batch_setitems() takes 2 positional arguments but 3 were given` on Python 3.14; both v2.21 and v3.6 affected (dill incompatibility)
- **Fix:** Replaced `load_dataset("mbien/recipe_nlg", streaming=True)` with direct HTTP streaming of the Mahimas/recipenlg CSV mirror: `pd.read_csv(requests.get(url, stream=True).raw, chunksize=5000)`. Removed `from datasets import load_dataset` import. Added `ast` import for `_parse_ner_list()`.
- **Files modified:** data/scrape_recipes.py
- **Verification:** `python3 -c "import ast; ast.parse(...)"` → syntax OK; pipeline runs to completion
- **Committed in:** bf17aaf (Task 2 commit)

**2. [Rule 1 - Bug] AllRecipes Cloudflare detection false positive**
- **Found during:** Task 2 (first pipeline run — AllRecipes showed "blocked after 0 recipes")
- **Issue:** `_is_blocked()` checked `"cloudflare" in response.text.lower()` which triggers on AllRecipes' legitimate CDN references
- **Fix:** Replaced broad cloudflare check with specific challenge indicators: `challenge-form` + `cloudflare` together, `cf_chl_` tokens, `cf-mitigated: challenge` header
- **Files modified:** data/scrape_recipes.py
- **Verification:** Manual test confirmed `_is_blocked(resp)` returns False for normal AllRecipes pages
- **Committed in:** bf17aaf (Task 2 commit)

**3. [Rule 1 - Bug] JSON-LD @type field returned as list not string**
- **Found during:** Task 2 (AllRecipes ingredient extraction returning 0 ingredients)
- **Issue:** AllRecipes JSON-LD contains `"@type": ["Recipe"]` (list) but code compared `item.get("@type") == "Recipe"` (string equality)
- **Fix:** Added `_is_recipe_type()` helper that handles both `str` and `list` @type values
- **Files modified:** data/scrape_recipes.py
- **Verification:** Test extraction on live recipe URL returned 15 ingredients correctly
- **Committed in:** bf17aaf (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking issue)
**Impact on plan:** All fixes necessary for correctness. The datasets library bypass required changing the streaming mechanism but preserved the OOM-safety goal. No scope creep.

## Issues Encountered

- `mbien/recipe_nlg` dataset on HuggingFace requires manual download from the original dataset website — the `load_dataset()` call fails with a manual download error even with `trust_remote_code=True`. Used a CSV mirror (`Mahimas/recipenlg`) that contains the same data in direct HTTP-accessible format.
- AllRecipes category URL structure has changed since RESEARCH.md was written — 6 of 10 category URLs returned 0 recipe links. The scraper logs warnings and continues gracefully, collecting 76 recipes from the 4 working categories.

## User Setup Required

None — no external service configuration required. The script runs standalone with no API keys needed.

## Next Phase Readiness

- `data/raw/recipes.csv` is ready for Phase 3 graph construction as the `co-occurs` edge type
- `data/raw/recipes.csv` is ready for Phase 4 recipe loss component
- All Phase 1 data collection plans (01-01 structure, 01-02 FlavorDB2, 01-03 recipes) are complete
- Plan 01-04 (if exists) can proceed immediately

---
*Phase: 01-foundation*
*Completed: 2026-03-11*
