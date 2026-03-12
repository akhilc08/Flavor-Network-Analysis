---
phase: 01-foundation
verified: 2026-03-11T00:00:00Z
status: gaps_found
score: 8/10 must-haves verified
re_verification: false
gaps:
  - truth: "FooDB CSV join enriches molecules.csv with foodb_matched, macronutrients_json, moisture_content columns"
    status: failed
    reason: "data/raw/foodb/ directory does not exist. FooDB data was never downloaded. join_foodb.py ran, printed download instructions, and returned gracefully — but the join itself never executed. molecules.csv has only 3 columns (pubchem_id, common_name, flavor_profile) with no foodb_matched column."
    artifacts:
      - path: "data/raw/foodb/"
        issue: "Directory missing — FooDB 952MB tar.gz not downloaded from foodb.ca/downloads"
      - path: "data/raw/molecules.csv"
        issue: "Missing foodb_matched, foodb_food_id, macronutrients_json, moisture_content columns — FooDB enrichment not applied"
    missing:
      - "Download FooDB CSV archive from https://foodb.ca/downloads (CC BY-NC 4.0)"
      - "Extract to data/raw/foodb/ (Food.csv and Compound.csv must be present)"
      - "Run: python data/join_foodb.py — should produce >= 300 matched ingredients and add foodb_matched column to molecules.csv"
      - "Update tests/test_foodb.py to remove @pytest.mark.skip decorator"

  - truth: "AllRecipes scraper fetches top 500 recipes from 10 categories"
    status: partial
    reason: "Only 76 recipes were scraped from 4 of 10 target categories. Six category URLs returned zero recipe links due to AllRecipes site structure changes. The pipeline continued without crashing and the partial data was saved, which satisfies the graceful-degradation requirement. However DATA-05 states '500 recipes from 10 categories' — only 76 recipes from 4 categories were achieved."
    artifacts:
      - path: "data/raw/recipes_allrecipes.csv"
        issue: "77 rows (header + 76 recipes) — target was 500 recipes from 10 categories; only 4 of 10 categories yielded any links"
    missing:
      - "Either: update 6 failing category URLs (site structure changed) to reach the 500-recipe target"
      - "Or: accept 76-recipe partial and document that recipes.csv co-occurrence data is dominated by RecipeNLG (5.94M pairs), making AllRecipes supplemental coverage non-critical for Phase 2 gate"
      - "Clarify with project owner whether 76-recipe partial coverage is acceptable for phase sign-off"
human_verification:
  - test: "conda activate flavor-network && python -c 'import torch, torch_geometric, rdkit; print(torch.__version__, torch.backends.mps.is_available())'"
    expected: "Prints torch version starting with 2.6 and True for MPS availability on Apple Silicon M2"
    why_human: "Cannot activate conda environment or verify MPS hardware in automated checks. ENV-01, ENV-02, ENV-03 tests (test_environment.py) require the conda env to be active."
---

# Phase 1: Foundation Verification Report

