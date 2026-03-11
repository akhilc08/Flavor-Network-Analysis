# Project Research Summary

**Project:** Flavor Network Analysis — GNN + Molecular Informatics + Streamlit Demo
**Domain:** Graph ML / molecular food science / active learning portfolio demo
**Researched:** 2026-03-11
**Confidence:** HIGH (core ML stack and architecture); MEDIUM (data access reliability, active learning UX norms); LOW (FlavorDB2 endpoint stability)

## Executive Summary

This is a heterogeneous graph ML portfolio project combining molecular food science, a Graph Attention Network (GAT), active learning, and an LLM-powered recipe generator into a single interactive Streamlit demo. The canonical approach — validated against FlavorGraph (Sony AI), KitcheNette, and the Ahn 2011 flavor network paper — is to build a bipartite ingredient-molecule graph enriched with recipe co-occurrence edges, train a 3-layer GAT with dual molecular+recipe supervision and InfoNCE contrastive loss, then expose pre-computed embeddings and a surprise score formula through a 4-page Streamlit UI. No existing public demo combines all three components (GNN + active learning + LLM rationale); this combination is the primary differentiator.

The recommended stack is Python 3.11 + PyTorch 2.6 + PyTorch Geometric 2.7 + RDKit (conda-forge) + Streamlit + Anthropic SDK. The single most important setup constraint is that PyTorch no longer publishes on the conda channel as of 2.6 — all installations must use pip from the PyTorch wheel index after RDKit is installed via conda. The data pipeline feeds from three sources: FlavorDB2 (937 ingredients, HTTP scraping), FooDB (compound-food CSV, direct download), and RecipeNLG via HuggingFace (2.2M recipes, no approval required). AllRecipes scraping is supplemental and should be treated as unreliable.

The dominant risks are front-loaded in the data pipeline: entity name mismatches between FlavorDB2 and FooDB can silently shrink the graph below the 500-ingredient validation threshold; PubChem rate limits cause SMILES gaps that propagate as zero-vector molecular features; and link prediction train/test splits that include test edges in the message-passing graph inflate AUC by 10-20 points. All three risks are detectable with explicit assertions in the pipeline. The active learning loop has two additional risks — cold-start on an undertrained model, and catastrophic forgetting during fine-tuning — both addressed by gating on validation AUC ≥ 0.70 and using experience replay with a 10x lower learning rate.

## Key Findings

### Recommended Stack

The core stack is well-settled: PyTorch 2.6 + PyG 2.7 is the only version pair officially supported for heterogeneous GNN work as of March 2026. RDKit must be installed from conda-forge — the pip wheel is incomplete on some platforms. Streamlit is the right UI choice over Gradio given the multi-page structure and Plotly integration requirements. The Anthropic SDK (0.84.0) targets `claude-sonnet-4-6`, the current default model. RecipeNLG replaces Recipe1M+ as the primary recipe corpus because it requires no academic approval and is available immediately via HuggingFace.

**Core technologies:**
- Python 3.11: Sweet spot for full PyG/RDKit ecosystem support; 3.12+ has sparse GNN support
- PyTorch 2.6.0 + PyG 2.7.0: Only officially supported pair; pip-only install (conda channel dropped)
- RDKit 2025.03.x (conda-forge): Only production cheminformatics library; conda install is mandatory
- NetworkX 3.6.1: Graph construction and validation only — NOT used as handoff format to PyG
- Streamlit 1.44.x: Multi-page demo UI with Plotly and PyVis integration, no frontend code
- Anthropic SDK 0.84.0: `claude-sonnet-4-6` for recipe generation with molecular rationale context
- scikit-learn 1.5.x: Uncertainty sampling (entropy), AUC computation for active learning delta display
- httpx 0.27.x: Async PubChem SMILES lookup with semaphore-limited concurrency (4 req/s max)

See `.planning/research/STACK.md` for full version matrix and installation commands.

### Expected Features

