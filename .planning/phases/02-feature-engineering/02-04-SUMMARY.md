---
phase: 02-feature-engineering
plan: "04"
subsystem: feature-engineering
tags: [multimodal-features, texture, temperature, cultural-context, flavor-profile, parquet, pipeline]
dependency_graph:
  requires: [02-03]
  provides: [ingredients.parquet, cooccurrence.parquet]
  affects: [03-graph-construction]
tech_stack:
  added: []
  patterns:
    - "Path-or-DataFrame polymorphic function signature (build_cultural_context_vectors)"
    - "AllRecipes co-occurrence fallback when recipes.csv unavailable"
    - "Moisture content override for texture encoding (< 10% crispy, > 80% soft)"
key_files:
  created:
    - data/processed/ingredients.parquet
    - data/processed/cooccurrence.parquet
  modified:
    - data/build_features.py
    - run_pipeline.py
decisions:
  - "encode_flavor_profile keeps string signature (test-authoritative); build_features() unions molecule tags internally before encoding"
  - "build_cultural_context_vectors accepts Path or DataFrame via isinstance check — supports both CLI (path) and unit test (DataFrame) usage"
  - "cooccurrence.parquet fallback: when recipes.csv unavailable, compute co-occurrence from AllRecipes (76 recipes, 5,824 pairs) — same schema, full version requires scrape_recipes"
  - "cooccurrence.parquet fallback noted with WARNING log message; regeneration instructions provided"
metrics:
  duration: "15 min"
  completed_date: "2026-03-11"
  tasks_completed: 2
  files_modified: 2
  files_created: 2
---

# Phase 2 Plan 4: Multimodal Ingredient Features Summary

Completed `data/build_features.py` with the full multimodal ingredient feature layer (texture, temperature, cultural context, flavor profile multi-hot) and wired `build_features()` into `run_pipeline.py` as a stage with `--skip-features` flag. Produces `ingredients.parquet` (935 rows, 598-dim flavor vocab) and `cooccurrence.parquet` from available recipe data.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add multimodal feature functions to build_features.py | edb60ad | data/build_features.py |
| 2 | Complete build_features pipeline — write parquets and wire run_pipeline.py | 64f6bee | data/build_features.py, run_pipeline.py |

## Outputs Produced

| File | Rows | Notes |
|------|------|-------|
| `data/processed/ingredients.parquet` | 935 | ingredient_id, name, category + 5 texture + 4 temperature + 10 cultural_context + 598 flavor_profile cols |
| `data/processed/cooccurrence.parquet` | 5,824 | Co-occurrence pairs from AllRecipes fallback (76 recipes); full version requires recipes.csv |
| `data/processed/molecules.parquet` | 1,788 | Already existed from Plan 02-03 |
| `data/processed/tanimoto_edges.parquet` | 1,678 | Already existed from Plan 02-03 |

## Verification

All 13 tests in `tests/test_features.py` pass:

```
13 xpassed in 3.77s
```

Feature vector dimensions confirmed:
- Texture: 5-dim one-hot (crispy/soft/creamy/chewy/crunchy)
- Temperature: 4-dim one-hot (raw/cold/warm/hot)
- Cultural context: 10-dim one-hot (Italian/Asian/Mexican/French/American/Indian/Mediterranean/Middle Eastern/Japanese/Thai)
- Flavor profile: 598-dim multi-hot (vocabulary built from all FlavorDB2 molecules, sorted for determinism)

Total feature vector per ingredient: 5 + 4 + 10 + 598 = **617 dimensions**

Pipeline stage stats:
- Ingredients: 935
- Flavor vocab size: 598
- Cultural context matched: 460 ingredients appeared in AllRecipes recipes
- Cooccurrence written from AllRecipes fallback: 5,824 pairs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] encode_flavor_profile signature mismatch**
- **Found during:** Task 1 implementation analysis
- **Issue:** Plan spec said `encode_flavor_profile(molecule_rows: list[dict], vocab_index)` but test uses `encode_flavor_profile("sweet@floral", vocab_index)` with a string
- **Fix:** Kept string-based signature (test-authoritative). `build_features()` internally unions molecule tags into a single @-delimited string before calling `encode_flavor_profile`
- **Files modified:** data/build_features.py
- **Commit:** edb60ad

**2. [Rule 2 - Missing functionality] build_cultural_context_vectors needed Path support**
- **Found during:** Task 2 integration
- **Issue:** Existing function only accepted DataFrame; `build_features()` needs to call it with a Path constant
- **Fix:** Updated to accept `Path | str | DataFrame` via `isinstance` check
- **Files modified:** data/build_features.py
- **Commit:** edb60ad

**3. [Rule 2 - Missing functionality] cooccurrence.parquet fallback for missing recipes.csv**
- **Found during:** Task 2 — `recipes.csv` is gitignored and requires 15-45 min RecipeNLG scrape
- **Issue:** Without cooccurrence.parquet, `test_parquet_outputs_exist` would remain xfail
- **Fix:** Added AllRecipes-based fallback: when `recipes.csv` unavailable, extract co-occurrence pairs from the 76 AllRecipes recipes (same schema: ingredient_a, ingredient_b, count). Logs WARNING with regeneration instructions
- **Files modified:** data/build_features.py
- **Commit:** 64f6bee

### Deferred Items

- **recipes.csv (full co-occurrence):** Requires running `scrape_recipes.py` (RecipeNLG streaming, 15-45 min). After completion, re-run `build_features --force` to regenerate `cooccurrence.parquet` with full 5.9M pairs. Current placeholder has 5,824 pairs from 76 AllRecipes recipes.
- **ingredients.csv was missing from git** (gitignored large file): Required re-running `scrape_flavordb.py` to regenerate (5:41 runtime using 3.45 req/s, stopped at 987/1100 due to consecutive 404s at entity boundary). File regenerated successfully with 935 rows.

## Self-Check

Files exist:
- `data/processed/ingredients.parquet` — FOUND
- `data/processed/cooccurrence.parquet` — FOUND
- `data/processed/molecules.parquet` — FOUND
- `data/processed/tanimoto_edges.parquet` — FOUND

Commits exist:
- edb60ad — FOUND
- 64f6bee — FOUND

## Self-Check: PASSED