**Phase Goal:** The project environment runs without version conflicts and all raw ingredient, molecule, and recipe data is cached to disk.
**Verified:** 2026-03-11
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | conda env spec exists with correct channel order (RDKit before PyTorch) | VERIFIED | environment.yml: name=flavor-network, rdkit=2025.03 in conda deps, torch==2.6.* in pip section |
| 2 | All required project directories exist | VERIFIED | data/raw, data/processed, graph, model/embeddings, scoring, app, logs all present |
| 3 | 8 test files exist and test_project_structure passes | VERIFIED | All 8 test files confirmed; test_project_structure.py checks dirs programmatically |
| 4 | FlavorDB2 scraper runs, caches responses, produces >= 900 row ingredients.csv | VERIFIED | 935 rows in ingredients.csv; flavordb_cache.sqlite 81MB exists; scraper code uses allowable_codes=[200,404], expire_after=None |
| 5 | molecules.csv has deduplicated molecules with correct schema | VERIFIED | 1788 rows; columns: pubchem_id, common_name, flavor_profile |
| 6 | FooDB join enriches molecules.csv with foodb_matched column | FAILED | data/raw/foodb/ directory missing; molecules.csv has only 3 columns — no foodb_matched, no macronutrients_json |
| 7 | RecipeNLG streamed without OOM; recipes.csv has > 1M co-occurrence pairs | VERIFIED | 5,944,163 rows; streaming via pd.read_csv chunksize=5000 over HTTP (Python 3.14-safe workaround) |
| 8 | AllRecipes scraper handles blocking gracefully; partial results saved | VERIFIED | 76 recipes saved to recipes_allrecipes.csv; pipeline log shows graceful handling; AllRecipes partial coverage functional |
| 9 | AllRecipes scrapes 500+ recipes from 10 categories | FAILED (partial) | Only 76 recipes from 4 categories; 6 category URLs returned 0 links due to AllRecipes site structure changes |
| 10 | run_pipeline.py orchestrates all stages with --skip-* and --force flags | VERIFIED | All 4 flags present; direct import pattern with per-stage try/except; summary table rendered |