**Must have (table stakes):**
- Ingredient search with autocomplete and top-10 pairing results list — without this the demo is inaccessible
- Shared flavor molecule display (common names, not SMILES) — the scientific hook that distinguishes from generic recommenders
- Radar chart for ingredient flavor profile — standard visual shorthand for multi-dimensional profiles
- Network graph explorer (PyVis) — makes the GNN aspect tangible; without it the graph ML work is invisible
- Surprise score with human-readable label ("Surprising", "Classic") — raw float score is meaningless to reviewers
- Active learning rating loop with AUC delta display — demonstrates the full ML lifecycle; even a small delta proves the loop closes
- AI recipe generation with molecular pairing rationale via Claude — closes the gap from "what pairs" to "how to cook it"
- Clean UI with no raw stack traces — portfolio minimum standard

**Should have (competitive differentiators for a graph ML role):**
- Surprise score formula visible and explained inline — the formula `pairing_score × (1 - recipe_familiarity) × (1 - mol_overlap × 0.5)` is only a differentiator if it is visible
- Uncertainty badges on pairing results — directly illustrates what the active learning loop is doing
- t-SNE embedding space visualization — proves the GNN learned meaningful representations
- Cross-cultural pairing flag — surfaces the Ahn 2011 Western/East-Asian finding in the UI
- Collapsible "Model Details" panel — loss function, training stats, architecture summary for technical reviewers

**Defer (v2+ or never):**
- User accounts / persistent ratings — auth complexity with zero graph ML portfolio signal
- Real-time AllRecipes scraping in the UI — bot-blocking will fail mid-demo; all data must be pre-built
- Nutritional optimization — completely different problem domain; dilutes the graph ML story
- Mobile-responsive UI — Streamlit mobile requires CSS fights; desktop-first is sufficient

See `.planning/research/FEATURES.md` for full prioritization matrix and competitor analysis.

### Architecture Approach

The system is a staged artifact pipeline (DAG with disk checkpoints) running in two modes: an offline pipeline executed once before app launch, and a Streamlit inference runtime that loads pre-computed artifacts. Each pipeline stage reads the previous stage's output files and writes its own artifacts, making stages independently re-runnable. At inference time, the Streamlit app loads pre-computed embeddings (a 128-dim dict per ingredient) and a pre-scored pairs table — no forward pass runs on user queries, keeping the demo fast even on CPU. The full GAT model is only loaded when the active learning fine-tune is explicitly triggered from the UI.

**Major components:**
1. Data ingestion (`data/`) — FlavorDB2 HTTP scraping, FooDB CSV loading, RecipeNLG/AllRecipes recipe sources; writes to `data/raw/`
2. Feature engineering (`data/feature_engineering.py`) — PubChem SMILES → RDKit molecular descriptors + Morgan fingerprints; multimodal ingredient feature assembly; writes to `data/processed/*.parquet`
3. Graph construction (`graph/builder.py`) — NetworkX validation (≥500 ingredients, ≥2000 molecules, 3 edge types) then manual HeteroData construction (NOT `from_networkx()`); writes `graph/hetero_data.pt`
4. Model training (`model/train.py`) — 3-layer GAT (8 heads, 256 hidden, 128 output), dual molecular+recipe supervision + InfoNCE (τ start at 0.1, not 0.07); writes checkpoints and `model/embeddings/ingredient_embeddings.pkl`
5. Active learning (`model/active_learn.py`) — entropy-based uncertainty sampling, 10-epoch fine-tune with experience replay, AUC delta computation; overwrites checkpoint and re-exports embeddings
6. Scoring (`scoring/surprise.py`) — applies surprise formula over embeddings + co-occurrence stats; writes `scoring/scored_pairs.pkl`
7. Streamlit UI (`app/`) — 4-page app using `@st.cache_resource` for embeddings; calls active_learn.py on rating submit; calls Anthropic SDK on Page 4

See `.planning/research/ARCHITECTURE.md` for full data flow diagrams and anti-patterns.

### Critical Pitfalls

1. **Link prediction information leakage** — Test edges included in the message-passing graph inflate AUC by 10-20 points. Prevention: use `RandomLinkSplit` with `edge_types` specified; assert zero overlap between test labels and edge_index before training. Recovery cost is HIGH (must retrain from scratch).

2. **NetworkX-to-HeteroData node index misalignment** — Ingredient/molecule IDs from NetworkX do not map correctly to PyG tensor row indices, causing silent feature corruption. Prevention: maintain explicit `ingredient_id_to_idx` and `molecule_id_to_idx` dicts; never use NetworkX auto-assigned integers as PyG indices. Recovery cost is HIGH.

