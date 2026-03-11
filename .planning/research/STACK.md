# Stack Research

**Domain:** Graph ML + Molecular Informatics + Interactive Demo (Flavor Pairing GNN)
**Researched:** 2026-03-11
**Confidence:** HIGH (core ML stack); MEDIUM (data access layer); LOW (FlavorDB2 scraping specifics)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11.x | Runtime | 3.11 is the sweet spot — 3.12/3.13 have sparse GNN ecosystem support, 3.10 misses performance improvements. PyG, RDKit, and all dependencies confirm 3.11 support. |
| PyTorch | 2.6.0 | Tensor computation + autograd | Stable release (Jan 29, 2025). PyG 2.7 supports it. NOTE: PyTorch no longer publishes on Conda as of 2.6 — pip-only installs required. |
| PyTorch Geometric | 2.7.0 | GNN layers, HeteroData, training utilities | De facto standard for graph ML in Python. Provides `HeteroData`, `GATConv`, `to_hetero()`, `HGTConv`, and link prediction utilities out of the box. |
| RDKit | 2025.03.x | Molecular feature computation from SMILES | Only production-quality cheminformatics library for Python. Computes MW, logP, HBD/HBA, rotatable bonds, TPSA, Morgan fingerprints. No viable alternative. |
| NetworkX | 3.6.1 | Graph construction and intermediate representation | Builds the heterogeneous graph (ingredient + molecule nodes, multi-edge types) before converting to PyG HeteroData. Well-understood API, easy to inspect before conversion. |
| Streamlit | 1.44.x | Interactive web UI | Fastest path to a polished ML demo. Native support for Plotly charts, component embedding for PyVis. No frontend code required. |
| Anthropic SDK | 0.84.0 | Claude API integration for recipe generation | Official SDK for claude-sonnet-4-6 (current default). Async-capable, handles streaming, well-documented. |

### Data Layer

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas | 2.3.x | Tabular data manipulation | FooDB CSV joins, recipe co-occurrence aggregation, feedback.csv for active learning. |
| NumPy | 2.4.2 | Numerical arrays | Feature matrix construction, molecular fingerprint arrays. Used implicitly by pandas and PyTorch. |
| requests | 2.32.x | HTTP scraping | FlavorDB2 JSON endpoint scraping (entities_json, ids 1–1000), PubChem REST API for SMILES lookup. |
| httpx | 0.27.x | Async HTTP | Use instead of requests when parallelizing PubChem lookups — PubChem rate-limits at ~5 req/s, async batching respects limits better. |
| beautifulsoup4 | 4.12.x | HTML parsing | AllRecipes scraping where structured JSON is not returned. Fallback only — prefer structured endpoints first. |
| datasets (HuggingFace) | 3.x | RecipeNLG dataset access | `load_dataset("mbien/recipe_nlg")` pulls 2M+ recipes without manual download. Simplest path to the open recipe corpus. |

### Visualization

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Plotly | 5.x | Radar charts, bar charts | Flavor profile radar chart on Page 1. Use `go.Scatterpolar` for radar. Integrated via `st.plotly_chart`. |
| PyVis | 0.3.2 | Interactive graph explorer | Page 3 interactive flavor graph. Wraps vis.js. Render via `streamlit.components.v1.html()` after saving to HTML. Note: `components.html` size must be set explicitly. |

### ML Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scikit-learn | 1.5.x | Active learning utilities, AUC metric, train/test splits | Uncertainty sampling implementation (entropy of sigmoid output over candidate pairs). `roc_auc_score` for AUC delta display. |
| torch-scatter | 2.1.x | Accelerated sparse reductions for PyG | Optional but speeds up GAT training significantly on large graphs. Install from PyG wheel index matching your torch+CUDA version. |
| torch-sparse | 0.6.x | SparseTensor support for PyG | Optional. Needed if using sparse adjacency representations. |
| tqdm | 4.x | Progress bars | Data scraping and training loops. Low-noise feedback during long pipeline runs. |
| python-dotenv | 1.x | Environment variable management | Load `ANTHROPIC_API_KEY` from `.env` without hardcoding. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| conda (miniforge/mamba) | Environment management | Required for RDKit installation. Use `conda create -c conda-forge -n flavor-net python=3.11 rdkit`. Then activate and pip-install everything else. |
| pip | Package installation | Install PyTorch, PyG, and all other deps via pip inside the conda env. Do NOT use conda for PyTorch 2.6+ (no conda channel). |
| pytest | Unit testing | Test graph validation (≥500 ingredients, ≥2000 molecules), surprise score formula, active learning query output shape. |