**Score:** 8/10 truths verified (1 failed, 1 partial/failed)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `environment.yml` | conda+pip hybrid spec, rdkit in conda, torch in pip | VERIFIED | Exact spec matches: rdkit=2025.03, torch==2.6.*, torch_geometric==2.7.* |
| `requirements.txt` | Pip-only reference list | VERIFIED | 12 pip packages listed; marked as reference only |
| `README.md` | Quickstart + FooDB + AllRecipes fallback docs | VERIFIED | All required sections present: conda env create, foodb.ca/downloads, recipes_allrecipes.csv format, all 4 pipeline flags |
| `tests/test_environment.py` | test_imports, test_mps_available, test_versions | VERIFIED | All 3 test functions present; MPS skips on non-Darwin; version assertions correct |
| `tests/test_project_structure.py` | test_directories | VERIFIED | Checks all 8 required directories; passes immediately |
| `data/scrape_flavordb.py` | Standalone scraper, requests_cache, tqdm, idempotent | VERIFIED | 172 lines; CachedSession with SQLite, allowable_codes=[200,404], CONSECUTIVE_404_STOP=10, idempotence check |
| `data/raw/ingredients.csv` | >= 900 rows, columns: ingredient_id, name, category, molecules_json | VERIFIED | 935 rows; correct 4-column schema |
| `data/raw/molecules.csv` | >= 1000 rows, columns: pubchem_id, common_name, flavor_profile | VERIFIED | 1788 rows; correct 3-column schema (unenriched — FooDB not available) |
| `data/raw/flavordb_cache.sqlite` | SQLite cache of all HTTP responses | VERIFIED | File exists (81MB per summary) |
| `data/scrape_recipes.py` | Streaming RecipeNLG, AllRecipes scraper, merge logic | VERIFIED | 460 lines; pd.read_csv chunksize streaming; JSON-LD extraction; bot-block detection; Counter merge |
| `data/raw/recipes.csv` | > 1000 rows, ingredient_a, ingredient_b, count | VERIFIED | 5,944,163 rows; correct 3-column schema |
| `data/join_foodb.py` | FooDB fuzzy join, token_sort_ratio, graceful missing-dir handling | VERIFIED (code only) | 334 lines; token_sort_ratio confirmed; join_foodb() returns gracefully when foodb/ absent |
| `data/raw/foodb/` | FooDB CSV source data | MISSING | Directory does not exist — manual download required |
| `run_pipeline.py` | Orchestrator with 4 flags, per-stage isolation, summary table | VERIFIED | 212 lines; direct import of all 3 data scripts; --skip-scrape, --skip-foodb, --skip-recipes, --force |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| environment.yml | conda env create -f environment.yml | conda-forge channel then pip section | VERIFIED | pip: section contains torch==2.6.*; conda-forge channel listed first |
| tests/test_environment.py | import torch, torch_geometric, rdkit | activated conda env | HUMAN NEEDED | Imports succeed in active conda env; cannot verify here |
| data/scrape_flavordb.py | cosylab.iiitd.edu.in/flavordb/entities_json | requests_cache.CachedSession with SQLite | VERIFIED | CachedSession("data/raw/flavordb_cache", backend="sqlite", allowable_codes=[200,404]) confirmed |
| data/scrape_flavordb.py | data/raw/ingredients.csv | pandas DataFrame.to_csv | VERIFIED | scraper writes to OUT_INGREDIENTS via pd.DataFrame(ingredients).to_csv |
| data/scrape_recipes.py | mbien/recipe_nlg (via HTTP mirror) | pd.read_csv(resp.raw, chunksize=5000) | VERIFIED | streaming=True equivalent via chunked HTTP; 5.9M pairs produced |
| data/scrape_recipes.py | data/raw/recipes.csv | Counter merged, pandas to_csv | VERIFIED | nlg_counter + allrecipes_counter merged; to_csv confirmed |
| data/join_foodb.py | data/raw/foodb/ | pandas read_csv for Food.csv and Compound.csv | NOT WIRED | foodb/ directory missing; join never ran |
| data/join_foodb.py | data/raw/ingredients.csv | rapidfuzz.process.extractOne(token_sort_ratio) | VERIFIED (code) | token_sort_ratio confirmed in code; never ran due to missing foodb/ |
| run_pipeline.py | scrape_flavordb, scrape_recipes, join_foodb | direct function import | VERIFIED | from data.scrape_flavordb import scrape_flavordb; all 3 imports confirmed with try/except guards |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ENV-01 | 01-01 | Apple Silicon conda+pip hybrid install | VERIFIED (code); HUMAN for runtime | environment.yml correct; runtime test needs activated env |
| ENV-02 | 01-01 | PyTorch MPS backend on Apple Silicon | HUMAN NEEDED | test_mps_available exists; cannot verify MPS hardware availability programmatically |
| ENV-03 | 01-01 | All dependency versions pinned in environment.yml and requirements.txt | VERIFIED | torch==2.6.*, torch_geometric==2.7.*, rdkit=2025.03 pinned in both files |
| ENV-04 | 01-01 | Project structure: data/, graph/, model/, scoring/, app/ directories | VERIFIED | All 7 directories confirmed present including model/embeddings |
| DATA-01 | 01-02 | FlavorDB2 scraper hits entities_json 1-1000, handles 404s, caches locally | VERIFIED | 935 ingredients scraped; SQLite cache confirmed; 404s cached (allowable_codes=[200,404]) |
| DATA-02 | 01-02 | Scraper extracts name, category, flavor molecule list per entity | VERIFIED | ingredients.csv schema confirmed (ingredient_id, name, category, molecules_json); molecules.csv has pubchem_id, common_name, flavor_profile |
| DATA-03 | 01-04 | FooDB compounds/foods CSVs downloaded; joined via RapidFuzz token_sort_ratio > 85 | BLOCKED | data/raw/foodb/ directory missing; join never executed; molecules.csv not enriched; REQUIREMENTS.md incorrectly marks as [x] |
| DATA-04 | 01-03 | RecipeNLG loaded in streaming/chunked mode, co-occurrence counts written to disk | VERIFIED | pd.read_csv chunksize=5000 over HTTP (datasets library bypassed for Python 3.14 compat); recipes.csv has 5.9M pairs |
| DATA-05 | 01-03 | AllRecipes scrapes top 500 recipes from 10 categories; handles bot-blocking | PARTIAL | 76 recipes from 4 of 10 categories; 6 categories returned 0 links; partial results saved; graceful handling VERIFIED; 500-recipe target not met |
| DATA-06 | 01-04 | Raw data saved as ingredients.csv, molecules.csv, recipes.csv in data/raw/ | VERIFIED | All 3 files exist with correct schemas and row counts above thresholds |

