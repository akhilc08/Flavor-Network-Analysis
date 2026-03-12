# Flavor Network Analysis

A graph neural network system that surfaces ingredient pairs that are molecularly
compatible but culturally underused. The core metric is a _surprise score_: how
unexpectedly compatible two ingredients are given their molecular similarity and
how rarely they appear together in real recipes. Built on FlavorDB2 compound data,
FooDB molecular profiles, RecipeNLG co-occurrence statistics, and a heterogeneous
GNN trained with InfoNCE contrastive loss.

## Quickstart

### 1. Create the environment

```bash
conda env create -f environment.yml
```

This creates a `flavor-network` conda environment using conda-forge for RDKit and
pip for PyTorch (ARM64-safe install order — do not change the channel order).

### 2. Activate the environment

```bash
conda activate flavor-network
```

Verify GPU access on Apple Silicon:

```python
import torch
print(torch.backends.mps.is_available())  # should print True
```

### 3. Run the pipeline

```bash
python run_pipeline.py
```

The pipeline runs all data ingestion stages in order:
- FlavorDB2 scraper (requires network access)
- FooDB join (requires manual download — see below)
- RecipeNLG processing (streams from HuggingFace datasets)
- AllRecipes scraping (polite scraper; may require manual fallback — see below)

**Pipeline flags** (resume or skip stages):

| Flag | Effect |
|------|--------|
| `--skip-scrape` | Skip FlavorDB2 scraping (use existing cache) |
| `--skip-foodb` | Skip FooDB join (use existing molecules.csv) |
| `--skip-recipes` | Skip RecipeNLG + AllRecipes processing |
| `--force` | Re-run all stages even if output files already exist |

Each stage can also be run standalone:

```bash
python data/scrape_flavordb.py
python data/join_foodb.py
python data/process_recipes.py
python data/scrape_allrecipes.py
```

## Manual Data Setup

### FooDB (required)

FooDB compound data is not scraped — it must be downloaded manually due to
licensing (CC BY-NC 4.0).

1. Visit [foodb.ca/downloads](https://foodb.ca/downloads)
2. Download the CSV export (foodb_2020_04_07_csv.tar.gz or current version)
3. Extract to `data/raw/foodb/`:

```bash
tar -xzf foodb_2020_04_07_csv.tar.gz -C data/raw/foodb/ --strip-components=1
```

The pipeline expects these files under `data/raw/foodb/`:
- `Food.csv` — food/ingredient names
- `Compound.csv` — chemical compound records

### AllRecipes fallback

The AllRecipes scraper uses polite delays and browser-like headers. If it
detects bot-blocking (HTTP 403, CAPTCHA, or zero results), it saves any
partial results and exits with a clear message.

If the scraper is blocked and you want to supply data manually, create:

```
data/raw/recipes_allrecipes.csv
```

with the following columns:

| Column | Format | Example |
|--------|--------|---------|
| `recipe_name` | Plain text | `"Pasta Carbonara"` |
| `ingredients` | Comma-separated ingredient names | `"egg,pasta,bacon,parmesan"` |

Example CSV:

```csv
recipe_name,ingredients
Pasta Carbonara,"egg,pasta,bacon,parmesan"
Chicken Tikka Masala,"chicken,yogurt,tomato,garam masala,onion"
Chocolate Lava Cake,"chocolate,butter,egg,sugar,flour"
```

The pipeline merges AllRecipes and RecipeNLG co-occurrence counts into a single
`data/raw/recipes.csv` table. If `recipes_allrecipes.csv` does not exist, the
pipeline proceeds using RecipeNLG only.

## Output Files

After the full pipeline runs:

| File | Description |
|------|-------------|
| `data/raw/ingredients.csv` | FlavorDB2 ingredients with molecule lists |
| `data/raw/molecules.csv` | Ingredient-molecule join with FooDB match flag |
| `data/raw/recipes.csv` | Ingredient co-occurrence counts (merged sources) |

These files feed Phase 2 (feature engineering) and Phase 3 (graph construction).

## Running Tests

```bash
# Full test suite (some will FAIL until data ingestion is complete — expected)
pytest tests/ -v

# Environment + structure only (should all pass after setup)
pytest tests/test_environment.py tests/test_project_structure.py -v
```

## Project Structure

```
.
├── environment.yml        # Conda+pip hybrid environment spec
├── requirements.txt       # Pip-only reference (not for env creation)
├── run_pipeline.py        # Master pipeline orchestrator
├── data/
│   ├── raw/               # Raw scraped/downloaded data
│   │   └── foodb/         # FooDB CSVs (manual download)
│   └── processed/         # Cleaned, normalized data
├── graph/                 # Graph construction outputs
├── model/
│   └── embeddings/        # Trained GNN embeddings
├── scoring/               # Surprise score computation
├── app/                   # Streamlit demo app
├── logs/                  # Pipeline logs (logs/pipeline.log)
└── tests/                 # pytest test suite
```
