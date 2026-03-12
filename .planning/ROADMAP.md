# Roadmap: Flavor Pairing Network

## Overview

This project builds a staged ML artifact pipeline — data ingestion through a trained GAT model and surprise scoring engine — then surfaces it through a 4-page Streamlit demo. Phases are hard-sequential: each phase produces disk artifacts that gate the next. The demo is complete when a user can search ingredients, explore the flavor graph, rate uncertain pairs to improve the model, and generate AI-backed recipes with molecular rationale.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Environment setup and raw data ingestion; produces working conda environment and populated data/raw/ (completed 2026-03-12)
- [ ] **Phase 2: Feature Engineering** - PubChem SMILES fetch, RDKit descriptors, and multimodal ingredient feature assembly; produces data/processed/ parquets
- [ ] **Phase 3: Graph Construction** - Heterogeneous HeteroData graph with validation gate and leakage-free link prediction split; produces graph/hetero_data.pt
- [ ] **Phase 4: Model Training** - 3-layer GAT with dual supervision and InfoNCE loss trained to AUC >= 0.70; produces ingredient_embeddings.pkl
- [ ] **Phase 5: Scoring and Active Learning** - Surprise score formula over all pairs plus fine-tuning loop with experience replay; produces scoring/scored_pairs.pkl and working active learning module
- [ ] **Phase 6: Streamlit UI** - Complete 4-page demo: ingredient search, active learning rating, flavor graph explorer, Claude recipe generation

## Phase Details

### Phase 1: Foundation
**Goal**: The project environment runs without version conflicts and all raw ingredient, molecule, and recipe data is cached to disk.
**Depends on**: Nothing (first phase)
**Requirements**: ENV-01, ENV-02, ENV-03, ENV-04, DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06
**Success Criteria** (what must be TRUE):
  1. `conda activate` succeeds and `python -c "import torch, torch_geometric, rdkit"` runs without errors on Apple Silicon
  2. `data/raw/ingredients.csv`, `molecules.csv`, and `recipes.csv` exist and contain data from at least FlavorDB2 and RecipeNLG
  3. FlavorDB2 scraper can be re-run without hitting the network (all responses cached locally)
  4. AllRecipes scraper logs a documented failure rate and the pipeline continues without crashing if scraping is blocked
  5. FooDB CSV join reports how many ingredients matched via fuzzy matching before proceeding
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md — Environment spec (environment.yml, README, test scaffold)
- [ ] 01-02-PLAN.md — FlavorDB2 scraper (ingredients.csv, molecules.csv)
- [ ] 01-03-PLAN.md — Recipe co-occurrence (RecipeNLG streaming + AllRecipes, recipes.csv)
- [ ] 01-04-PLAN.md — FooDB join + run_pipeline.py orchestrator

### Phase 2: Feature Engineering
**Goal**: Every ingredient has a complete multimodal feature vector and every molecule has RDKit descriptors and Morgan fingerprints, with all gaps logged and reported.
**Depends on**: Phase 1
**Requirements**: FEAT-01, FEAT-02, FEAT-03, FEAT-04, FEAT-05, FEAT-06, FEAT-07, FEAT-08, FEAT-09
**Success Criteria** (what must be TRUE):
  1. `data/processed/` contains parquet files for ingredients, molecules, and co-occurrence data
  2. PubChem SMILES cache (`pubchem_cache.json`) covers 100% of requested molecule IDs before RDKit processing begins
  3. RDKit sanitization failures are logged by ingredient and molecule name — running the script twice produces identical logs (deterministic)
  4. Tanimoto similarity edges for molecule pairs with similarity > 0.7 are computed and saved
  5. Each ingredient's feature vector includes texture, temperature affinity, cultural context, and flavor profile components
**Plans**: 4 plans

Plans:
- [ ] 02-01-PLAN.md — Test scaffold (tests/test_features.py: all 13 FEAT-01..09 test stubs, xfail)
- [ ] 02-02-PLAN.md — fetch_smiles.py (FlavorDB2 extraction + PubChem gap-fill → pubchem_cache.json)
- [ ] 02-03-PLAN.md — build_features.py RDKit layer (descriptors, Morgan FPs, Tanimoto edges → molecules.parquet, tanimoto_edges.parquet)
- [ ] 02-04-PLAN.md — build_features.py multimodal layer (texture, temperature, cultural context, flavor profile → ingredients.parquet, cooccurrence.parquet)

### Phase 3: Graph Construction
**Goal**: A validated heterogeneous graph exists on disk with all three edge types, explicit index mappings, and a leakage-free link prediction split.
**Depends on**: Phase 2
**Requirements**: GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-05, GRAPH-06, GRAPH-07, GRAPH-08, GRAPH-09
**Success Criteria** (what must be TRUE):
  1. `graph/hetero_data.pt` loads successfully and reports >= 500 ingredient nodes and >= 2000 molecule nodes
  2. All three edge types (contains, co-occurs, structurally-similar) are present in the loaded graph
  3. The validation gate blocks execution with a clear error message if node/edge thresholds are not met
  4. An assertion confirms zero overlap between test edge labels and the message-passing edge_index before training is permitted
  5. `ingredient_id_to_idx` and `molecule_id_to_idx` dicts are saved alongside the graph for downstream use
