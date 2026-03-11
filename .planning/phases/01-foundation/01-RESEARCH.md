# Phase 1: Foundation - Research

**Researched:** 2026-03-11
**Domain:** Python environment setup (conda+pip hybrid, Apple Silicon), web scraping (FlavorDB2, AllRecipes), data ingestion (FooDB CSV join, RecipeNLG streaming)
**Confidence:** MEDIUM-HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Pipeline Orchestration**: Single `run_pipeline.py` master script calling each stage in order with flags `--skip-scrape`, `--skip-foodb`, etc. to resume. Each script also runs standalone (e.g., `python data/scrape_flavordb.py`). Setup instructions in README.md quickstart.
- **Progress & Logging UX**: tqdm progress bars per batch; all output logged to `logs/pipeline.log`; console shows progress + summary. Summary table printed at end of each script with counts/percentages.
- **AllRecipes Handling**: Polite scraper with delays and user-agent headers. If bot-blocking detected, save partial results and print manual instructions. Manual fallback: user supplies `data/raw/recipes_allrecipes.csv` with columns: recipe_name, ingredients (comma-separated). AllRecipes and RecipeNLG co-occurrence counts merged into single co-occurrence table: ingredient_a, ingredient_b, count.
- **Failure Behavior**: Always continue + summarize. If FooDB fuzzy match yields <300 ingredients: print prominent WARNING with count, continue. FlavorDB cache: use silently without hitting network if cache exists. No automatic threshold-lowering or retry escalation.

### Claude's Discretion
- Exact delays and retry logic for AllRecipes scraper
- Log format details (timestamp format, log rotation)
- FooDB CSV download method (requests vs manual instructions)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENV-01 | Project runs on Apple Silicon (M2) using conda+pip hybrid install (RDKit via conda-forge, PyTorch via pip wheel index) | Confirmed working pattern: conda-forge for RDKit first, then pip for PyTorch after env activation |
| ENV-02 | PyTorch uses MPS backend on Apple Silicon for training acceleration | MPS is included in standard macOS PyTorch pip wheels; verified via `torch.backends.mps.is_available()` |
| ENV-03 | All dependency versions pinned in environment.yml and requirements.txt (PyTorch 2.6, PyG 2.7, RDKit 2025.03) | PyG 2.7 docs confirmed; RDKit from conda-forge; install order critical |
| ENV-04 | Project structure matches spec: data/, graph/, model/, scoring/, app/ directories | Pure filesystem setup; no dependencies |
| DATA-01 | FlavorDB2 scraper hits entities_json?id=1–1000, handles 404s gracefully, caches all responses locally | Endpoint confirmed at `cosylab.iiitd.edu.in/flavordb/entities_json?id=X`; ~43 missing IDs in 1–1000 range; requests_cache recommended |
| DATA-02 | Scraper extracts ingredient name, category, and flavor molecule list (pubchem_id, common_name, flavor_profile) | JSON fields confirmed: entity_alias_readable, category_readable, molecules[].pubchem_id, common_name, flavor_profile |
| DATA-03 | FooDB compounds and foods CSVs joined via fuzzy name matching (RapidFuzz token_sort_ratio > 85) | FooDB download is 952MB tar.gz; RapidFuzz 3.x is the correct library; process_one_by_one for memory |
| DATA-04 | RecipeNLG loaded via HuggingFace in streaming/chunked mode and processed into co-occurrence counts | Dataset name: `mbien/recipe_nlg`; 2.2M recipes; streaming=True is the mandatory pattern |
| DATA-05 | AllRecipes scraper fetches top 500 recipes from 10 categories; handles bot-blocking gracefully | Polite scraper with random delays and browser-like headers; BeautifulSoup4 + requests recommended |
| DATA-06 | Raw data saved as ingredients.csv, molecules.csv, recipes.csv in data/raw/ | Output schema must be defined and consistent for Phase 2 consumption |
</phase_requirements>