---

## Installation

```bash
# Step 1: Create conda env with RDKit (only reliable RDKit install path)
conda create -c conda-forge -n flavor-net python=3.11 rdkit -y
conda activate flavor-net

# Step 2: Install PyTorch (CPU or CUDA — pick one)
# CPU only:
pip install torch==2.6.0+cpu --index-url https://download.pytorch.org/whl/cpu

# CUDA 12.6:
pip install torch==2.6.0+cu126 --index-url https://download.pytorch.org/whl/cu126

# Step 3: Install PyTorch Geometric (core — no optional deps required for basic usage)
pip install torch_geometric==2.7.0

# Step 4: Install optional PyG acceleration libs (match TORCH+CUDA versions)
# Example for torch 2.6.0 + cpu:
pip install pyg_lib torch_scatter torch_sparse \
  -f https://data.pyg.org/whl/torch-2.6.0+cpu.html

# Step 5: Install remaining dependencies
pip install \
  networkx==3.6.1 \
  streamlit \
  anthropic \
  pandas \
  numpy \
  requests \
  httpx \
  beautifulsoup4 \
  datasets \
  plotly \
  pyvis==0.3.2 \
  scikit-learn \
  tqdm \
  python-dotenv

# Step 6: Verify RDKit (must import from conda, not pip)
python -c "from rdkit import Chem; print('RDKit OK')"

# Step 7: Verify PyG + PyTorch
python -c "import torch; import torch_geometric; print(torch.__version__, torch_geometric.__version__)"
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| PyTorch Geometric | DGL (Deep Graph Library) | DGL has strong heterogeneous graph support and better documentation for HeteroData patterns. Switch if the PyG `to_hetero()` + GAT debugging becomes untenable. |
| PyTorch Geometric | GraphBLAS-backed NetworkX | Only relevant if avoiding PyTorch entirely; not viable for GNN training. |
| GATConv + `to_hetero()` | HGTConv (Heterogeneous Graph Transformer) | HGTConv is purpose-built for heterogeneous graphs and may produce better embeddings. More opaque than GAT; switch if GAT attention doesn't differentiate edge types well. |
| HuggingFace `datasets` for RecipeNLG | Manual download from recipenlg.cs.put.poznan.pl | Use manual download if Hugging Face access is unavailable or the hosted dataset version is stale. |
| Recipe1M+ (email request) | RecipeNLG via HuggingFace | Recipe1M+ requires academic affiliation form + email approval (~210GB images, recipe text separate). Use RecipeNLG (2M+ recipes, immediate, HuggingFace-hosted) unless you specifically need the image-recipe pairing. For co-occurrence edges only, RecipeNLG is strictly better. |
| PyVis 0.3.2 | Cytoscape.js via `streamlit-agraph` | `streamlit-agraph` provides a React-based Cytoscape integration with cleaner Streamlit API but less control over physics. Use if PyVis `components.html` iframe sizing becomes a problem. |
| Streamlit | Gradio | Gradio has faster component iteration for ML demos but weaker layout control. Stick with Streamlit for the multi-page structure and Plotly integration this project needs. |
| conda + pip (hybrid) | pip-only (with `rdkit` PyPI wheel) | `pip install rdkit` works for simple use cases but the conda-forge build is more complete (includes SMILES parsing edge cases, drawing utilities). Use pip-only for CI environments where conda is unavailable. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `rdkit-pypi` (pip package) | Historically incomplete; conda-forge build includes full RDKit with all optional components and is updated alongside conda-forge releases. The pip wheel has had missing features on some platforms. | `conda install -c conda-forge rdkit` |
| PyTorch 2.7 or 2.8 | As of March 2026, PyTorch 2.7 is very new (PyG 2.7 officially supports it but the ecosystem around it is less tested). 2.6 is the "proven stable" version. | `torch==2.6.0` |
| Conda for PyTorch | PyTorch dropped the conda channel as of 2.6. Installing `pytorch` from conda pulls stale 2.2.x builds from defaults channel. | pip from download.pytorch.org |
| `recipe1m+` dataset via image files | 210 GB of images irrelevant to this project. The text/recipe portion requires academic email approval with multi-day wait. | `datasets` → `mbien/recipe_nlg` (immediate, 2M+ recipes) or `corbt/all-recipes` on HuggingFace |
| `stvis` (Streamlit PyVis component wrapper) | Thin wrapper around `components.html` with extra indirection. The underlying pattern (`net.save_graph("graph.html"); components.html(open("graph.html").read(), height=600)`) is simple enough to use directly. | `streamlit.components.v1.html` directly |
| `torch-geometric` version < 2.3 | Versions before 2.3 require mandatory installation of torch-scatter, torch-sparse, etc. as hard dependencies. From 2.3 onward, PyG works without them (they become optional performance upgrades). | `torch_geometric>=2.3.0` |
| `openai` SDK | Project specifies Anthropic/Claude for recipe generation. No OpenAI usage. | `anthropic>=0.84.0` |

---

## Stack Patterns by Variant

**If running on CPU-only (no GPU):**
- Use `torch==2.6.0+cpu` from the CPU wheel index
- Install PyG optional deps with `+cpu` suffix in the wheel URL
- Training will be slow (~10-30x vs GPU) but feasible for graph sizes of 500-2500 nodes
- Add `device = torch.device('cpu')` explicitly; checkpoint every 5 epochs

**If running on CUDA (NVIDIA GPU):**
- Verify CUDA version with `nvidia-smi` before installing
- Use matching CUDA suffix: `cu124` for CUDA 12.4, `cu126` for CUDA 12.6
- Install `pyg_lib` (heterogeneous sparse ops acceleration) — meaningful speedup for GAT on HeteroData

**If conda is unavailable (CI/CD, Docker):**
- Use `pip install rdkit` (the PyPI wheel; test that Morgan fingerprints work)
- Accept that some RDKit drawing utilities may not work; this project only needs SMILES → feature computation
- Set `RDKit_MINIMAL=1` if the full build fails

**If AllRecipes bot-blocking is severe:**
- Fall back entirely to `corbt/all-recipes` (HuggingFace) + `mbien/recipe_nlg`
- The project's PROJECT.md explicitly accepts partial data loss from AllRecipes; supplement with open datasets first

---

## Version Compatibility Matrix

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `torch==2.6.0` | `torch_geometric==2.7.0` | Officially supported. PyG 2.7 lists PyTorch 2.6.* as a supported target. |
| `torch==2.6.0` | `pyg_lib`, `torch_scatter`, `torch_sparse` via `torch-2.6.0+{CUDA}` wheel URL | Must match exact torch version + CUDA suffix in the `-f` URL. Mismatches cause silent import failures. |
| `rdkit` (conda-forge 2025.03.x) | `numpy>=2.0`, `pandas>=2.3` | RDKit 2025 is built against NumPy 2.x; no compatibility issues. |
| `pandas>=3.0` | `numpy>=2.0` | Pandas 3.0+ requires NumPy >=2.0. Both are fine on Python 3.11. |
| `pyvis==0.3.2` | `streamlit>=1.30` | PyVis renders to HTML; `streamlit.components.v1.html` works with any recent Streamlit. No direct dependency. |
| `anthropic>=0.84.0` | `claude-sonnet-4-6` (latest), `claude-sonnet-4-5` | MODEL IDs: `claude-sonnet-4-6` is the current default. `claude-sonnet-4-5` still works but 4.6 preferred. Both priced at $3/$15 per million tokens. |
| `torch_geometric` (HeteroData + GATConv) | `add_self_loops=False` required | When using `GATConv` converted via `to_hetero()`, bipartite edges make self-loops undefined. Always set `add_self_loops=False` in GATConv constructor. |

---

## Data Source Access Notes

### FlavorDB2
- **URL:** `https://cosylab.iiitd.edu.in/flavordb2/`
- **Access:** No key required. Public endpoint.
- **Scraping pattern:** Entity JSON at `https://cosylab.iiitd.edu.in/flavordb2/entities_json?entity=N` for N in 1–1000. Add `time.sleep(0.5)` between requests. The site does not document this officially; it is community-known from the original FlavorDB codebase.
- **Confidence:** MEDIUM. Endpoint is functional as of early 2026 but undocumented; it may change without notice. Cache all responses locally on first run.

