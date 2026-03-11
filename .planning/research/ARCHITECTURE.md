# Architecture Research

**Domain:** Graph ML system — molecular food pairing with heterogeneous GNN and active learning
**Researched:** 2026-03-11
**Confidence:** HIGH (core PyG/PyTorch patterns), MEDIUM (active learning integration), HIGH (Streamlit caching patterns)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION LAYER                          │
├──────────────┬──────────────────┬──────────────┬────────────────────┤
│  FlavorDB2   │  FooDB CSVs      │  Recipe1M+   │  AllRecipes        │
│  (HTTP API)  │  (local files)   │  (open data) │  (scraper)         │
│  entities_   │  foods.csv       │              │  10 categories     │
│  json 1-1000 │  compounds.csv   │              │  500 recipes each  │
└──────┬───────┴────────┬─────────┴──────┬───────┴──────────┬─────────┘
       │                │                │                   │
       ▼                ▼                ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FEATURE ENGINEERING LAYER                         │
├──────────────────────────────┬──────────────────────────────────────┤
│   Molecular Features         │   Ingredient Features                 │
│   (PubChem SMILES → RDKit)   │   (multimodal embeddings)            │
│   MW, logP, HBD/HBA          │   - texture embedding                │
│   rotatable bonds, TPSA      │   - temperature affinity             │
│   Morgan fingerprints (2048) │   - cultural context vector          │
│                              │   - flavor profile multi-hot         │
└──────────────┬───────────────┴──────────────────────┬───────────────┘
               │                                       │
               ▼                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GRAPH CONSTRUCTION LAYER                          │
│                                                                      │
│   NetworkX (build + validate)  →  PyG HeteroData (serialize)        │
│                                                                      │
│   Node types:  ingredient (≥500)  |  molecule (≥2000)               │
│   Edge types:  ingredient-contains-molecule                          │
│                ingredient-cooccurs-ingredient                        │
│                molecule-structsim-molecule                           │
│                                                                      │
│   Validation gate: ≥500 ingredient nodes, ≥2000 molecule nodes      │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       TRAINING LAYER                                 │
│                                                                      │
│   GAT model: 3 layers, 8 heads, 256 hidden, 128 output              │
│   Loss: molecular_loss + recipe_loss + InfoNCE (temp=0.07)          │
│   Output: ingredient node embeddings (128-dim) + model checkpoint   │
│                                                                      │
│   Artifacts written:                                                 │
│     model/checkpoints/  — .pt checkpoint files                      │
│     model/embeddings/   — ingredient_embeddings.pkl                 │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
                   ┌────────────────┴────────────────┐
                   │                                 │
                   ▼                                 ▼
┌──────────────────────────────┐  ┌──────────────────────────────────┐
│     SCORING LAYER            │  │      ACTIVE LEARNING LOOP         │
│                              │  │                                   │
│  Surprise score:             │  │  1. Uncertainty sampling:         │
│  pairing_score ×             │  │     entropy over top-20 pairs     │
│  (1 - recipe_familiarity) ×  │  │  2. Present to user (UI Page 2)  │
│  (1 - mol_overlap × 0.5)     │  │  3. Write to feedback.csv         │
│                              │  │  4. 10-epoch fine-tune            │
│  Reads: embeddings           │  │  5. Report AUC delta to user      │
│  Writes: scored_pairs.pkl    │  │                                   │
└──────────────┬───────────────┘  └──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      STREAMLIT UI LAYER                              │
├──────────────────┬───────────────────┬──────────────────────────────┤
│  Page 1          │  Page 2           │  Page 3          Page 4      │
│  Ingredient      │  Active Learning  │  Graph Explorer  Recipe Gen  │
│  Pairing Search  │  Rating UI        │  (PyVis)         (Claude API)│
└──────────────────┴───────────────────┴──────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| `data/` scrapers/loaders | Raw data acquisition from FlavorDB2, FooDB, recipe sources | Writes raw CSVs / JSON to `data/raw/` |
| `data/` feature builder | SMILES → PubChem lookup → RDKit feature vectors; multimodal ingredient feature assembly | Reads raw data, writes `data/processed/` feature tables |
| `graph/builder.py` | Constructs NetworkX multigraph, validates node counts, serializes to PyG HeteroData | Reads processed features, writes `graph/hetero_data.pt` |
| `model/train.py` | Loads HeteroData, runs GAT training loop with dual + InfoNCE loss, checkpoints | Reads `hetero_data.pt`, writes `model/checkpoints/` and `model/embeddings/ingredient_embeddings.pkl` |
| `model/active_learn.py` | Computes uncertainty over candidate pairs, runs feedback fine-tune loop | Reads model checkpoint + `feedback.csv`, overwrites checkpoint, recomputes embeddings |
| `scoring/surprise.py` | Applies surprise formula to embedding similarity scores, materializes ranked pair table | Reads `ingredient_embeddings.pkl` + recipe co-occurrence stats, writes `scoring/scored_pairs.pkl` |
| `app/app.py` | Multi-page Streamlit entrypoint; caches model, embeddings, scored pairs via `@st.cache_resource` / `@st.cache_data` | Reads artifacts, calls `model/active_learn.py` on user rating submit, calls Anthropic SDK for Page 4 |

