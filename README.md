# Flavor Network Analysis

**[flavornet.vercel.app](https://flavornet.vercel.app)**

A graph neural network system that discovers non-obvious but scientifically grounded food ingredient pairings. The core metric is a _surprise score_: how unexpectedly compatible two ingredients are given their molecular similarity and how rarely they appear together in real recipes.

## What It Does

- **Search pairings** — enter an ingredient and get its top molecularly compatible but culturally underused partners, with shared flavor molecules, radar charts, and cuisine context
- **Rate pairs** — vote on uncertain pairings to improve the model via an active learning loop
- **Explore the graph** — interactive flavor network centered on any ingredient
- **Generate recipes** — pick 2–3 surprise-pair ingredients and get a Claude-generated recipe with molecular pairing rationale

## How It Works

The system is built in two parts: a Python ML backend and a Next.js frontend.

### ML Pipeline (Python)

1. **Data ingestion** — FlavorDB2 ingredient/molecule data, FooDB compound profiles, and recipe co-occurrence from RecipeNLG and AllRecipes
2. **Feature engineering** — RDKit computes molecular features from SMILES (MW, logP, HBD/HBA, Morgan fingerprints); multimodal ingredient features include texture, temperature affinity, cultural context, and flavor profile vectors
3. **Graph construction** — heterogeneous graph via NetworkX → PyTorch Geometric `HeteroData` with ingredient nodes, molecule nodes, and co-occurrence/contains/structural-similarity edges
4. **Model training** — 3-layer Graph Attention Network (8 heads, 256 hidden, 128 output) trained with dual supervision: molecular similarity + recipe co-occurrence + InfoNCE contrastive loss
5. **Surprise scoring** — `pairing_score × (1 - recipe_familiarity) × (1 - molecular_overlap × 0.5)`
6. **Active learning** — uncertainty sampling on the top uncertain pairs; user ratings fine-tune the model for 10 epochs

### API (FastAPI on Modal)

The Python backend runs as a FastAPI app deployed on Modal. Routes:

| Route | Description |
|-------|-------------|
| `GET /search` | Top pairings for an ingredient |
| `GET /graph` | Graph data for the flavor network explorer |
| `POST /rate` | Submit a rating, triggers fine-tuning |
| `POST /recipe` | Generate a recipe via Claude API |

### Frontend (Next.js)

A Next.js App Router frontend deployed on Vercel at [flavornet.vercel.app](https://flavornet.vercel.app).

| Page | Route | Description |
|------|-------|-------------|
| Search | `/search` | Ingredient search → top pairings with radar chart and molecule details |
| Rate | `/rate` | Vote on uncertain pairs to improve the model |
| Graph | `/graph` | Interactive PyVis-style flavor network explorer |
| Recipe | `/recipe` | Select surprise ingredients → AI-generated recipe |

## Local Development

### Python backend

#### 1. Create the environment

```bash
conda env create -f environment.yml
conda activate flavor-network
```

This creates a `flavor-network` conda environment using conda-forge for RDKit and pip for PyTorch (ARM64-safe install order).

Verify GPU access on Apple Silicon:

```python
import torch
print(torch.backends.mps.is_available())  # should print True
```

#### 2. Run the data pipeline

```bash
python run_pipeline.py
```

Runs all ingestion stages in order:
- FlavorDB2 scraper (requires network access)
- FooDB join (requires manual download — see below)
- RecipeNLG processing (streams from HuggingFace datasets)
- AllRecipes scraping (polite scraper; may require manual fallback)

**Pipeline flags:**

| Flag | Effect |
|------|--------|
| `--skip-scrape` | Skip FlavorDB2 scraping (use existing cache) |
| `--skip-foodb` | Skip FooDB join (use existing molecules.csv) |
| `--skip-recipes` | Skip RecipeNLG + AllRecipes processing |
| `--force` | Re-run all stages even if output files exist |

Each stage can also be run standalone:

```bash
python data/scrape_flavordb.py
python data/join_foodb.py
python data/process_recipes.py
python data/scrape_allrecipes.py
```

#### 3. Train the model

```bash
modal run modal_train.py
```

#### 4. Run the API

```bash
modal serve api/modal_app.py
```

### Frontend

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Set `NEXT_PUBLIC_API_URL` in `web/.env.local` to point at your Modal API endpoint.

## Manual Data Setup

### FooDB (required)

FooDB compound data must be downloaded manually due to licensing (CC BY-NC 4.0).

1. Visit [foodb.ca/downloads](https://foodb.ca/downloads)
2. Download the CSV export (`foodb_2020_04_07_csv.tar.gz` or current version)
3. Extract to `data/raw/foodb/`:

```bash
tar -xzf foodb_2020_04_07_csv.tar.gz -C data/raw/foodb/ --strip-components=1
```

Expected files under `data/raw/foodb/`:
- `Food.csv` — food/ingredient names
- `Compound.csv` — chemical compound records

### AllRecipes fallback

If the scraper is blocked, create `data/raw/recipes_allrecipes.csv` manually:

| Column | Format | Example |
|--------|--------|---------|
| `recipe_name` | Plain text | `"Pasta Carbonara"` |
| `ingredients` | Comma-separated names | `"egg,pasta,bacon,parmesan"` |

If this file does not exist, the pipeline proceeds using RecipeNLG only.

## Pipeline Output Files

| File | Description |
|------|-------------|
| `data/raw/ingredients.csv` | FlavorDB2 ingredients with molecule lists |
| `data/raw/molecules.csv` | Ingredient-molecule join with FooDB match flag |
| `data/raw/recipes.csv` | Ingredient co-occurrence counts (merged sources) |
| `model/embeddings/` | Trained GNN embeddings |
| `scoring/scored_pairs.pkl` | Precomputed surprise scores |

## Running Tests

```bash
# Full suite (some will fail until data ingestion is complete)
pytest tests/ -v

# Environment + structure only
pytest tests/test_environment.py tests/test_project_structure.py -v
```

Note: memory-intensive tests (training, scoring) run on Modal, not locally.

## Project Structure

```
.
├── environment.yml          # Conda+pip hybrid environment
├── requirements.txt         # Pip-only reference
├── run_pipeline.py          # Master pipeline orchestrator
├── modal_train.py           # Modal training job
├── modal_score.py           # Modal scoring job
├── data/
│   ├── raw/                 # Scraped/downloaded data
│   │   └── foodb/           # FooDB CSVs (manual download)
│   └── processed/           # Cleaned, normalized data
├── graph/                   # Graph construction outputs
├── model/
│   └── embeddings/          # Trained GNN embeddings
├── scoring/
│   ├── compute_scores.py    # Surprise score computation
│   └── scored_pairs.pkl     # Precomputed scores
├── api/
│   ├── main.py              # FastAPI app
│   ├── modal_app.py         # Modal deployment wrapper
│   └── routes/              # search, rate, recipe, graph
├── web/                     # Next.js frontend
│   └── app/
│       ├── search/          # Ingredient search page
│       ├── rate/            # Active learning rating page
│       ├── graph/           # Flavor network explorer
│       └── recipe/          # Recipe generation page
├── logs/                    # Pipeline logs
└── tests/                   # pytest test suite
```

## Data Sources

| Source | Data | License |
|--------|------|---------|
| [FlavorDB2](https://cosylab.iiitd.edu.in/flavordb2/) | Ingredient flavor molecules | Public API |
| [FooDB](https://foodb.ca) | Chemical compound profiles | CC BY-NC 4.0 |
| [RecipeNLG](https://recipenlg.cs.put.poznan.pl/) | Recipe co-occurrence | Research use |
| [AllRecipes](https://www.allrecipes.com) | Recipe co-occurrence | Scraped (polite) |
| [PubChem](https://pubchem.ncbi.nlm.nih.gov/) | SMILES / molecular data | Public domain |

## Research Basis

Based on the flavor pairing hypothesis from [Ahn et al. 2011](https://www.nature.com/articles/srep00196) — ingredients sharing flavor compounds tend to pair well in Western cuisines. This model extends that by scoring _surprise_: pairs that are molecularly compatible but culturally underused, surfacing cross-cultural discoveries the original hypothesis misses.