**Plans**: 4 plans

Plans:
- [ ] 03-01-PLAN.md — Test stubs for all GRAPH requirements (Wave 0)
- [ ] 03-02-PLAN.md — Node feature construction (index dicts, ingredient.x, molecule.x)
- [ ] 03-03-PLAN.md — Edge construction (contains, co-occurs, structurally-similar)
- [ ] 03-04-PLAN.md — Graph assembly, validation gate, link prediction split, save

### Phase 4: Model Training
**Goal**: A trained GAT checkpoint exists that achieves validation AUC >= 0.70, with 128-dim ingredient embeddings exported and ready for scoring.
**Depends on**: Phase 3
**Requirements**: MODEL-01, MODEL-02, MODEL-03, MODEL-04, MODEL-05, MODEL-06, MODEL-07, MODEL-08, MODEL-09
**Success Criteria** (what must be TRUE):
  1. Training completes 200 epochs without OOM crash on Apple Silicon MPS backend
  2. Best validation AUC is logged to console; checkpoint is saved only when AUC improves
  3. InfoNCE loss is logged as a separate component (not merged into the combined loss number)
  4. `model/embeddings/ingredient_embeddings.pkl` exists and contains a 128-dim vector for every ingredient in the graph
  5. Validation AUC >= 0.70 is reached (required gate before active learning is enabled)
**Plans**: 4 plans

Plans:
- [ ] 04-01-PLAN.md — Test scaffold (tests/test_model.py stubs + conftest.py HeteroData fixture)
- [ ] 04-02-PLAN.md — FlavorGAT model class (model/gat_model.py: HeteroConv + GATConv, BN, projections)
- [ ] 04-03-PLAN.md — Loss functions (model/losses.py: molecular BCE, recipe BCE, InfoNCE, combined)
- [ ] 04-04-PLAN.md — Training script + embedding export (model/train_gat.py: full loop, checkpoints, CSV log, pkl export)

### Phase 5: Scoring and Active Learning
**Goal**: Every ingredient pair has a calibrated surprise score on disk, and the active learning loop can accept user ratings and fine-tune the model without catastrophic forgetting.
**Depends on**: Phase 4
**Requirements**: SCORE-01, SCORE-02, SCORE-03, SCORE-04, LEARN-01, LEARN-02, LEARN-03, LEARN-04, LEARN-05, LEARN-06
**Success Criteria** (what must be TRUE):
  1. `scoring/scored_pairs.pkl` loads and contains surprise scores for ingredient pairs, each labeled "Surprising", "Unexpected", or "Classic"
  2. The top-20 most uncertain pairs (pairing_score closest to 0.5) can be queried programmatically
  3. Submitting a rating appends a row to `feedback.csv` and triggers a 10-epoch fine-tune with experience replay
  4. A checkpoint is saved before each fine-tune round and can be used to restore the pre-fine-tune state
  5. After fine-tuning, validation AUC before and after are both available as values (not just printed to console)
**Plans**: 3 plans

Plans:
- [ ] 05-01-PLAN.md — Wave 0: test stubs (tests/test_scoring.py, tests/test_active_learning.py) and API stubs (scoring/score.py, model/active_learning.py)
- [ ] 05-02-PLAN.md — Scoring module: vectorized compute_all_pairs, all public API functions, standalone compute_scores.py
- [ ] 05-03-PLAN.md — Active learning module: submit_rating, is_active_learning_enabled, fine_tune_with_replay with experience replay

### Phase 6: Streamlit UI
**Goal**: A polished 4-page Streamlit demo runs end-to-end: users can search ingredients, rate uncertain pairs to improve the model, explore the flavor graph, and generate AI-backed recipes — with no raw stack traces visible.
**Depends on**: Phase 5
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07
**Success Criteria** (what must be TRUE):
  1. Page 1 returns top 10 pairings for a searched ingredient, with a Plotly radar chart and shared flavor molecules visible
  2. Page 2 shows 5 uncertain pairs, accepts star ratings, triggers fine-tuning, and displays AUC delta after completion
  3. Page 3 renders a PyVis graph centered on a selected ingredient with <= 50 nodes; clicking a node re-centers the graph on that ingredient
  4. Page 4 generates a recipe via Claude API (`claude-sonnet-4-6`) that includes molecular pairing rationale — the recipe is readable and references specific shared compounds
  5. All four pages load without raw Python tracebacks visible to the user under normal operation
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 4/4 | Complete   | 2026-03-12 |
| 2. Feature Engineering | 0/4 | Planned | - |
| 3. Graph Construction | 0/TBD | Not started | - |
| 4. Model Training | 0/4 | Planned | - |
| 5. Scoring and Active Learning | 0/3 | Planned | - |
| 6. Streamlit UI | 0/TBD | Not started | - |