## Recommended Project Structure

```
Flavor-Network-Analysis/
├── data/
│   ├── raw/                    # unmodified source data
│   │   ├── flavordb/           # JSON responses from entities_json endpoint
│   │   ├── foodb/              # foods.csv, compounds.csv
│   │   └── recipes/            # Recipe1M+ / AllRecipes scraped files
│   ├── processed/              # feature-engineered tables ready for graph builder
│   │   ├── ingredients.parquet # ingredient rows with multimodal feature columns
│   │   ├── molecules.parquet   # molecule rows with RDKit descriptor columns
│   │   └── cooccurrence.parquet# ingredient pair co-occurrence counts
│   ├── ingest_flavordb.py      # FlavorDB2 scraper
│   ├── ingest_foodb.py         # FooDB CSV processor
│   ├── ingest_recipes.py       # Recipe1M+ + AllRecipes scraper
│   └── feature_engineering.py # PubChem → RDKit pipeline; multimodal assembly
├── graph/
│   ├── builder.py              # NetworkX → HeteroData; validation gate
│   ├── hetero_data.pt          # serialized PyG HeteroData (gitignored, large)
│   └── validate.py             # assertion helpers (node/edge counts, dtype checks)
├── model/
│   ├── gat.py                  # HeteroGAT model definition (to_hetero or HeteroConv)
│   ├── train.py                # training loop; multi-loss; checkpoint logic
│   ├── losses.py               # molecular_loss, recipe_loss, InfoNCE
│   ├── active_learn.py         # uncertainty sampling; feedback fine-tune
│   ├── checkpoints/            # model_epoch_{N}.pt  (gitignored)
│   └── embeddings/
│       └── ingredient_embeddings.pkl  # {ingredient_id: 128-dim tensor}
├── scoring/
│   ├── surprise.py             # surprise score formula; ranked pair table
│   └── scored_pairs.pkl        # pre-computed pairs (gitignored, regenerated)
├── app/
│   ├── app.py                  # Streamlit entrypoint + page routing
│   ├── pages/
│   │   ├── 01_pairing_search.py
│   │   ├── 02_active_learning.py
│   │   ├── 03_graph_explorer.py
│   │   └── 04_recipe_generator.py
│   └── utils/
│       ├── loaders.py          # @st.cache_resource model/embedding loaders
│       └── viz.py              # Plotly radar chart, PyVis graph builder
├── requirements.txt
└── README.md
```

### Structure Rationale

