# Requirements: Flavor Pairing Network

**Defined:** 2026-03-11
**Core Value:** Surface ingredient pairs that are molecularly compatible but culturally underused — the surprise score is the key metric, not just similarity.

## v1 Requirements

### Environment Setup

- [x] **ENV-01**: Project runs on Apple Silicon (M2) using conda+pip hybrid install (RDKit via conda-forge, PyTorch via pip wheel index)
- [x] **ENV-02**: PyTorch uses MPS backend on Apple Silicon for training acceleration
- [x] **ENV-03**: All dependency versions pinned in environment.yml and requirements.txt (PyTorch 2.6, PyG 2.7, RDKit 2025.03)
- [x] **ENV-04**: Project structure matches spec: data/, graph/, model/, scoring/, app/ directories

### Data Ingestion

- [ ] **DATA-01**: FlavorDB2 scraper hits entities_json?id=1–1000, handles 404s gracefully, caches all responses locally on first run
- [ ] **DATA-02**: Scraper extracts ingredient name, category, and flavor molecule list (pubchem_id, common_name, flavor_profile) per entity
- [ ] **DATA-03**: FooDB compounds and foods CSVs downloaded; joined to ingredients via fuzzy name matching (RapidFuzz token_sort_ratio > 85) to enrich with macronutrients, moisture content, additional compounds
- [ ] **DATA-04**: RecipeNLG dataset loaded via HuggingFace in streaming/chunked mode (not fully into RAM) and processed into ingredient co-occurrence counts written to disk
- [ ] **DATA-05**: AllRecipes scraper fetches top 500 recipes from 10 categories (Italian, Asian, Mexican, French, American, Indian, Mediterranean, Middle Eastern, Japanese, Thai); handles bot-blocking gracefully and logs failure rate; user can manually supply data if scraper is blocked
- [ ] **DATA-06**: Raw data saved as ingredients.csv, molecules.csv, recipes.csv in data/raw/

### Feature Engineering

- [ ] **FEAT-01**: PubChem API fetches canonical SMILES per pubchem_id with async httpx, token-bucket rate limiting (≤400 req/min), and full local cache (pubchem_cache.json); missing SMILES logged and reported
- [ ] **FEAT-02**: RDKit computes molecular descriptors from SMILES: MW, logP, HBD, HBA, rotatable bonds, TPSA; sanitization failures logged with ingredient/molecule name
- [ ] **FEAT-03**: RDKit computes Morgan fingerprints (radius=2, 1024 bits) per molecule
- [ ] **FEAT-04**: Tanimoto similarity computed between all molecule pairs; pairs with similarity > 0.7 recorded as structural similarity edges
- [ ] **FEAT-05**: Texture embedding computed per ingredient (crispy/soft/creamy/chewy/crunchy) via lookup from category + moisture content
- [ ] **FEAT-06**: Temperature affinity computed per ingredient (raw/cold/warm/hot) via hand-coded lookup table
- [ ] **FEAT-07**: Cultural context vector computed per ingredient: one-hot over 10 cuisine categories derived from recipe co-occurrence data
- [ ] **FEAT-08**: Flavor profile multi-hot vector encoded per ingredient from flavor_profile tags (sweet/sour/umami/bitter/floral/smoky etc.)
- [ ] **FEAT-09**: Processed features written to data/processed/ as parquet files before graph construction

### Graph Construction

- [ ] **GRAPH-01**: Heterogeneous graph constructed manually as PyTorch Geometric HeteroData (not via from_networkx()); explicit ingredient_id_to_idx and molecule_id_to_idx dicts maintained
- [ ] **GRAPH-02**: Ingredient nodes feature vector = concat([multimodal features, mean-pooled Morgan fingerprints, flavor profile vector])
- [ ] **GRAPH-03**: Molecule nodes feature vector = RDKit descriptors + Morgan fingerprints
- [ ] **GRAPH-04**: Ingredient→Molecule "contains" edges with weight = FooDB concentration if available, else 1.0
- [ ] **GRAPH-05**: Ingredient→Ingredient "co-occurs" edges with weight = normalized co-occurrence count across all recipes
- [ ] **GRAPH-06**: Molecule→Molecule "structurally similar" edges for Tanimoto similarity > 0.7
- [ ] **GRAPH-07**: Graph passes validation gate: ≥500 ingredient nodes, ≥2000 molecule nodes, all 3 edge types present; gate blocks training if not met
- [ ] **GRAPH-08**: Link prediction train/val/test split created with zero test-edge leakage (test edges excluded from message-passing graph); leakage asserted before training begins
- [ ] **GRAPH-09**: Graph saved as graph/hetero_data.pt

### Model Training

- [ ] **MODEL-01**: GAT model implemented with HeteroConv wrapper: 3 layers, 8 attention heads, 256 hidden dim, separate linear projections per node type to shared 128-dim embedding space
- [ ] **MODEL-02**: GATConv layers use add_self_loops=False on all bipartite edge types
- [ ] **MODEL-03**: Batch normalization and dropout (0.3) applied between layers
- [ ] **MODEL-04**: Molecular loss: BCE link prediction on ingredient pairs sharing >5 flavor molecules (label=1) vs 0 shared (label=0)
- [ ] **MODEL-05**: Recipe loss: BCE link prediction on ingredient pairs co-occurring in >10 recipes (label=1)
- [ ] **MODEL-06**: InfoNCE contrastive loss with temperature τ starting at 0.1–0.2 (not 0.07); gradient clipping (max_norm=1.0) applied unconditionally; InfoNCE loss logged separately from other components
- [ ] **MODEL-07**: Combined loss: α=0.4 × molecular_loss + β=0.4 × recipe_loss + γ=0.2 × contrastive_loss; α/β/γ tunable
- [ ] **MODEL-08**: Training runs 200 epochs, Adam optimizer lr=1e-3, cosine LR schedule, MPS backend; best checkpoint saved by validation AUC
- [ ] **MODEL-09**: Ingredient embeddings (128-dim dict) exported to model/embeddings/ingredient_embeddings.pkl after training