### FooDB
- **URL:** `https://foodb.ca/downloads`
- **File:** `foodb_2020_4_7_csv.tar.gz` (952 MB, last updated April 2020)
- **Contents:** `compounds.csv`, `foods.csv`, `contents.csv` (compound-food associations), nutrient data.
- **Access:** Direct download, no registration.
- **Note:** Data is from 2020. Acceptable for compound enrichment; do not treat as authoritative for newly identified compounds.

### RecipeNLG (primary open recipe source)
- **Access:** `datasets.load_dataset("mbien/recipe_nlg")` — immediate, no approval required.
- **Size:** 2.2M recipes with structured ingredient lists.
- **Confidence:** HIGH. HuggingFace-hosted, stable, widely used.

### Recipe1M+ (secondary, if needed)
- **Access:** Requires form submission + email approval at `im2recipe.csail.mit.edu`. Academic affiliation expected.
- **Recommendation:** Do NOT block the pipeline on Recipe1M+ access. RecipeNLG alone is sufficient for co-occurrence edge construction.

### PubChem REST API
- **URL:** `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/...`
- **Access:** Free, no key. Rate limit: ~5 req/s.
- **Use:** SMILES retrieval for molecules identified in FlavorDB2 that lack SMILES strings.
- **Strategy:** Use `httpx` async client with semaphore limiting to 4 concurrent requests.