- **`data/raw/` vs `data/processed/`:** Separating raw from processed follows the FTI pipeline principle — raw data is immutable, processed features are regeneratable. This lets you re-run feature engineering without re-scraping.
- **`graph/`:** Graph construction is its own stage because it has a hard validation gate (≥500/≥2000 nodes) before training can begin. Isolating it makes that gate explicit and testable.
- **`model/embeddings/`:** Embeddings are separated from model weights because the Streamlit app reads only embeddings at inference time — it does not reload the full model for search/pairing queries. The model is only needed during active learning fine-tune.
- **`scoring/`:** The surprise formula is a pure function over embeddings and co-occurrence stats. Keeping it separate from the model makes it easy to iterate on the formula without retraining.
- **`app/pages/`:** Streamlit's multi-page app convention — each page is a separate file. Shared resources (model, embeddings) are loaded once in `utils/loaders.py` with `@st.cache_resource`.

## Architectural Patterns

### Pattern 1: Staged Artifact Pipeline (DAG with Checkpoints)

**What:** Each pipeline stage reads from the previous stage's output files rather than in-memory objects. Stages are independently re-runnable.

**When to use:** Any ML pipeline where stages have significant compute cost (scraping, RDKit batch processing, graph construction, training). This project needs it because each stage takes minutes to hours.

**Trade-offs:** More disk I/O, but makes debugging and re-runs far cheaper than a monolithic script. Critical for a portfolio project where you will iterate on individual stages frequently.

**Example:**
```python
# graph/builder.py reads a processed parquet, writes hetero_data.pt
# This makes builder.py independently runnable without re-scraping
ingredients = pd.read_parquet("data/processed/ingredients.parquet")
molecules    = pd.read_parquet("data/processed/molecules.parquet")
# ... construct HeteroData ...
torch.save(hetero_data, "graph/hetero_data.pt")
```

### Pattern 2: Separate Inference Path from Training Path

**What:** At Streamlit runtime, load pre-computed embeddings (a pickle dict) rather than the full model. The full GAT model is only loaded when the active learning fine-tune is triggered.

**When to use:** Any app where inference is a nearest-neighbor lookup over static embeddings — no forward pass needed at query time.

**Trade-offs:** Embeddings go stale after fine-tuning until regenerated. You must re-export embeddings after each active learning round. Accept this: document it as a design choice, run re-export at end of fine-tune.

**Example:**
```python
# app/utils/loaders.py
@st.cache_resource
def load_embeddings():
    with open("model/embeddings/ingredient_embeddings.pkl", "rb") as f:
        return pickle.load(f)  # {ingredient_id: np.ndarray (128,)}

# Pairing search is then a cosine similarity over this dict — no GPU needed
```

### Pattern 3: Heterogeneous Graph via Manual HeteroData Construction

**What:** Build the PyG HeteroData object manually from processed DataFrames rather than relying on `from_networkx()`. Use NetworkX only for validation and visualization, not as the serialization format passed to PyG.

**When to use:** Always for this project. PyG's `from_networkx()` does not support heterogeneous graphs natively — nodes of different types have different attribute shapes, which causes errors. Manual construction is more verbose but reliable.

**Trade-offs:** More boilerplate in `graph/builder.py`, but avoids the documented incompatibility between NetworkX heterogeneous graphs and PyG HeteroData conversion utilities.

**Example:**
```python
data = HeteroData()
data['ingredient'].x = torch.tensor(ingredient_features)   # (N_ing, feat_dim)
data['molecule'].x   = torch.tensor(molecule_features)     # (N_mol, feat_dim)
data['ingredient', 'contains', 'molecule'].edge_index = contains_edges  # (2, E)
data['ingredient', 'cooccurs', 'ingredient'].edge_index = cooccur_edges
data['molecule', 'structsim', 'molecule'].edge_index = sim_edges
```

### Pattern 4: Dual Supervision + InfoNCE Multi-Task Loss

**What:** Combine three losses: (1) molecular supervision — pairs with high shared compound count should have similar embeddings; (2) recipe supervision — co-occurring pairs should be close; (3) InfoNCE contrastive loss — anchor ingredient embeddings vs positive/negative samples.

**When to use:** When multiple signals of "similarity" exist and you want the model to learn a unified representation that respects all of them.

**Trade-offs:** Loss balancing is a free hyperparameter that requires tuning. Start with equal weights; use validation set surprise-score distribution as a proxy metric.