3. **FlavorDB2/FooDB entity name mismatch** — Naive inner join discards 40-60% of valid matches, silently shrinking the graph below the 500-ingredient threshold. Prevention: fuzzy matching with RapidFuzz (`token_sort_ratio > 85`); assert ≥300 matched ingredients with populated FooDB fields before proceeding.

4. **PubChem rate limiting with silent SMILES gaps** — HTTP 503 blocks mid-batch leave molecule nodes with zero-vector features that appear valid. Prevention: token bucket at 400 req/min ceiling (not just 5/sec); cache all responses to `pubchem_cache.json` immediately; assert 100% cache coverage before RDKit processing.

5. **Active learning catastrophic forgetting** — 10-epoch fine-tune on 5-20 feedback samples at full learning rate overwrites base model knowledge. Prevention: learning rate 10x lower during fine-tune; experience replay with 5x feedback sample size from original training set; checkpoint before each fine-tune round.

6. **GAT self-loops on bipartite edges** — `add_self_loops=True` (GATConv default) fails or silently corrupts attention on ingredient↔molecule bipartite edges. Prevention: always set `add_self_loops=False` on GATConv instances handling bipartite edge types.

7. **InfoNCE temperature instability** — τ = 0.07 (image contrastive learning default) causes gradient explosion or mode collapse in food flavor domain where many "negative" pairs share volatile compounds. Prevention: start at τ = 0.1-0.2; add gradient clipping (`max_norm=1.0`); log InfoNCE loss component separately.

See `.planning/research/PITFALLS.md` for full checklist, recovery strategies, and warning signs.

## Implications for Roadmap