---

## Sources

- [PyTorch Geometric 2.7.0 Installation Docs](https://pytorch-geometric.readthedocs.io/en/2.7.0/install/installation.html) — PyG versions, optional deps, wheel install commands — HIGH confidence
- [PyTorch 2.6 Release Blog](https://pytorch.org/blog/pytorch2-6/) — Confirmed stable Jan 2025, confirmed conda channel dropped — HIGH confidence
- [torch-geometric PyPI](https://pypi.org/project/torch-geometric/) — Latest version 2.7.0 confirmed — HIGH confidence
- [RDKit Installation Docs](https://www.rdkit.org/docs/Install.html) — conda-forge as recommended install path — HIGH confidence
- [PyG Heterogeneous Graph Learning](https://pytorch-geometric.readthedocs.io/en/latest/notes/heterogeneous.html) — GATConv + to_hetero() pattern, HGTConv alternative — HIGH confidence
- [anthropic PyPI](https://pypi.org/project/anthropic/) — Version 0.84.0, Python >=3.9 — HIGH confidence
- [Anthropic Models Overview](https://platform.claude.com/docs/en/about-claude/models/overview) — claude-sonnet-4-6 current default — HIGH confidence
- [mbien/recipe_nlg on HuggingFace](https://huggingface.co/datasets/mbien/recipe_nlg) — 2.2M recipes, no-registration access — HIGH confidence
- [FooDB Downloads](https://foodb.ca/downloads) — Single CSV archive from 2020, 952MB — HIGH confidence
- [FlavorDB2](https://cosylab.iiitd.edu.in/flavordb2/) — No documented REST API; entity scraping is community-known pattern — LOW confidence (endpoint stability)
- [Recipe1M+ MIT](https://im2recipe.csail.mit.edu/) — Requires academic email approval — HIGH confidence (access process)
- [pandas PyPI](https://pypi.org/project/pandas/) — 3.0.1 latest, requires Python >=3.11 — HIGH confidence
- [NumPy releases](https://numpy.org/news/) — 2.4.2 latest stable — HIGH confidence
- [pyvis PyPI](https://pypi.org/project/pyvis/) — 0.3.2, conda-forge updated Jan 2025 — HIGH confidence
- [PyVis + Streamlit integration](https://github.com/kennethleungty/Pyvis-Network-Graph-Streamlit) — `components.v1.html` pattern confirmed — MEDIUM confidence

---

*Stack research for: Flavor Pairing Network — GNN + Molecular Informatics + Streamlit Demo*
*Researched: 2026-03-11*