**Example:**
```python
total_loss = alpha * mol_loss + beta * recipe_loss + gamma * infonce_loss
# alpha=1.0, beta=1.0, gamma=0.5 as starting point; tune if training diverges
```

### Pattern 5: Active Learning as a Fine-Tune Overlay

**What:** After base training, the active learning loop fine-tunes only the final GAT layer + output projection for 10 epochs on feedback data. It does not re-train from scratch.

**When to use:** When user feedback is sparse (5 ratings per session) and base model is already well-trained.

**Trade-offs:** Risk of catastrophic forgetting if feedback distribution is very different from training data. Mitigation: include a small random sample of original training pairs in each fine-tune batch (experience replay).

**Uncertainty sampling implementation:** Use entropy of the softmax over pairwise cosine similarity scores — high entropy = model is unsure which pairs are good. Top-20 uncertain pairs are presented to the user.

## Data Flow

### Offline Pipeline Flow (Run Once Before App Launch)

```
FlavorDB2 API  →  data/raw/flavordb/*.json
FooDB CSVs     →  data/raw/foodb/*.csv
Recipe sources →  data/raw/recipes/*.json
                         │
                         ▼
           data/feature_engineering.py
           (PubChem SMILES lookup, RDKit descriptors,
            multimodal feature assembly)
                         │
                         ▼
           data/processed/*.parquet
                         │
                         ▼
           graph/builder.py
           (NetworkX validation → HeteroData construction)
                         │
                         ▼
           graph/hetero_data.pt  ← validation gate here
                         │
                         ▼
           model/train.py
           (GAT 3-layer, dual + InfoNCE loss, checkpoints)
                         │
                  ┌──────┴──────┐
                  │             │
                  ▼             ▼
    model/checkpoints/   model/embeddings/
    model_epoch_N.pt     ingredient_embeddings.pkl
                  │
                  ▼
    scoring/surprise.py
    (surprise formula over embeddings + co-occurrence stats)
                  │
                  ▼
    scoring/scored_pairs.pkl  ← app reads this at startup
```

### Active Learning Flow (Triggered by User Rating Submission)

```
User rates 5 pairs (1–5 stars) on UI Page 2
    │
    ▼
feedback.csv  ←  append new rows
    │
    ▼
model/active_learn.py
  - Load latest checkpoint
  - Uncertainty sampling: entropy over candidate embedding cosine scores
  - Fine-tune 10 epochs on feedback + experience replay buffer
  - Save new checkpoint
  - Re-export ingredient_embeddings.pkl
  - Re-run scoring/surprise.py → overwrite scored_pairs.pkl
    │
    ▼
UI shows AUC delta (before vs after fine-tune on held-out pairs)
st.cache_resource.clear()  ← forces embedding reload on next query
```

### Streamlit Inference Flow (Per User Query on Page 1)

```
User types ingredient name
    │
    ▼
app/utils/loaders.py  (cached: load embeddings dict, scored_pairs)
    │
    ▼
Cosine similarity: query_embedding vs all ingredient embeddings
    │
    ▼
Join with scored_pairs to get surprise scores
    │
    ▼
Top-10 results with:
  - Surprise score
  - Shared molecule list (from graph/hetero_data.pt metadata)
  - Radar chart of flavor profile dimensions (Plotly)
  - Cuisine context vector
```

### Claude API Flow (Page 4)

```
User selects 2–3 surprise-pair ingredients
    │
    ▼
Retrieve shared molecules, surprise scores, flavor profiles
    │
    ▼
Construct prompt: ingredient names + molecular pairing rationale context
    │
    ▼
Anthropic SDK  →  claude-sonnet (latest)
    │
    ▼
Stream recipe text to Streamlit with st.write_stream()
```

## Build Order (Phase Dependencies)

The system has hard sequential dependencies between stages. Each stage produces artifacts that the next stage requires. Parallel work is possible only within a stage.