---

## Summary

Phase 1 is a data acquisition and environment setup phase. The two main workstreams are independent: (1) building and verifying the conda+pip hybrid environment on Apple Silicon, and (2) implementing scrapers and data loaders that produce three well-structured CSVs in `data/raw/`.

The critical risk is the conda+pip hybrid install order. RDKit must be installed via conda-forge before PyTorch is installed via pip — doing this in reverse causes solver conflicts on Apple Silicon. PyTorch Geometric 2.7 does not require any optional C++ extensions for the operations used in Phase 1 (no GNN training yet); a plain `pip install torch_geometric` is sufficient until Phase 3.

The data acquisition work involves three patterns: (a) a paginated JSON API scraper with filesystem cache (FlavorDB2), (b) a large streaming dataset with co-occurrence counting (RecipeNLG + AllRecipes), and (c) a CSV-join with fuzzy matching (FooDB). All three must handle partial/failed states gracefully and continue without crashing, which is the defined failure behavior.

**Primary recommendation:** Install RDKit via conda-forge first, pin all conda packages, then install PyTorch + PyG via pip using the `pip:` section of environment.yml. Use `requests_cache` with SQLite backend for FlavorDB2 (zero-setup, idempotent re-runs). Load RecipeNLG exclusively with `streaming=True` — the 2.2M recipe dataset cannot fit in 8GB RAM.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rdkit | 2025.03 (conda-forge) | Molecule parsing, SMILES sanitization used in DATA-03 | Only reliable binary distribution for ARM64 macOS is conda-forge |
| torch | 2.6.x (pip) | Tensor ops, MPS backend | Must be pip-installed after RDKit to avoid conda solver conflicts |
| torch_geometric | 2.7.x (pip) | Graph neural network framework (Phase 3+) | Referenced in requirements; minimal footprint in Phase 1 |
| requests | 2.32.x | HTTP client for FlavorDB2 scraper | Standard; used with requests_cache |
| requests_cache | 1.2.x | Transparent HTTP disk cache | Zero-code-change caching; SQLite backend is the default and works offline |
| datasets (huggingface) | 3.x | Streaming loader for RecipeNLG | Official HuggingFace library; `streaming=True` avoids loading 2.2M rows into RAM |
| rapidfuzz | 3.x | Fuzzy string matching for FooDB join | C++-backed, 5-100x faster than fuzzywuzzy; `token_sort_ratio` is the correct scorer for ingredient name variants |
| pandas | 2.x | DataFrame operations for CSV joins and output | Standard data manipulation |
| tqdm | 4.x | Progress bars | Works with `tqdm.contrib.logging.logging_redirect_tqdm` to keep log files clean |
| beautifulsoup4 | 4.x | HTML parsing for AllRecipes scraper | Industry standard; paired with html.parser |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mamba | latest | Faster conda solver | Substitute for `conda` when `conda env create` is too slow or OOMs |
| python-dotenv | 1.x | Environment variable management | If any API keys are needed in future phases |
| loguru | 0.7.x | Structured logging alternative | Use if standard `logging` module formatting proves unwieldy; optional |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| requests_cache | Manual JSON file cache in data/raw/flavordb_cache/ | Manual cache requires custom key logic; requests_cache handles etags, 404 caching, expiry automatically |
| datasets (HuggingFace) | pandas read_csv with chunksize | HuggingFace streaming is cleaner API; chunksize works but requires manual state management |
| rapidfuzz token_sort_ratio | difflib.SequenceMatcher | RapidFuzz is 5-100x faster; token_sort_ratio handles "garlic, minced" vs "minced garlic" word-order variance |
| beautifulsoup4 | scrapy | Scrapy is heavyweight for a single-domain polite scraper; BS4 + requests is sufficient |