Architecture research identifies 6 hard sequential phases with explicit dependency gates. The pipeline cannot be parallelized across phases (each phase consumes the previous stage's artifacts), but model code (gat.py, losses.py) and Streamlit page shells can be written in parallel with the data stages.

### Phase 1: Environment Setup and Data Ingestion
**Rationale:** All downstream work is blocked until data is scraped and stored. Environment setup must come first because RDKit + PyTorch version conflicts are a project-killer if discovered mid-pipeline. Conda+pip hybrid install is required and non-obvious.
**Delivers:** Working conda environment with all dependencies pinned; `data/raw/` populated from FlavorDB2, FooDB, and RecipeNLG; AllRecipes partial scrape with documented failure rate.
**Addresses:** Ingredient search (data foundation), shared molecule display (data foundation)
**Avoids:** PyG/PyTorch version incompatibility (Pitfall 7); AllRecipes scraping failure (Pitfall 12); API key exposure (security)

### Phase 2: Feature Engineering
**Rationale:** Blocked by data ingestion. PubChem SMILES lookup and RDKit descriptor computation are the most fragile steps in the pipeline — both require robust error handling before graph construction can begin.
**Delivers:** `data/processed/ingredients.parquet`, `molecules.parquet`, `cooccurrence.parquet` with validated molecular features and a logged RDKit failure report.
**Uses:** RDKit, httpx, pandas, NumPy
**Avoids:** PubChem rate limiting silent gaps (Pitfall 4); RDKit sanitization failures (Pitfall 5); FlavorDB/FooDB name mismatch (Pitfall 3)

### Phase 3: Graph Construction
**Rationale:** Hard dependency on processed parquets. The validation gate (≥500 ingredients, ≥2000 molecules, ≥1000 edges per edge type) is a go/no-go decision point for training. Manual HeteroData construction must happen here, not via `from_networkx()`.
**Delivers:** `graph/hetero_data.pt` with validated heterogeneous graph; explicit `ingredient_id_to_idx` and `molecule_id_to_idx` mappings; link prediction split with zero test-edge leakage assertion.
**Implements:** Graph construction component; NetworkX validation + manual HeteroData pattern (Pattern 3)
**Avoids:** NetworkX-to-HeteroData index misalignment (Pitfall 2); link prediction information leakage (Pitfall 1)

### Phase 4: Model Training
**Rationale:** Blocked by graph construction. Model definition files (gat.py, losses.py) can be written during Phase 3 in parallel. Training cannot run until hetero_data.pt is validated.
**Delivers:** Trained GAT model checkpoint; `ingredient_embeddings.pkl` (128-dim per ingredient); baseline validation AUC ≥ 0.70 (gate for active learning)
**Uses:** PyTorch 2.6, PyG 2.7, GATConv with `add_self_loops=False`, multi-task loss with τ=0.1 InfoNCE start
**Avoids:** GAT self-loops on bipartite edges (Pitfall 6); InfoNCE temperature instability (Pitfall 10); full-batch OOM (use NeighborLoader if memory is constrained)

### Phase 5: Scoring and Active Learning
**Rationale:** Blocked by trained embeddings. Surprise score formula is a pure function over embeddings and co-occurrence stats — can be tuned without retraining. Active learning loop requires validated AUC ≥ 0.70 before uncertainty sampling is meaningful.
**Delivers:** `scoring/scored_pairs.pkl` with calibrated surprise scores; active learning fine-tune loop with experience replay and AUC delta tracking
**Addresses:** Surprise score metric + label (P1); active learning rating loop + AUC delta (P1)
**Avoids:** Active learning cold start (Pitfall 8); catastrophic forgetting (Pitfall 9)

### Phase 6: Streamlit UI (4 Pages)
**Rationale:** Blocked by scored_pairs.pkl and embeddings. Pages 1, 3, and 4 can be built in any order after Phase 5. Page 2 (active learning) depends additionally on the active_learn.py module from Phase 5. Page shells with stub data can be built in parallel with Phases 3-5.
**Delivers:** Complete 4-page Streamlit demo: ingredient pairing search with radar chart + shared molecules (Page 1); active learning rating with AUC delta (Page 2); PyVis graph explorer with 50-node cap (Page 3); Claude API recipe generation with molecular rationale (Page 4)
**Uses:** Streamlit, Plotly, PyVis, Anthropic SDK; `@st.cache_resource` for all loaded artifacts
**Avoids:** PyVis graph performance collapse beyond 500 nodes (Pitfall 11); raw stack traces in UI (technical debt); loading model at every Streamlit query (Anti-Pattern 2)

### Phase 7: Polish and v1.x Features
**Rationale:** After core demo is working and validated end-to-end. Lower risk; high explainability value.
**Delivers:** Uncertainty badges on pairing results; t-SNE embedding visualization; cross-cultural pairing flag; model architecture details panel; UX polish (display names, score labels as percentile rank, loading indicators)

### Phase Ordering Rationale

- Phases 1-5 are hard-sequential: each phase has an explicit artifact gate that blocks the next. Attempting to build the UI before embeddings are computed produces a demo that cannot demonstrate its core claim.
- Model code (gat.py, losses.py) and Streamlit page shells are the only safe parallel tracks — they have no runtime dependencies on upstream data artifacts.
- The surprise score formula is isolated in `scoring/` intentionally: it can be iterated independently of the GNN, making Phase 5 internally parallelizable between formula tuning and active learning loop development.
- Phase 7 is explicitly last: all v1.x features (t-SNE, uncertainty badges, cross-cultural flags) require validated working embeddings from Phase 4 to be meaningful.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Feature Engineering):** PubChem + RDKit interaction is well-documented individually but the combined async fetch + sanitization failure handling + cache management pattern needs a concrete implementation plan before coding begins.
- **Phase 3 (Graph Construction):** The `RandomLinkSplit` configuration for HeteroData with multiple edge types has limited worked examples; the leakage-free split pattern needs to be verified against the specific edge type schema before implementation.
- **Phase 5 (Active Learning):** Experience replay implementation for fine-tuning a GNN with sparse feedback is not a well-documented pattern; the specific buffer size and learning rate schedule need validation during implementation.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Environment Setup):** Conda+pip hybrid install for RDKit+PyTorch is fully documented and tested. Follow STACK.md install commands exactly.
- **Phase 4 (Model Training):** 3-layer GAT with dual supervision is a standard pattern in PyG. The architecture and loss functions are well-documented.
- **Phase 6 (Streamlit UI):** `@st.cache_resource`, Plotly radar charts, and PyVis iframe integration all have established patterns documented in ARCHITECTURE.md.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core versions (PyTorch 2.6, PyG 2.7, RDKit 2025.03) verified against official docs and PyPI; conda-pip hybrid install confirmed. PyTorch 2.7 availability is the only near-term risk. |
| Features | MEDIUM | Table stakes and P1 differentiators are well-supported by published research (FlavorGraph, KitcheNette, Ahn 2011). Active learning UX norms are community-consensus, not formally documented. |
| Architecture | HIGH | Staged artifact pipeline, manual HeteroData construction, and Streamlit caching patterns are all verified against official PyG docs and Streamlit docs. Active learning integration is MEDIUM — sparse worked examples for GNN-specific fine-tune with experience replay. |
| Pitfalls | HIGH | 10 of 12 pitfalls verified via official documentation, PyG GitHub issues, or peer-reviewed papers. AllRecipes bot-blocking behavior is community-known. |