```
Phase 1: Data Ingestion
  FlavorDB2 scraper  ──┐
  FooDB loader       ──┤──→  data/raw/  (prerequisite for Phase 2)
  Recipe scrapers    ──┘

Phase 2: Feature Engineering
  Depends on: data/raw/ (all sources populated)
  PubChem + RDKit pipeline  ──→  data/processed/*.parquet
  Multimodal feature assembly
  Produces: features ready for graph construction

Phase 3: Graph Construction
  Depends on: data/processed/*.parquet
  NetworkX assembly + validation gate
  HeteroData serialization  ──→  graph/hetero_data.pt
  BLOCK: training cannot start until ≥500 ingredients + ≥2000 molecules validated

Phase 4: Model Training
  Depends on: graph/hetero_data.pt
  GAT model definition  (can write in parallel with Phase 3)
  Loss functions        (can write in parallel with Phase 3)
  Training loop + checkpointing  ──→  model/checkpoints/ + embeddings/

Phase 5: Scoring
  Depends on: model/embeddings/ingredient_embeddings.pkl
  Surprise formula implementation
  Pair materialization  ──→  scoring/scored_pairs.pkl

Phase 6: Streamlit UI
  Depends on: scored_pairs.pkl + ingredient_embeddings.pkl
  Can build Pages 1, 3, 4 in any order after Phase 5
  Page 2 (active learning) depends additionally on:
    - model/active_learn.py (Phase 4 work)
    - feedback.csv schema defined
```

**What can start early (before full pipeline runs):**
- GAT model definition (`model/gat.py`) — can write against mock tensors
- Loss functions (`model/losses.py`) — pure math, no data dependency
- Streamlit page shells with stub data — unblocks UI polish work
- Surprise formula — can unit-test with synthetic embeddings

## Anti-Patterns

### Anti-Pattern 1: Using `from_networkx()` for the Heterogeneous Graph

**What people do:** Build a single NetworkX graph with node type attributes, then call `pyg.utils.from_networkx()` hoping it produces a HeteroData object.

**Why it's wrong:** PyG's `from_networkx()` targets homogeneous Data objects. For heterogeneous graphs, it throws "Not all nodes contain the same attributes" errors because ingredient and molecule nodes have different feature dimensions. Workarounds that normalize feature shapes across types destroy the type-specificity that makes heterogeneous modeling valuable.

**Do this instead:** Build HeteroData manually from typed DataFrames (see Pattern 3). Use NetworkX only as an intermediate validation tool or for PyVis visualization — never as the handoff format to PyG.

### Anti-Pattern 2: Loading the Full Model at Every Streamlit Query

**What people do:** Call `torch.load(model_checkpoint)` inside a query handler, or skip caching altogether.

**Why it's wrong:** Model load + forward pass is expensive. Streamlit re-executes the entire script on every user interaction. Without `@st.cache_resource`, the model reloads on every keypress in the search box.

**Do this instead:** Use `@st.cache_resource` to load model and embeddings once per process lifetime. For the active learning fine-tune (which mutates the model), explicitly call `st.cache_resource.clear()` afterward to force a reload of updated artifacts.

### Anti-Pattern 3: Monolithic Training Script That Also Preprocesses Data

**What people do:** Write one large script: scrape → feature engineer → build graph → train. Common in notebooks/prototypes.

**Why it's wrong:** Any failure (rate limit, OOM during training) forces a re-run from the beginning. On this dataset size, scraping + RDKit batch processing alone can take 30+ minutes.

**Do this instead:** Each pipeline stage writes artifacts to disk and has an independent entry point. This is the staged artifact pipeline pattern (Pattern 1). Bonus: it makes each component unit-testable with fixture files.

### Anti-Pattern 4: Training Active Learning Without Experience Replay

**What people do:** Fine-tune only on the 5 new feedback ratings, discarding original training signal.

**Why it's wrong:** With only 5 examples, the model will catastrophically forget previously learned structure in as few as 10 epochs. The resulting embeddings will over-index on the feedback labels and produce worse pairings overall.