**Installation:**
```bash
# Step 1: create environment with conda-forge packages FIRST
conda env create -f environment.yml

# Step 2: activate before pip installs
conda activate flavor-network

# Step 3: pip installs happen inside environment.yml pip: section or manually after
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install torch_geometric
pip install requests requests_cache datasets rapidfuzz pandas tqdm beautifulsoup4
```

---

## Architecture Patterns

### Recommended Project Structure
```
flavor-network/
├── data/
│   ├── raw/                     # ingredients.csv, molecules.csv, recipes.csv
│   │   └── flavordb_cache/      # requests_cache SQLite file lives here (or .sqlite in data/raw/)
│   └── processed/               # Phase 2 outputs
├── graph/                       # Phase 3 outputs
├── model/                       # Phase 4 outputs
├── scoring/                     # Phase 5 outputs
├── app/                         # Phase 6 Streamlit
├── logs/
│   └── pipeline.log
├── run_pipeline.py              # Master orchestrator
├── environment.yml
├── requirements.txt             # pip-only packages for reference
└── README.md
```

### Pattern 1: Idempotent Stage Execution
**What:** Each pipeline stage checks whether its output file already exists before doing any work.
**When to use:** Every stage in run_pipeline.py and in standalone scripts.
**Example:**
```python
# Source: CONTEXT.md — locked decision on checkpoint resumption
import os

INGREDIENTS_CSV = "data/raw/ingredients.csv"

def stage_scrape_flavordb(force=False):
    if not force and os.path.exists(INGREDIENTS_CSV):
        print(f"[SKIP] {INGREDIENTS_CSV} already exists. Use --force to re-scrape.")
        return
    # ... scraping logic ...
```