**Orphaned requirements:** None. All 10 requirement IDs (ENV-01 through ENV-04, DATA-01 through DATA-06) appear in plan frontmatter and are accounted for above.

**Note on REQUIREMENTS.md:** DATA-03 is marked `[x]` in REQUIREMENTS.md but the actual join never executed. The checkbox was likely set prematurely when join_foodb.py was created (which handles missing FooDB gracefully). This is a documentation inaccuracy — DATA-03 is BLOCKED, not satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| tests/test_foodb.py | 17 | `@pytest.mark.skip(reason="FooDB join not yet run")` | Warning | test_foodb.py still skipped — expected given FooDB not downloaded, but inconsistent with other completed test files which had skips removed |
| data/raw/molecules.csv | — | Missing foodb_matched column | Blocker | DATA-03 not satisfied; Phase 3 graph construction depends on this column for FooDB concentration edge weights (GRAPH-04) |

No placeholder comments, empty implementations, or console.log-only stubs found in production scripts. The `return []` occurrences in scrape_recipes.py are legitimate error-handling early returns in helper functions, not stubs.

### Human Verification Required

#### 1. Environment import and MPS test

**Test:** With the conda environment active, run:
```bash
conda activate flavor-network
python -c "import torch, torch_geometric, rdkit; print(torch.__version__, torch.backends.mps.is_available())"
python -m pytest tests/test_environment.py -v
```
**Expected:** torch version starting with "2.6", MPS returns True, all 3 tests pass.
**Why human:** Cannot activate conda environment in automated checks. ENV-01, ENV-02, ENV-03 all require the activated env.

#### 2. AllRecipes 500-recipe target assessment

**Test:** Review whether 76-recipe partial coverage (from 4 of 10 categories) is acceptable for phase sign-off.
**Expected:** Project owner decision — either accept the partial as sufficient (RecipeNLG provides 5.9M pairs, making AllRecipes truly supplemental) or require updated category URLs.
**Why human:** Business decision about whether DATA-05 "top 500 recipes" language is a hard gate or aspirational target.

### Gaps Summary

Two gaps block full goal achievement:

**Gap 1 (BLOCKER) — DATA-03 FooDB join never executed:**
FooDB is a 952MB manual download under CC BY-NC 4.0 that must be downloaded from foodb.ca/downloads and extracted to `data/raw/foodb/`. The join script (data/join_foodb.py) is fully implemented and correct — it handles the missing directory gracefully and is ready to run. However, no FooDB data has been downloaded, so molecules.csv has only 3 columns instead of the required 7. This directly blocks Phase 3 graph construction requirement GRAPH-04 (FooDB concentration edge weights) and means test_foodb.py is still skipped.

**Gap 2 (PARTIAL) — DATA-05 AllRecipes partial coverage:**
The AllRecipes scraper collected 76 recipes from 4 of 10 target categories. Six category URLs returned zero recipe links due to AllRecipes site restructuring. The 500-recipe target was not met. The practical impact is low since RecipeNLG provides 5,939,145 co-occurrence pairs (99.9% of the total merged dataset), making the 5,824 AllRecipes pairs genuinely supplemental. However, DATA-05 as written requires "top 500 recipes from 10 categories" and was not achieved. This requires a project owner decision on whether to accept partial coverage or fix the 6 failing category URLs.

**What is working well:** The FlavorDB2 scraper, RecipeNLG processing, run_pipeline.py orchestrator, all environment artifacts, and project structure are fully implemented and verified. The core data pipeline is functional. FooDB enrichment is a data availability issue, not a code issue.

---

_Verified: 2026-03-11_
_Verifier: Claude (gsd-verifier)_