**Do this instead:** During each fine-tune pass, sample a buffer of ~50-100 original training pairs alongside the 5 feedback pairs. This keeps the loss landscape anchored to the base model's knowledge while incorporating new signal.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| FlavorDB2 (`/entities_json?page=N`) | HTTP GET in a loop, IDs 1–1000, rate-limited with `time.sleep(0.5)` | Public endpoint, no auth; returns ingredient + compound list |
| PubChem REST API | HTTP GET per SMILES lookup (`/compound/name/{name}/property/...`) | Free, no key; cache responses to avoid re-fetching; 400 errors mean compound not found |
| AllRecipes | `requests` + `BeautifulSoup`, 10 categories × 500 recipes, 1–2s delay | Expect bot-blocking; use rotating user-agents; treat partial data as acceptable |
| Anthropic SDK | `anthropic.Anthropic().messages.create(model="claude-sonnet-4-5", ...)` | Requires `ANTHROPIC_API_KEY` env var; use streaming for better UX |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `data/` → `graph/` | Parquet files in `data/processed/` | Parquet is the canonical handoff format; avoids CSV encoding issues with molecule names |
| `graph/` → `model/` | `graph/hetero_data.pt` via `torch.save/load` | Include metadata dict alongside HeteroData: ingredient ID-to-index mapping needed at inference time |
| `model/` → `scoring/` | `ingredient_embeddings.pkl` (dict: ingredient_id → np.ndarray) | Export after training and after each fine-tune round |
| `model/` → `app/` | Same embedding pickle + model checkpoint for active learning only | App uses embeddings for search; loads full model only when fine-tune triggers |
| `scoring/` → `app/` | `scored_pairs.pkl` (list of dicts with pairing + surprise score + metadata) | Pre-computed at pipeline end; app loads at startup via `@st.cache_data` |
| `app/` → `model/active_learn.py` | Direct Python call (subprocess or in-process) | In-process is simpler; use a Streamlit spinner to block UI during fine-tune |
| `app/` → Anthropic API | Direct SDK call in page handler | Pass ingredient names + molecular context; keep prompt under 2000 tokens |

## Scaling Considerations

This is a single-user local demo. Scaling is not a design goal. That said:

| Concern | Current approach | What would change for multi-user |
|---------|-----------------|----------------------------------|
| Embedding lookup | In-memory dict loaded at startup | Switch to FAISS index for ANN search |
| Active learning fine-tune | Synchronous, blocks UI | Move to background task queue (Celery/RQ) |
| Graph storage | Single `.pt` file | Graph database (Neo4j) for dynamic updates |
| Model serving | In-process torch.load | TorchServe or separate FastAPI inference server |

## Sources

- [PyTorch Geometric Heterogeneous Graph Learning docs](https://pytorch-geometric.readthedocs.io/en/2.5.1/notes/heterogeneous.html)
- [PyG HeteroData convert discussion — manual construction required for heterogeneous graphs](https://github.com/pyg-team/pytorch_geometric/discussions/4457)
- [Streamlit caching docs — st.cache_resource for ML models](https://docs.streamlit.io/develop/concepts/architecture/caching)
- [Hopsworks FTI pipeline architecture — Feature/Training/Inference separation pattern](https://www.hopsworks.ai/post/mlops-to-ml-systems-with-fti-pipelines)
- [Flavor network and the principles of food pairing — Ahn et al. 2011 (bipartite graph methodology)](https://www.nature.com/articles/srep00196)
- [Active learning with GNNs: uncertainty sampling strategies (STAL paper)](https://link.springer.com/article/10.1007/s10618-023-00959-z)
- [InfoNCE for graph contrastive learning — positive/negative pair sampling](https://arxiv.org/abs/2505.06282)
- [GAT: Graph Attention Networks original paper](https://arxiv.org/abs/1710.10903)
- [RDKit descriptor pipeline — SMILES to feature vector](https://www.blopig.com/blog/2022/06/how-to-turn-a-molecule-into-a-vector-of-physicochemical-descriptors-using-rdkit/)

---
*Architecture research for: Flavor Pairing Network — GNN + active learning + Streamlit*
*Researched: 2026-03-11*