### Pattern 2: requests_cache for FlavorDB2
**What:** Drop-in transparent HTTP cache backed by SQLite. First run fetches from network; all subsequent runs read from disk.
**When to use:** FlavorDB2 scraper. Cache 404 responses too (they indicate missing entity IDs — don't re-request them).
**Example:**
```python
# Source: https://requests-cache.readthedocs.io/
import requests_cache

session = requests_cache.CachedSession(
    cache_name="data/raw/flavordb_cache",
    backend="sqlite",
    allowable_codes=[200, 404],   # cache 404s — entity gaps are stable
    expire_after=None             # never expire; re-run is safe
)

resp = session.get(f"https://cosylab.iiitd.edu.in/flavordb/entities_json?id={entity_id}")
if resp.status_code == 404:
    continue  # log and skip
data = resp.json()
```

### Pattern 3: RecipeNLG Streaming Co-occurrence
**What:** Stream 2.2M recipes without loading into RAM; accumulate co-occurrence counts in a dict or Counter.
**When to use:** DATA-04 — mandatory on 8GB RAM target machine.
**Example:**
```python
# Source: https://huggingface.co/docs/datasets/en/stream
from datasets import load_dataset
from collections import Counter
from itertools import combinations

dataset = load_dataset("mbien/recipe_nlg", streaming=True, split="train")
co_occurrence = Counter()

for recipe in dataset:
    # 'ner' field has clean ingredient names from NER
    ingredients = list(set(recipe["ner"]))
    for a, b in combinations(sorted(ingredients), 2):
        co_occurrence[(a, b)] += 1
```

### Pattern 4: FooDB Fuzzy Join
**What:** Fuzzy-match FooDB food names against FlavorDB2 ingredient names using RapidFuzz. Process row-by-row, not as a matrix, to keep memory bounded.
**When to use:** DATA-03.
**Example:**
```python
# Source: https://rapidfuzz.github.io/RapidFuzz/
from rapidfuzz import process, fuzz

def fuzzy_join(flavordb_names, foodb_name, threshold=85):
    match, score, _ = process.extractOne(
        foodb_name,
        flavordb_names,
        scorer=fuzz.token_sort_ratio
    )
    if score >= threshold:
        return match, score
    return None, score
```

### Pattern 5: tqdm + logging Integration
**What:** Use `logging_redirect_tqdm` context manager so log messages don't break progress bars. File handler on `logs/pipeline.log` is unaffected.
**When to use:** All scraping loops.
**Example:**
```python
# Source: https://tqdm.github.io/docs/contrib.logging/
import logging
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

logging.basicConfig(
    handlers=[
        logging.FileHandler("logs/pipeline.log"),
        logging.StreamHandler()
    ],
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

with logging_redirect_tqdm():
    for entity_id in tqdm(range(1, 1001), desc="FlavorDB2 entities"):
        # logger.warning(...) will not break progress bar
        pass
```

### Anti-Patterns to Avoid
- **Installing PyTorch via conda before conda-forge packages:** The PyTorch conda channel and conda-forge have incompatible libstdc++ versions on ARM64. Always install PyTorch via pip after conda env is created.
- **Loading RecipeNLG without streaming=True:** `load_dataset("mbien/recipe_nlg")` without streaming will attempt to materialize 2.2M recipes into RAM. Will OOM on 8GB.
- **Building a hand-written JSON file cache for FlavorDB2:** requests_cache handles cache key generation, 404 caching, and SQLite ACID writes correctly. Custom solutions break on concurrent access and don't handle HTTP headers correctly.
- **Using fuzz.ratio instead of token_sort_ratio for ingredient names:** Ingredient names appear with qualifiers ("garlic, roasted" vs "roasted garlic"). token_sort_ratio normalizes token order before comparing, which is critical for food data.
- **Printing summary tables with print() inside tqdm loops:** Use `tqdm.write()` or log at INFO level within `logging_redirect_tqdm` context.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP disk cache for scrapers | Custom JSON file per URL | requests_cache | Handles etag validation, 404 caching, concurrent safety, expiry, and SQLite ACID transactions |
| Fuzzy string matching | Levenshtein loop in Python | rapidfuzz | C++ implementation; handles token ordering, partial match, 100x faster on 1000+ ingredient lists |
| Streaming large HuggingFace datasets | Custom CSV chunker | `datasets` with `streaming=True` | Handles sharding, decompression, and lazy iteration natively |
| Progress bars that coexist with logging | Custom print-to-stderr | tqdm + logging_redirect_tqdm | Solved problem; hand-rolled versions break on multiline log messages |

**Key insight:** The data acquisition domain has well-solved infrastructure problems. Every "infrastructure" item above has an idiomatic Python library solution with years of production use.

---

## Common Pitfalls

### Pitfall 1: PyTorch / RDKit conda solver conflict on ARM64
**What goes wrong:** Installing PyTorch via `conda install pytorch` alongside RDKit from conda-forge causes `libgcc-ng` and `_libgcc_mutex` conflicts. Install fails or produces a broken environment.
**Why it happens:** PyTorch's conda channel pins older glibc/libstdc++ versions that conflict with conda-forge's newer builds. On Linux/x86 these often resolve; on ARM64 macOS they do not.
**How to avoid:** environment.yml uses `channels: [conda-forge]` only for conda packages; PyTorch is listed under `pip:` in the `dependencies:` section and is installed after `conda env create`.
**Warning signs:** `conda env create` taking >20 minutes or printing "solving environment: failed" retries.

### Pitfall 2: FlavorDB2 endpoint is the OLD `/flavordb/` path, not `/flavordb2/`
**What goes wrong:** The live site is at `/flavordb2/` but the entities_json API endpoint is at `/flavordb/entities_json?id=X` (no "2" in the path). Using the wrong base URL returns HTML, not JSON.
**Why it happens:** FlavorDB2 reused the legacy API backend.
**How to avoid:** Hardcode `BASE_URL = "https://cosylab.iiitd.edu.in/flavordb/entities_json?id="`. Validate that response Content-Type is `application/json` on first fetch.
**Warning signs:** Response body starts with `<!DOCTYPE` or `<html`.

### Pitfall 3: FooDB download is 952MB tar.gz requiring manual extraction
**What goes wrong:** Assuming FooDB has a direct machine-readable download URL and attempting to programmatically wget it. The download page is CC BY-NC 4.0 licensed; automated download should verify license compliance.
**Why it happens:** FooDB provides a single large archive, not per-table CSVs. The download is at `foodb.ca/downloads`.
**How to avoid:** Provide clear instructions in README for manual download and extraction. The pipeline script should check for `data/raw/foodb/` existence and print instructions if missing (similar to AllRecipes fallback pattern).
**Warning signs:** Pipeline hangs on a large HTTP request with no progress.

### Pitfall 4: RecipeNLG `ner` field vs `ingredients` field for co-occurrence
**What goes wrong:** Using `ingredients` (raw strings like "2 cups flour, sifted") instead of `ner` (NER-cleaned tokens like "flour") causes every pair to be unique and co-occurrence counts to be 1.
**Why it happens:** The `ingredients` field is raw text with quantities and qualifiers. The `ner` field is the cleaned named-entity list.
**How to avoid:** Always use `recipe["ner"]` for co-occurrence counting.
**Warning signs:** Co-occurrence Counter has no entry with count > 5 after processing 10,000 recipes.

### Pitfall 5: AllRecipes 403/429 on first request due to missing Accept headers
**What goes wrong:** The scraper is immediately blocked because requests' default headers lack `Accept`, `Accept-Language`, and browser-like `User-Agent`. AllRecipes detects this on the first request.
**Why it happens:** AllRecipes uses CDN-level bot detection that checks for browser-like header profiles.
**How to avoid:** Set a realistic header bundle on the requests.Session object before any request. Add `time.sleep(random.uniform(2, 5))` between requests.
**Warning signs:** First response returns 403 or redirects to a Cloudflare challenge page.

### Pitfall 6: PyTorch Geometric optional wheels for PyTorch 2.6 vs 2.7
**What goes wrong:** The PyG wheel index at `data.pyg.org/whl/torch-${TORCH}+${CUDA}.html` requires an exact PyTorch version match. If requirements.txt pins `torch==2.6.0` but the wheel URL uses `2.7.0`, pyg_lib/torch_scatter won't install.
**Why it happens:** Optional C++ extensions (torch_scatter, torch_sparse) are compiled against a specific torch ABI.
**How to avoid:** In Phase 1, only install `pip install torch_geometric` (pure Python core). Defer optional C++ extensions until Phase 3 if they are needed. Verify with `python -c "import torch_geometric"` only.
**Warning signs:** `pip install pyg_lib torch_scatter` fails with "no matching distribution found."

---

## Code Examples

Verified patterns from official sources:

### environment.yml structure (conda+pip hybrid)
```yaml
# Source: conda documentation — conda-forge first, pip after
name: flavor-network
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.12
  - rdkit=2025.03
  - numpy
  - pip
  - pip:
    - torch==2.6.*
    - torchvision
    - torchaudio
    - torch_geometric==2.7.*
    - requests
    - requests-cache
    - datasets
    - rapidfuzz
    - pandas
    - tqdm
    - beautifulsoup4
```

### FlavorDB2 entity JSON response structure
```python
# Source: github.com/tarek-kerbedj/flavor_db2.0 (community scraper)
# Confirmed fields from JSON response
{
    "entity_id": 1,
    "entity_alias_readable": "Bakery products",
    "entity_alias_synonyms": ["bread", "pastry"],
    "natural_source_name": "Triticum aestivum",
    "category_readable": "Bakery products",
    "molecules": [
        {
            "pubchem_id": 12345,
            "common_name": "2-acetyl pyrrole",
            "flavor_profile": "nutty, roasted"
        }
        # ...
    ]
}
```

### MPS device verification
```python
# Source: developer.apple.com/metal/pytorch/
import torch

device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Using device: {device}")
# Expected on M2: "Using device: mps"
```

### run_pipeline.py argument structure
```python
# Source: CONTEXT.md locked decisions
import argparse

parser = argparse.ArgumentParser(description="Flavor Network data pipeline")
parser.add_argument("--skip-scrape", action="store_true", help="Skip FlavorDB2 scraping")
parser.add_argument("--skip-foodb", action="store_true", help="Skip FooDB CSV join")
parser.add_argument("--skip-recipes", action="store_true", help="Skip recipe co-occurrence")
parser.add_argument("--force", action="store_true", help="Re-run all stages even if outputs exist")
args = parser.parse_args()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| fuzzywuzzy for string matching | rapidfuzz | 2020 | 5-100x faster; same API; MIT license |
| Load full dataset into DataFrame | HuggingFace streaming IterableDataset | 2021 | Enables processing datasets larger than RAM |
| requests + manual cache dict | requests_cache | 2012, stable | Transparent caching without code changes |
| conda install pytorch | pip install torch (after conda env) | 2022 | Avoids ARM64 glibc conflicts |

**Deprecated/outdated:**
- `fuzzywuzzy`: Replaced by RapidFuzz. fuzzywuzzy is slower and has GPL-adjacent licensing. Do not use.
- `conda install pytorch -c pytorch`: Causes solver conflicts with conda-forge on ARM64. Do not use.
- FlavorDB1 endpoint (`/flavordb/entities_json?id=X`): This is actually still the correct path — the "2" only appears in the site URL, not the API path. Confirmed working.

---

## Open Questions

1. **FooDB exact column names for join**
   - What we know: FooDB provides `foods` and `compounds` tables in the CSV archive
   - What's unclear: The exact column names for food name, compound name, and nutrient columns until the tar.gz is extracted
   - Recommendation: Provide `foodb_schema.md` in data/ after first extraction, or add a `data/inspect_foodb.py` script that prints column names

2. **FlavorDB2 entity ID upper bound**
   - What we know: ~1000 IDs, ~43 are missing (404), 936 natural ingredients documented in the paper
   - What's unclear: Whether IDs above 1000 exist in the live database (the paper was from 2022)
   - Recommendation: Scrape IDs 1–1100 and stop after 10 consecutive 404s to handle any expansion

3. **AllRecipes HTML structure stability**
   - What we know: AllRecipes uses a structured recipe schema and JSON-LD on most pages
   - What's unclear: Whether the current DOM structure matches any available scraping examples from 2024+
   - Recommendation: Write the scraper to target JSON-LD `<script type="application/ld+json">` blocks (more stable than CSS selectors) and fall back to BeautifulSoup CSS parsing if absent

4. **PyG 2.7 vs PyTorch 2.6 compatibility**
   - What we know: PyG 2.7 docs say it requires PyTorch 2.7.*
   - What's unclear: Whether PyG 2.7.0 actually works with PyTorch 2.6.x (sometimes minor version is flexible)
   - Recommendation: Pin `torch_geometric` without a version constraint initially; let pip resolve against the installed PyTorch 2.6. If incompatible, downgrade to PyG 2.6.x. Verify with `python -c "import torch_geometric; print(torch_geometric.__version__)"`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (to be installed in Wave 0) |
| Config file | none — see Wave 0 |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENV-01 | `import torch, torch_geometric, rdkit` succeeds | smoke | `pytest tests/test_environment.py::test_imports -x` | Wave 0 |
| ENV-02 | `torch.backends.mps.is_available()` returns True | smoke | `pytest tests/test_environment.py::test_mps_available -x` | Wave 0 |
| ENV-03 | Version strings match pinned versions | smoke | `pytest tests/test_environment.py::test_versions -x` | Wave 0 |
| ENV-04 | Required directories exist | unit | `pytest tests/test_project_structure.py::test_directories -x` | Wave 0 |
| DATA-01 | FlavorDB2 cache file exists and contains at least 900 entries | integration | `pytest tests/test_flavordb.py::test_cache_populated -x` | Wave 0 |
| DATA-02 | ingredients.csv has required columns (name, category, molecules_json) | unit | `pytest tests/test_flavordb.py::test_ingredients_schema -x` | Wave 0 |
| DATA-03 | FooDB join produces >= 300 matched ingredients | integration | `pytest tests/test_foodb.py::test_join_count -x` | Wave 0 |
| DATA-04 | recipes.csv co-occurrence table has > 1000 rows | integration | `pytest tests/test_recipes.py::test_cooccurrence_count -x` | Wave 0 |
| DATA-05 | AllRecipes scraper runs without crash (partial OK) | integration | `pytest tests/test_allrecipes.py::test_scraper_runs -x` | Wave 0 |
| DATA-06 | data/raw/ contains ingredients.csv, molecules.csv, recipes.csv | unit | `pytest tests/test_outputs.py::test_output_files_exist -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_environment.py tests/test_project_structure.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — test package init
- [ ] `tests/test_environment.py` — covers ENV-01, ENV-02, ENV-03
- [ ] `tests/test_project_structure.py` — covers ENV-04
- [ ] `tests/test_flavordb.py` — covers DATA-01, DATA-02
- [ ] `tests/test_foodb.py` — covers DATA-03
- [ ] `tests/test_recipes.py` — covers DATA-04
- [ ] `tests/test_allrecipes.py` — covers DATA-05
- [ ] `tests/test_outputs.py` — covers DATA-06
- [ ] Framework install: `pip install pytest` (not yet in environment)

---

## Sources

### Primary (HIGH confidence)
- [pytorch-geometric.readthedocs.io/en/2.7.0/install](https://pytorch-geometric.readthedocs.io/en/2.7.0/install/installation.html) — PyG 2.7 installation requirements
- [huggingface.co/datasets/mbien/recipe_nlg](https://huggingface.co/datasets/mbien/recipe_nlg) — Dataset schema, size, streaming usage
- [huggingface.co/docs/datasets/en/stream](https://huggingface.co/docs/datasets/en/stream) — Streaming API documentation
- [requests-cache.readthedocs.io](https://requests-cache.readthedocs.io/) — requests_cache API, SQLite backend, 404 caching
- [rapidfuzz.github.io/RapidFuzz](https://rapidfuzz.github.io/RapidFuzz/) — token_sort_ratio scorer API
- [rdkit.org/docs/Install.html](https://www.rdkit.org/docs/Install.html) — conda-forge install command
- [tqdm.github.io/docs/contrib.logging](https://tqdm.github.io/docs/contrib.logging/) — logging_redirect_tqdm

### Secondary (MEDIUM confidence)
- [github.com/tarek-kerbedj/flavor_db2.0](https://github.com/tarek-kerbedj/flavor_db2.0) — FlavorDB2 community scraper, JSON field names confirmed
- [cosylab.iiitd.edu.in/flavordb2/](https://cosylab.iiitd.edu.in/flavordb2/) — Live database, confirmed 936 ingredients, 25595 molecules
- [foodb.ca/downloads](https://foodb.ca/downloads) — FooDB download size (952MB tar.gz), CC BY-NC 4.0 license
- [developer.apple.com/metal/pytorch/](https://developer.apple.com/metal/pytorch/) — MPS backend availability check pattern

### Tertiary (LOW confidence)
- Community reports of PyG 2.7 requiring PyTorch 2.7 — needs empirical validation against PyTorch 2.6

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — confirmed from official docs and live sites
- Architecture: HIGH — patterns are from locked decisions in CONTEXT.md
- Pitfalls: MEDIUM — FlavorDB2 endpoint path confirmed; FooDB column names unconfirmed until download
- Validation: MEDIUM — test structure is greenfield, no existing infrastructure to verify against

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (FlavorDB2 endpoint may change without notice; verify first on re-run)
