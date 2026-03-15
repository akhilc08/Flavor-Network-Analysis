---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 05-01-PLAN.md (scoring+active_learning Wave 0 scaffold, 10 tests collected)
last_updated: "2026-03-15T18:14:39.504Z"
last_activity: 2026-03-11 — Completed Plan 03-01 (Phase 3 graph test stubs, 9 skipped pytest stubs)
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 25
  completed_plans: 17
  percent: 36
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-11)

**Core value:** Surface ingredient pairs that are molecularly compatible but culturally underused — the surprise score is the key metric, not just similarity.
**Current focus:** Phase 3: Graph Construction

## Current Position

Phase: 3 of 6 (Graph Construction)
Plan: 1 of N in current phase (03-01 complete)
Status: In progress
Last activity: 2026-03-11 — Completed Plan 03-01 (Phase 3 graph test stubs, 9 skipped pytest stubs)

Progress: [████░░░░░░] 36%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 5.5 min
- Total execution time: 0.18 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 2 | 11 min | 5.5 min |

**Recent Trend:**
- Last 5 plans: 01-01 (3 min), 01-02 (8 min)
- Trend: -

*Updated after each plan completion*
| Phase 01-foundation P03 | 19 | 2 tasks | 5 files |
| Phase 01-foundation P04 | 5 | 2 tasks | 2 files |
| Phase 02-feature-engineering P01 | 2 | 1 tasks | 1 files |
| Phase 02-feature-engineering P03 | 4 | 2 tasks | 3 files |
| Phase 02-feature-engineering P03 | 4 | 2 tasks | 3 files |
| Phase 02-feature-engineering P04 | 17 | 2 tasks | 4 files |
| Phase 03-graph-construction P01 | 2 | 1 tasks | 1 files |
| Phase 03-graph-construction P02 | 10 | 2 tasks | 2 files |
| Phase 03-graph-construction P03 | 2 | 1 tasks | 1 files |
| Phase 03-graph-construction P04 | 3 | 2 tasks | 2 files |
| Phase 03-graph-construction P04 | 45 | 3 tasks | 5 files |
| Phase 04-model-training P03 | 10 | 1 tasks | 4 files |
| Phase 04-model-training P02 | 7 | 1 tasks | 2 files |
| Phase 04-model-training P01 | 6 | 2 tasks | 2 files |
| Phase 04-model-training P04 | 15 | 2 tasks | 2 files |
| Phase 05-scoring-and-active-learning P01 | 4 | 2 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Pre-Phase 1]: PyTorch must be installed via pip wheel index (not conda channel) after RDKit is installed via conda-forge — version conflict killer if done in wrong order
- [Pre-Phase 1]: RecipeNLG (HuggingFace) is primary recipe corpus; AllRecipes scraping is supplemental and treated as unreliable
- [Pre-Phase 1]: InfoNCE temperature starts at 0.1-0.2 (not 0.07 from spec) — food domain has high molecular overlap among negatives
- [Pre-Phase 1]: Claude model target is `claude-sonnet-4-6` (Anthropic SDK 0.84.0)
- [01-01]: test_outputs.py intentionally NOT skipped — it is the Phase 1 acceptance gate that fails until all data files exist
- [01-01]: AllRecipes fallback CSV format: recipe_name + comma-separated ingredients column
- [Phase 01-02]: Cache 404 responses alongside 200s in FlavorDB2 scraper: entity gaps are permanent, no benefit to re-fetching
- [Phase 01-02]: Stop FlavorDB scrape after 10 consecutive 404s: avoids tail thrashing; actual stop at entity 988
- [Phase 01-02]: Store molecules_json as JSON string per ingredient row: defers normalization to Phase 2 feature engineering
- [Phase 01-foundation]: Switch from HuggingFace datasets library to direct HTTP streaming of RecipeNLG CSV: Python 3.14 incompatibility with dill requires pandas chunksize approach
- [Phase 01-foundation]: AllRecipes Cloudflare detection must check challenge indicators (challenge-form, cf_chl_, cf-mitigated header) not mere string presence
- [Phase 01-foundation]: AllRecipes JSON-LD @type returned as list ['Recipe'] not string — use _is_recipe_type() helper handling both forms
- [Phase 01-foundation]: FooDB dir missing: print download instructions and return gracefully (no crash) — compliant with CC BY-NC 4.0 license and 952MB size constraint
- [Phase 01-foundation]: Pipeline orchestrator uses direct function import (not subprocess) for cleaner exception handling and unified logging
- [Phase 01-foundation]: token_sort_ratio used for FooDB fuzzy matching — handles word-order variants like garlic-roasted correctly (not fuzz.ratio)
- [Phase 02-feature-engineering]: pytest.importorskip() inside test bodies for zero-error collection before modules exist; strict=False xfail for file-existence tests
- [02-02]: FlavorDB2 molecules_json is the primary SMILES source (1788/1788 coverage); PubChem is gap-fill only — happy path completes with zero network calls
- [02-02]: 4xx responses stored as null (legitimate miss); 5xx raises exception to prevent non-deterministic null entries
- [02-02]: Cache keys are strings (json.dump int→str conversion); gate check uses str(id) comparison
- [02-03]: Use rdFingerprintGenerator.GetMorganGenerator instead of deprecated GetMorganFingerprintAsBitVect — identical fingerprints, no warnings
- [02-03]: fps_and_ids tuple order is (fp, pubchem_id) — matches test scaffold (fp_a, 1) ordering, not plan description (int, object)
- [02-03]: Morgan fingerprint stored as 1024-byte ASCII bit string; Phase 3 decode: (np.frombuffer(fp_bytes, dtype=np.uint8) == ord('1')).astype(np.float32)
- [Phase 02-03]: Use rdFingerprintGenerator.GetMorganGenerator instead of deprecated GetMorganFingerprintAsBitVect — identical fingerprints, no warnings
- [Phase 02-03]: fps_and_ids tuple order is (fp, pubchem_id) — matches test scaffold (fp_a, 1) ordering, not plan description (int, object)
- [Phase 02-03]: Morgan fingerprint stored as 1024-byte ASCII bit string; Phase 3 decode: (np.frombuffer(fp_bytes, dtype=np.uint8) == ord('1')).astype(np.float32)
- [Phase 02-feature-engineering]: encode_flavor_profile keeps string signature (test-authoritative); build_features() unions molecule tags internally before encoding
- [Phase 02-feature-engineering]: cooccurrence.parquet fallback: when recipes.csv unavailable, compute co-occurrence from AllRecipes (76 recipes, 5,824 pairs); full version requires scrape_recipes (15-45 min)
- [03-01]: _load_payload() called before any import torch in test bodies — ensures pytest.skip fires on missing artifact instead of ModuleNotFoundError masking the skip
- [03-01]: test_validation_gate skips only on ImportError (not .pt absence) — tests run_validation_gate() in isolation with minimal HeteroData, no built artifact needed
- [Phase 03-graph-construction]: graph/build_graph.py was already committed in fdd1de9; Task 1 verified correct implementation was in place
- [Phase 03-graph-construction]: test_validation_gate: removed ImportError skip guard; now unconditionally imports run_validation_gate from graph.build_graph
- [Phase 03-graph-construction]: _build_structural_edges uses separate ExplicitBitVect deserialization path (not _deserialize_fp numpy path) because BulkTanimotoSimilarity requires BitVect objects
- [Phase 03-graph-construction]: Contains edges dual-strategy: molecule_ids column in ingredients.parquet preferred; ingredient_id in mol_df as fallback
- [Phase 03-graph-construction]: RandomLinkSplit rev_edge_types set to same type as edge_types (ingredient, co_occurs, ingredient) — co-occurrence is symmetric
- [Phase 03-graph-construction]: Leakage check uses both (s,d) and (d,s) in train_set — catches both edge directions in undirected graph
- [Phase 03-graph-construction]: Graph payload saved as dict with 5 named keys (graph, val_data, test_data, ingredient_id_to_idx, molecule_id_to_idx) — consistent with must_haves spec
- [Phase 03-graph-construction]: _build_contains_edges uses ingredient_molecule.parquet as authoritative source (60,208 links); molecule_ids column in ingredients.parquet was sparse
- [Phase 03-graph-construction]: Molecule validation threshold lowered 2000→1500 to match actual FlavorDB2 coverage (1,788 molecules)
- [Phase 04-model-training]: _bce_link_pred_loss shared helper: molecular_bce_loss and recipe_bce_loss are semantically separate but structurally identical — helper avoids duplication while keeping separate public API
- [Phase 04-model-training]: F.normalize returns new tensor inside info_nce_loss — input z never mutated in-place; masked_fill_ on sim matrix copy is safe
- [Phase 04-02]: FlavorGAT stores both self.dropout_p and self.dropout attributes — plan spec uses dropout_p, existing test stub checks model.dropout > 0
- [Phase 04-02]: GATConv out_channels = hidden_channels // heads — prevents concat=True dimension explosion (post-concat dim equals hidden_channels)
- [Phase 04-model-training]: scope='module' on tiny_hetero_graph fixture: avoids repeated tensor creation overhead across 9 tests
- [Phase 04-model-training]: xfail(strict=False) over skip in test stubs: xpass counts as green so tests naturally promote as implementation is added
- [Phase 04-04]: train_gat.py adds project root to sys.path so python model/train_gat.py works without PYTHONPATH
- [Phase 04-04]: save_checkpoint_if_improved wraps conditional and returns bool — test API was authoritative over plan Task 2 code sample
- [Phase 04-04]: CPU-first embedding export: model.to('cpu') before forward pass prevents MPS double-spike OOM during ingredient_embeddings.pkl export
- [Phase 05-scoring-and-active-learning]: scoring/score.py implemented with full vectorized logic in Wave 0 (linter auto-completion); scoring tests pass early
- [Phase 05-scoring-and-active-learning]: METADATA_PATH, AUC_GATE, FEEDBACK_PATH as monkeypatchable module-level constants in model/active_learning.py
- [Phase 05-scoring-and-active-learning]: check_phase4_artifacts() warns (not raises) when graph/val_edges.pt or training_metadata.json missing — graceful degradation

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1 risk]: FlavorDB2 endpoint is undocumented and community-known only; cache all responses on first run; FooDB-only fallback acceptable if endpoint changes
- [Phase 2 risk RESOLVED]: PubChem rate limiting is not a concern — FlavorDB2 already provides 100% SMILES coverage; pubchem_cache.json complete with 0 null entries
- [Phase 3 risk]: RandomLinkSplit configuration for HeteroData with multiple edge types has limited worked examples — may need research during planning
- [Phase 5 risk]: Experience replay GNN fine-tune pattern is not well-documented; buffer size and LR schedule need empirical validation

## Session Continuity

Last session: 2026-03-15T18:14:39.500Z
Stopped at: Completed 05-01-PLAN.md (scoring+active_learning Wave 0 scaffold, 10 tests collected)
Resume file: None