**Overall confidence:** HIGH for the core pipeline and model; MEDIUM for active learning fine-tune specifics and FlavorDB2 endpoint stability.

### Gaps to Address

- **FlavorDB2 endpoint stability:** The `entities_json?entity=N` pattern is community-known but undocumented. Cache all responses on first run; have a fallback plan if the endpoint changes (FooDB-only graph with reduced ingredient coverage is acceptable).
- **Active learning fine-tune hyperparameters:** The specific learning rate (1e-5), replay buffer size (5x feedback), and 10-epoch fine-tune duration are reasonable estimates but need empirical validation during Phase 5. Instrument the training loop to log per-epoch global validation AUC from the start.
- **InfoNCE temperature τ calibration:** The research recommends starting at 0.1-0.2 rather than the project spec's 0.07, based on the food domain's high molecular overlap between "negative" pairs. This should be tuned in Phase 4 with the InfoNCE loss logged separately from other loss components.
- **Graph validation thresholds:** The 500-ingredient and 2000-molecule minimums come from the project spec, not from published baselines. If fuzzy matching yields fewer than 400 ingredients, assess whether the demo still works before declaring the data pipeline failed.

## Sources

### Primary (HIGH confidence)
- [PyTorch Geometric 2.7.0 Installation Docs](https://pytorch-geometric.readthedocs.io/en/2.7.0/install/installation.html) — version matrix, wheel install commands
- [PyTorch 2.6 Release Blog](https://pytorch.org/blog/pytorch2-6/) — conda channel dropped, pip-only confirmed
- [PyG Heterogeneous Graph Learning docs](https://pytorch-geometric.readthedocs.io/en/latest/notes/heterogeneous.html) — GATConv + to_hetero(), HeteroConv, bipartite self-loop caveat
- [Streamlit caching docs](https://docs.streamlit.io/develop/concepts/architecture/caching) — st.cache_resource patterns
- [RDKit Installation Docs](https://www.rdkit.org/docs/Install.html) — conda-forge as recommended path
- [Pitfalls in Link Prediction with GNNs (ACM WSDM 2024)](https://dl.acm.org/doi/10.1145/3616855.3635786) — information leakage in link prediction
- [FlavorGraph paper (Scientific Reports, 2021)](https://www.nature.com/articles/s41598-020-79422-8) — graph architecture, feature design reference
- [mbien/recipe_nlg on HuggingFace](https://huggingface.co/datasets/mbien/recipe_nlg) — 2.2M recipes, confirmed accessible
- [anthropic PyPI](https://pypi.org/project/anthropic/) — SDK version 0.84.0 confirmed

### Secondary (MEDIUM confidence)
- [FlavorGraph GitHub](https://github.com/lamypark/FlavorGraph) — implementation reference for heterogeneous graph architecture
- [KitcheNette (IJCAI 2019)](https://www.ijcai.org/proceedings/2019/0822.pdf) — Siamese network baseline, Bayesian Surprise metric
- [Active learning cold start problem (NeurIPS 2024)](https://arxiv.org/abs/2403.03728) — cold-start mitigation strategies
- [Temperature-Free InfoNCE (arXiv 2025)](https://arxiv.org/abs/2501.17683) — temperature sensitivity in contrastive learning
- [Streamlit + PyVis large graph error (community)](https://discuss.streamlit.io/t/streamlit-pyvis-error-when-displaying-large-network/28501) — 500-node cap requirement
- [PyG HeteroData from_networkx discussion](https://github.com/pyg-team/pytorch_geometric/discussions/4457) — manual index mapping requirement confirmed

### Tertiary (LOW confidence)
- [FlavorDB2 entities_json endpoint](https://cosylab.iiitd.edu.in/flavordb2/) — undocumented REST API; community-known scraping pattern; endpoint stability not guaranteed

---
*Research completed: 2026-03-11*
*Ready for roadmap: yes*