### Scoring

- [ ] **SCORE-01**: Surprise score computed for all ingredient pairs: pairing_score × (1 - recipe_familiarity) × (1 - molecular_overlap × 0.5)
- [ ] **SCORE-02**: pairing_score = dot product of embeddings; molecular_overlap = Jaccard of shared molecules; recipe_familiarity = co_occurrence_count / max_co_occurrence
- [ ] **SCORE-03**: All pairs sorted by surprise_score descending and persisted to scoring/scored_pairs.pkl before app launch
- [ ] **SCORE-04**: Human-readable surprise label assigned alongside float score ("Surprising", "Unexpected", "Classic")

### Active Learning

- [ ] **LEARN-01**: feedback.csv maintained with columns: ingredient_a, ingredient_b, user_rating (1–5), timestamp
- [ ] **LEARN-02**: Active learning query surfaces top-20 pairs where pairing_score is closest to 0.5 (maximum model uncertainty)
- [ ] **LEARN-03**: On user rating submission: append to feedback.csv, fine-tune model for 10 epochs using experience replay (feedback batch mixed with 5× original training pairs), learning rate 10× lower than base
- [ ] **LEARN-04**: Model checkpoint saved before each fine-tune round; embeddings and scored_pairs re-exported after fine-tuning
- [ ] **LEARN-05**: Validation AUC ≥ 0.70 required before active learning loop is enabled in the UI; gate enforced at app startup
- [ ] **LEARN-06**: AUC before and after each fine-tune round tracked and available for display

### Streamlit UI

- [ ] **UI-01**: Page 1 — Ingredient search box; returns top 10 pairings sorted by surprise_score; each result shows ingredient name, surprise score + label, pairing score, top 5 shared molecules with flavor descriptors, Plotly radar chart comparing flavor profiles, cuisine overlap
- [ ] **UI-02**: Page 1 — "Why this works" section per pairing: shared flavor compounds listed in plain English with their flavor descriptors
- [ ] **UI-03**: Page 2 — Shows top 5 most uncertain pairs (active learning candidates); user rates each 1–5 stars; submit triggers fine-tuning; "model updated" confirmation shown with AUC delta
- [ ] **UI-04**: Page 3 — PyVis interactive graph centered on selected ingredient; ≤50 nodes to prevent browser crash; nodes sized by pairing_score with center ingredient; edges colored by surprise_score (red=surprising, blue=expected); click node to pivot graph
- [ ] **UI-05**: Page 4 — Select 2–3 ingredients from surprise pairs; calls Anthropic SDK (claude-sonnet-4-6) with shared flavor compounds, texture profiles, and cultural context; generates recipe with molecular pairing rationale; prompt instructs Claude to explain why these ingredients work together scientifically
- [ ] **UI-06**: All pages use @st.cache_resource for embeddings and model (loaded once per process); cache cleared after active learning fine-tune completes
- [ ] **UI-07**: No raw stack traces visible to users; all errors shown as friendly messages

## v2 Requirements

### Polish and Explainability

- **POLISH-01**: Uncertainty badges on pairing results (shows model confidence)
- **POLISH-02**: t-SNE embedding space visualization (proves GNN learned meaningful representations)
- **POLISH-03**: Cross-cultural pairing flag (surfaces East-West pairing surprises from Ahn 2011)
- **POLISH-04**: Collapsible "Model Details" panel with loss function, training stats, architecture summary

### UI Enhancements

- **UI-V2-01**: Score displayed as percentile rank alongside raw float
- **UI-V2-02**: Loading indicators for fine-tune and recipe generation operations

## Out of Scope

| Feature | Reason |
|---------|--------|
| User accounts / persistent ratings | Auth complexity with zero graph ML portfolio signal |
| Real-time AllRecipes scraping in UI | Bot-blocking will fail mid-demo; all data pre-built |
| Nutritional optimization recommendations | Different problem domain; dilutes graph ML story |
| Mobile-responsive UI | Desktop-first sufficient for portfolio demo |
| Multi-user deployment | Single-user local demo is the target |
| 2048-bit Morgan fingerprints | Reduced to 1024 bits for M2/8GB RAM compatibility |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENV-01 to ENV-04 | Phase 1: Foundation | Pending |
| DATA-01 to DATA-06 | Phase 1: Foundation | Pending |
| FEAT-01 to FEAT-09 | Phase 2: Feature Engineering | Pending |
| GRAPH-01 to GRAPH-09 | Phase 3: Graph Construction | Pending |
| MODEL-01 to MODEL-09 | Phase 4: Model Training | Pending |
| SCORE-01 to SCORE-04 | Phase 5: Scoring and Active Learning | Pending |
| LEARN-01 to LEARN-06 | Phase 5: Scoring and Active Learning | Pending |
| UI-01 to UI-07 | Phase 6: Streamlit UI | Pending |

**Coverage:**
- v1 requirements: 54 total (ENV: 4, DATA: 6, FEAT: 9, GRAPH: 9, MODEL: 9, SCORE: 4, LEARN: 6, UI: 7)
- Mapped to phases: 54
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-11 after roadmap creation (corrected requirement count to 54)*
