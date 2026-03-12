# Phase 3: Graph Construction - Research

**Researched:** 2026-03-11
**Domain:** PyTorch Geometric HeteroData construction, link prediction splits, leakage prevention
**Confidence:** HIGH (core PyG API), MEDIUM (RandomLinkSplit edge-type behavior), HIGH (RDKit BulkTanimotoSimilarity)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Split **co-occurs edges only** (ingredient→ingredient) for train/val/test — 70 / 15 / 15
- Negative sampling ratio: 1.0 (1 negative per positive)
- Message-passing graph uses training edges only; val and test edges excluded from edge_index
- Zero test-edge leakage asserted with an explicit assertion before saving
- Hard stop on validation gate: ≥500 ingredient nodes, ≥2000 molecule nodes, all 3 edge types present
- Diagnostics table format: `✓ Ingredient nodes: 612 found (>=500)` / `✗ ... N found, M required`
- After diagnostics table, print remediation hint: "Run Phase 2 feature engineering and verify data/processed/ parquet files exist"
- No partial graph saved on failure — clean exit
- Save as dict: `torch.save({"graph": hetero_data, "ingredient_id_to_idx": ..., "molecule_id_to_idx": ...}, "graph/hetero_data.pt")`
- Also save `graph/index_maps.json` for human readability
- tqdm progress bars for edge construction loops; summary table on success; logs to `logs/pipeline.log`
- Script runnable standalone: `python graph/build_graph.py`
- `run_pipeline.py` calls it; skip if `graph/hetero_data.pt` already exists

### Claude's Discretion
- All gray areas delegated to Claude — decisions optimized for portfolio quality and minimum bugs
- No specific implementation preferences from user

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GRAPH-01 | Heterogeneous graph constructed manually as PyG HeteroData (not via from_networkx()); explicit ingredient_id_to_idx and molecule_id_to_idx dicts maintained | HeteroData construction API section below |
| GRAPH-02 | Ingredient nodes feature vector = concat([multimodal features, mean-pooled Morgan fingerprints, flavor profile vector]) | Feature vector construction section below |
| GRAPH-03 | Molecule nodes feature vector = RDKit descriptors + Morgan fingerprints | Feature vector construction section below |
| GRAPH-04 | Ingredient→Molecule "contains" edges with weight = FooDB concentration if available, else 1.0 | Edge construction patterns below |
| GRAPH-05 | Ingredient→Ingredient "co-occurs" edges with weight = normalized co-occurrence count | Edge construction patterns below |
| GRAPH-06 | Molecule→Molecule "structurally similar" edges for Tanimoto similarity > 0.7 | Tanimoto-to-edge construction section below |
| GRAPH-07 | Validation gate: ≥500 ingredient nodes, ≥2000 molecule nodes, all 3 edge types present | Validation gate pattern below |
| GRAPH-08 | Link prediction train/val/test split with zero test-edge leakage asserted | RandomLinkSplit section below |
| GRAPH-09 | Graph saved as graph/hetero_data.pt | Saving/loading section below |
</phase_requirements>

---

## Summary

Phase 3 builds a heterogeneous PyTorch Geometric graph from the parquet files Phase 2 produces. The primary technical risks are: (1) `RandomLinkSplit` behavior on HeteroData with multiple edge types where only one edge type should be split, and (2) memory-efficient pairwise Tanimoto edge construction for ~2000 molecules. Both risks are resolvable with verified patterns documented below.

The core execution sequence is: load parquets → build index dicts → construct node feature tensors → construct edge_index tensors → assemble HeteroData → run validation gate → apply RandomLinkSplit to co-occurs edges only → assert zero leakage → save. The split produces three HeteroData objects (train/val/test); only train_data is saved as the message-passing graph; val and test edge supervision labels are embedded alongside it.

**Primary recommendation:** Use `RandomLinkSplit(edge_types=[('ingredient','co_occurs','ingredient')], rev_edge_types=[None], num_val=0.15, num_test=0.15, neg_sampling_ratio=1.0)`. Non-listed edge types (contains, structurally_similar) are inherited unchanged by all three split outputs via shallow copy — confirmed from source analysis.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| torch_geometric | 2.7 (project-pinned) | HeteroData, RandomLinkSplit, coalesce | Official PyG — no alternative |
| torch | 2.6 (project-pinned) | Tensor ops, torch.save/load | No alternative |
| pandas | project env | Load parquets, build index dicts | Phase 2 output format |
| numpy | project env | Feature matrix ops, normalization | Standard numeric layer |
| rdkit | 2025.03 (project-pinned) | Deserialize Morgan fp bytes, BulkTanimotoSimilarity | Phase 2 stored fps as bytes |
| tqdm | project env | Progress bars on edge loops | Project-established pattern |
| json | stdlib | Write index_maps.json sidecar | No dep needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sklearn.preprocessing.StandardScaler | project env | Per-column z-score on RDKit descriptors before concat | Descriptors (MW, logP, TPSA etc.) have different scales — normalize before concat |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual HeteroData construction | from_networkx() | from_networkx() loses type control and forces homogeneous NetworkX graph first; manual construction is unambiguous and what GRAPH-01 requires |
| StandardScaler on descriptors | torch NormalizeFeatures transform | Sklearn scaler is fit on training data only (correct); PyG transform operates on full graph (leakage risk if used before split) |

**Installation:** All already installed per environment.yml.

---

## Architecture Patterns

### Recommended Project Structure
```
graph/
├── build_graph.py       # standalone script, also importable by run_pipeline.py
├── hetero_data.pt       # output: dict with graph + index maps (created by script)
├── index_maps.json      # output: human-readable sidecar (created by script)
└── .gitkeep             # already exists
```

### Pattern 1: Manual HeteroData Construction
**What:** Assign node feature tensors and edge_index tensors using string-keyed access. Node types use single-string keys; edge types use 3-tuple keys.
**When to use:** Always for GRAPH-01 — do not use from_networkx().

```python
# Source: https://pytorch-geometric.readthedocs.io/en/latest/notes/heterogeneous.html
from torch_geometric.data import HeteroData
import torch

data = HeteroData()

# Node features — shape [num_nodes, num_features]
data['ingredient'].x = ingredient_feat_tensor   # float32
data['molecule'].x = molecule_feat_tensor       # float32

# Optional: set num_nodes explicitly to catch isolated nodes
data['ingredient'].num_nodes = len(ingredient_id_to_idx)
data['molecule'].num_nodes = len(molecule_id_to_idx)

# Edge indices — shape [2, num_edges], dtype=torch.long
data['ingredient', 'contains', 'molecule'].edge_index = contains_edge_index
data['ingredient', 'co_occurs', 'ingredient'].edge_index = cooccurs_edge_index
data['molecule', 'structurally_similar', 'molecule'].edge_index = struct_edge_index

# Optional edge weights — shape [num_edges]
data['ingredient', 'contains', 'molecule'].edge_attr = contains_weights
data['ingredient', 'co_occurs', 'ingredient'].edge_attr = cooccurs_weights
```

### Pattern 2: Feature Vector Construction for Ingredient Nodes (GRAPH-02)
**What:** Concat multimodal features, mean-pooled Morgan fingerprints, and flavor multi-hot into a single float32 tensor. Normalize continuous features before concat.
**When to use:** Building `ingredient_feat_tensor`.

Key concern: Morgan fingerprints are stored as bytes in molecules.parquet (per Phase 2 decision). They must be deserialized via RDKit and then mean-pooled per ingredient (average across all molecules the ingredient contains).

```python
from rdkit.Chem import AllChem
from rdkit.DataStructs import ConvertToNumpyArray
import numpy as np
from sklearn.preprocessing import StandardScaler

# 1. Multimodal features (already float: texture 5-dim, temp 4-dim, cultural 10-dim)
#    These are already one-hot/multi-hot from Phase 2 — no scaling needed.
#    Shape per ingredient: 5 + 4 + 10 = 19 dims

# 2. Mean-pool Morgan fingerprints across ingredient's molecules
#    fp_bytes are stored in molecules.parquet as morgan_fp_bytes column
def deserialize_fp(fp_bytes):
    fp = AllChem.GetMorganFingerprintAsBitVect.__func__  # use from_bytes
    # RDKit stores ExplicitBitVect — deserialize with DataStructs
    from rdkit import DataStructs
    fp = DataStructs.ExplicitBitVect(1024)
    fp.FromBase64(fp_bytes)  # if stored as base64
    arr = np.zeros(1024, dtype=np.float32)
    ConvertToNumpyArray(fp, arr)
    return arr

# Build per-ingredient mean-pooled fp: shape [num_ingredients, 1024]
# Then concat: [multimodal (19), mean_fp (1024), flavor_multihot (vocab_size)]

# 3. Flavor multi-hot is already in ingredients.parquet
#    No scaling for binary vectors.

# Scaling: only apply StandardScaler to continuous features if any are present.
# For this project, multimodal features are already one-hot (already 0/1 range).
# Morgan mean-pool values are [0,1] floats. No additional scaling required.
# NOTE: If RDKit descriptor columns are included in ingredient features (they
#       are not per GRAPH-02 spec — those go to molecule nodes), StandardScaler
#       would be needed.
```

### Pattern 3: Feature Vector Construction for Molecule Nodes (GRAPH-03)
**What:** Concat RDKit descriptors (6 floats) + Morgan fingerprint (1024 bits). Scale descriptors before concat.
**When to use:** Building `molecule_feat_tensor`.

```python
from sklearn.preprocessing import StandardScaler

# molecules.parquet columns: pubchem_id, smiles, MW, logP, HBD, HBA,
#                             rotatable_bonds, TPSA, morgan_fp_bytes

descriptor_cols = ['MW', 'logP', 'HBD', 'HBA', 'rotatable_bonds', 'TPSA']
desc_matrix = mol_df[descriptor_cols].fillna(0.0).values  # [N, 6]

# Fit scaler on all molecules (no train/test split at feature level — features
# are structural properties, not supervision labels)
scaler = StandardScaler()
desc_scaled = scaler.fit_transform(desc_matrix).astype(np.float32)  # [N, 6]

# Deserialize Morgan fps: [N, 1024]
fp_matrix = np.stack([deserialize_fp(b) for b in mol_df['morgan_fp_bytes']])

# Concat: [N, 6 + 1024] = [N, 1030]
molecule_feat = np.concatenate([desc_scaled, fp_matrix], axis=1)
molecule_feat_tensor = torch.tensor(molecule_feat, dtype=torch.float32)
```

**Null handling:** Molecules with null descriptors (sanitization failures from Phase 2) should have their null cols filled with 0 (column mean post-scaling becomes 0 — correct behavior for StandardScaler on mean-filled data).

### Pattern 4: Edge Construction — Contains (GRAPH-04)
**What:** Build ingredient→molecule edge_index from ingredient-molecule membership data (molecules_json in ingredients.csv, or equivalently from Phase 2's ingredients.parquet).
**When to use:** Building contains edges.

```python
src_indices = []  # ingredient idx
dst_indices = []  # molecule idx
weights = []

for ing_idx, row in enumerate(ingredients_df.itertuples()):
    ing_id = row.ingredient_id
    for mol_pubchem_id in ingredient_molecule_lookup[ing_id]:
        if mol_pubchem_id not in molecule_id_to_idx:
            continue
        mol_idx = molecule_id_to_idx[mol_pubchem_id]
        src_indices.append(ingredient_id_to_idx[ing_id])
        dst_indices.append(mol_idx)
        # FooDB concentration if available, else 1.0
        conc = foodb_concentration_lookup.get((ing_id, mol_pubchem_id), 1.0)
        weights.append(float(conc))

contains_edge_index = torch.tensor([src_indices, dst_indices], dtype=torch.long)
contains_weights = torch.tensor(weights, dtype=torch.float32)
```

### Pattern 5: Edge Construction — Co-occurs (GRAPH-05)
**What:** Build ingredient→ingredient edge_index from cooccurrence.parquet. Normalize weights.
**When to use:** Building co-occurs edges (the link prediction target).

```python
# cooccurrence.parquet: ingredient_a (name), ingredient_b (name), count
# Need to map ingredient names to ingredient_id_to_idx

cooc_df = pd.read_parquet("data/processed/cooccurrence.parquet")
max_count = cooc_df['count'].max()

src_indices, dst_indices, weights = [], [], []
for row in cooc_df.itertuples():
    a_idx = name_to_ingredient_idx.get(row.ingredient_a)
    b_idx = name_to_ingredient_idx.get(row.ingredient_b)
    if a_idx is None or b_idx is None:
        continue
    src_indices.append(a_idx)
    dst_indices.append(b_idx)
    weights.append(row.count / max_count)

cooccurs_edge_index = torch.tensor([src_indices, dst_indices], dtype=torch.long)
cooccurs_weights = torch.tensor(weights, dtype=torch.float32)
```

**Note on directionality:** Co-occurrence is symmetric. RandomLinkSplit with `is_undirected=True` will handle reverse edges automatically. See RandomLinkSplit section.

### Pattern 6: RandomLinkSplit — Splitting Co-occurs Only (GRAPH-08)
**What:** Split only the co-occurs edge type; leave contains and structurally_similar edges untouched in all three split outputs.

This is the most technically complex step. Key findings from source analysis:

**Verified behavior (MEDIUM-HIGH confidence, from PyG source and discussion analysis):**
- `RandomLinkSplit` accepts `edge_types` as a list of 3-tuples specifying which edges to split.
- Edge types NOT listed in `edge_types` are inherited unchanged in all three output objects via `copy.copy(data)` — they are NOT dropped or modified.
- `rev_edge_types` must be a list of equal length to `edge_types`. For a directed edge type with no reverse in the graph, pass `None` as its rev_edge_type entry.
- For a symmetric co-occurrence edge with `is_undirected=True`, set `rev_edge_types=[('ingredient', 'co_occurs', 'ingredient')]` (same type).

**Correct configuration for this project:**
```python
# Source: PyG docs + source analysis
from torch_geometric.transforms import RandomLinkSplit

transform = RandomLinkSplit(
    num_val=0.15,
    num_test=0.15,
    is_undirected=True,          # co-occurs is symmetric
    neg_sampling_ratio=1.0,      # 1 negative per positive
    add_negative_train_samples=True,
    edge_types=[('ingredient', 'co_occurs', 'ingredient')],
    rev_edge_types=[('ingredient', 'co_occurs', 'ingredient')],  # same type (undirected homo)
)

train_data, val_data, test_data = transform(data)
# train_data['ingredient','co_occurs','ingredient'].edge_index  — message passing edges
# train_data['ingredient','co_occurs','ingredient'].edge_label_index  — supervision labels
# val_data['ingredient','co_occurs','ingredient'].edge_label_index    — val labels
# test_data['ingredient','co_occurs','ingredient'].edge_label_index   — test labels

# contains and structurally_similar are unchanged in all three outputs
```

**What the transform produces per split:**
- `train_data`: `edge_index` = training co-occurs edges (used in message passing); `edge_label_index` + `edge_label` = positive + negative supervision pairs
- `val_data`: `edge_index` = same training edges (val nodes see training graph); `edge_label_index` = val positive + negative pairs
- `test_data`: `edge_index` = same training edges; `edge_label_index` = test positive + negative pairs

**disjoint_train_ratio:** Leave at default (0.0). This would further split training edges into message-passing vs. supervision subsets. For this project, all training edges participate in message passing AND provide supervision — the standard approach. Only set `disjoint_train_ratio > 0` for full inductive link prediction (not needed here).

### Pattern 7: Leakage Assertion (GRAPH-08)
**What:** Assert zero overlap between test supervision edge endpoints and message-passing edge_index before saving.

```python
# After RandomLinkSplit:
# test_edge_label_index: shape [2, num_test_edges*2] (pos + neg)
# train edge_index: shape [2, num_train_edges]

train_ei = train_data['ingredient', 'co_occurs', 'ingredient'].edge_index
test_eli = test_data['ingredient', 'co_occurs', 'ingredient'].edge_label_index

# Build set of (src, dst) tuples from message-passing graph
train_set = set(zip(train_ei[0].tolist(), train_ei[1].tolist()))

# Check test supervision edges — only check POSITIVE test edges (edge_label == 1)
test_labels = test_data['ingredient', 'co_occurs', 'ingredient'].edge_label
positive_mask = (test_labels == 1)
test_pos_ei = test_eli[:, positive_mask]

leakage_count = sum(
    1 for s, d in zip(test_pos_ei[0].tolist(), test_pos_ei[1].tolist())
    if (s, d) in train_set or (d, s) in train_set  # check both directions
)

assert leakage_count == 0, (
    f"DATA LEAKAGE DETECTED: {leakage_count} test edges appear in message-passing "
    f"edge_index. Graph not saved. Check RandomLinkSplit configuration."
)
```

**Note:** RandomLinkSplit should prevent this automatically when configured correctly, but the assertion is the explicit portfolio-quality guard that CONTEXT.md requires.

### Pattern 8: Validation Gate (GRAPH-07)
**What:** Check node/edge thresholds before the split step; raise ValueError with formatted diagnostics.

```python
def run_validation_gate(data: HeteroData) -> None:
    checks = []
    passed = True

    n_ing = data['ingredient'].num_nodes
    n_mol = data['molecule'].num_nodes

    def check(label, actual, threshold, comparator='>='):
        ok = actual >= threshold
        symbol = '✓' if ok else '✗'
        if ok:
            checks.append(f"  {symbol} {label}: {actual:,} found (>={threshold:,})")
        else:
            checks.append(f"  {symbol} {label}: {actual:,} found, {threshold:,} required")
        return ok

    passed &= check("Ingredient nodes", n_ing, 500)
    passed &= check("Molecule nodes", n_mol, 2000)

    required_edge_types = [
        ('ingredient', 'contains', 'molecule'),
        ('ingredient', 'co_occurs', 'ingredient'),
        ('molecule', 'structurally_similar', 'molecule'),
    ]
    for et in required_edge_types:
        present = et in data.edge_types
        symbol = '✓' if present else '✗'
        label = f"Edge type {et[1]!r}"
        if present:
            checks.append(f"  {symbol} {label}: present ({data[et].num_edges:,} edges)")
        else:
            checks.append(f"  {symbol} {label}: MISSING")
        passed &= present

    print("\n=== Graph Validation Gate ===")
    for line in checks:
        print(line)

    if not passed:
        print("\nRemediation: Run Phase 2 feature engineering and verify data/processed/ parquet files exist")
        raise ValueError("Graph validation gate failed — see diagnostics above. Graph not saved.")

    print("  All checks passed.")
    print("=============================\n")
```

### Pattern 9: Saving and Loading the .pt Dict (GRAPH-09)
**What:** Save HeteroData + index maps as a single dict for atomic loading.

```python
# SAVE
import json, torch

payload = {
    "graph": train_data,          # HeteroData after split — includes train edge_index
    "val_data": val_data,          # for Phase 4 AUC evaluation
    "test_data": test_data,        # for Phase 4 AUC evaluation
    "ingredient_id_to_idx": ingredient_id_to_idx,   # {int -> int}
    "molecule_id_to_idx": molecule_id_to_idx,        # {int -> int}
}
torch.save(payload, "graph/hetero_data.pt")

# JSON sidecar (ints as keys must be converted to strings for JSON)
json_maps = {
    "ingredient_id_to_idx": {str(k): v for k, v in ingredient_id_to_idx.items()},
    "molecule_id_to_idx": {str(k): v for k, v in molecule_id_to_idx.items()},
}
with open("graph/index_maps.json", "w") as f:
    json.dump(json_maps, f, indent=2)

# LOAD (Phase 4+)
payload = torch.load("graph/hetero_data.pt", weights_only=False)
train_data = payload["graph"]
val_data = payload["val_data"]
test_data = payload["test_data"]
ingredient_id_to_idx = payload["ingredient_id_to_idx"]
molecule_id_to_idx = payload["molecule_id_to_idx"]
```

**Important:** `torch.load` with `weights_only=True` (default in PyTorch 2.6) will FAIL for HeteroData objects because they contain non-tensor Python objects. Must use `weights_only=False`. This is safe for locally-generated files.

### Anti-Patterns to Avoid
- **Using `from_networkx()`:** Loses heterogeneous type structure; GRAPH-01 explicitly prohibits it.
- **Saving graph before leakage assertion:** The assertion must gate the save — never write a potentially-leaked graph.
- **Setting `is_undirected=False` for co-occurs edges:** Co-occurrence is symmetric; `is_undirected=True` ensures reverse direction is not leaked.
- **Running StandardScaler on all molecules including test split:** In this phase, molecules are nodes (not split) so fitting on all is correct. Only edge labels have a train/test distinction.
- **Storing 1024-column Morgan fingerprints in parquet:** Phase 2 already stored them as bytes — deserialize in Phase 3. Do not re-flatten.
- **Forgetting `weights_only=False` in torch.load:** Will crash silently or with cryptic error in PyTorch 2.6.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Link prediction train/val/test split | Custom edge mask logic | `RandomLinkSplit` from PyG | Handles negative sampling, reverse edge removal, edge_label_index generation — many subtle correctness requirements |
| Pairwise Tanimoto on 2000+ molecules | Nested Python loop | `DataStructs.BulkTanimotoSimilarity()` | BulkTanimotoSimilarity crosses Python-C++ boundary once per query; nested Python loop is ~100x slower |
| Feature normalization | Custom z-score | `sklearn.preprocessing.StandardScaler` | Handles NaN-fill, per-column scaling, fit/transform separation correctly |
| Edge deduplication | Manual set operations | `torch_geometric.utils.coalesce()` | Handles duplicates with reduce options; sorts edge_index for efficient access |
| Graph correctness check | Manual assertions scattered throughout | `data.validate()` | Checks edge_index bounds vs num_nodes, dtypes, etc. — run before validation gate |

**Key insight:** RandomLinkSplit's negative sampling and reverse-edge removal are non-trivial to reimplement correctly. The `rev_edge_types` parameter is required for undirected co-occurrence — omitting it causes test edge reverse directions to leak into training edge_index.

---

## Common Pitfalls

### Pitfall 1: RandomLinkSplit Requires edge_types for HeteroData
**What goes wrong:** Calling `RandomLinkSplit(num_val=0.15, num_test=0.15)(data)` on a HeteroData without specifying `edge_types` raises `ValueError: 'RandomLinkSplit' expects 'edge_types' when operating on 'HeteroData' objects`.
**Why it happens:** The transform cannot infer which of the three edge types to split.
**How to avoid:** Always specify `edge_types=[('ingredient', 'co_occurs', 'ingredient')]` explicitly.
**Warning signs:** `ValueError` at transform call time.

### Pitfall 2: rev_edge_types Length Must Match edge_types Length
**What goes wrong:** Passing `rev_edge_types=None` when `edge_types` is a list raises an error or silently skips reverse-direction leakage prevention.
**Why it happens:** The transform expects a list of equal length — one rev_edge_type per edge_type.
**How to avoid:** Always pass `rev_edge_types=[('ingredient', 'co_occurs', 'ingredient')]` (same type for undirected homo-type edges), or `rev_edge_types=[None]` for directed edges with no explicit reverse.
**Warning signs:** Leakage assertion fires; or `AssertionError`/`AttributeError` at transform time.

### Pitfall 3: Morgan Fingerprint Deserialization from Bytes
**What goes wrong:** Trying to directly pass morgan_fp_bytes (stored as Python bytes in parquet) to numpy or torch without deserializing through RDKit first.
**Why it happens:** Phase 2 stored fingerprints as RDKit-serialized bytes, not raw numpy arrays.
**How to avoid:** Use `DataStructs.ExplicitBitVect` deserialization before converting to numpy array. Confirm storage format at the start of Phase 3 by printing `type(mol_df['morgan_fp_bytes'].iloc[0])`.
**Warning signs:** `TypeError: a bytes-like object is required` or garbage float values.

### Pitfall 4: Isolated Nodes When co-occurrence Name Lookup Fails
**What goes wrong:** Ingredients in ingredients.parquet may have names that don't match names in cooccurrence.parquet (e.g., case differences, trailing whitespace). Those ingredients get zero co-occurs edges.
**Why it happens:** Phase 1 may produce slightly different string representations across files.
**How to avoid:** Normalize ingredient names (lowercase, strip) in both lookup dicts. Log how many ingredients have zero co-occurs edges — this is expected for rare ingredients but should not be the majority.
**Warning signs:** Extremely low co-occurs edge count relative to expected (~thousands of edges).

### Pitfall 5: torch.load weights_only=True Crashes on HeteroData
**What goes wrong:** PyTorch 2.6 defaults `weights_only=True` in `torch.load`, which refuses to unpickle non-tensor Python objects (dicts, HeteroData internal storage).
**Why it happens:** PyTorch security hardening since 2.4.
**How to avoid:** Always call `torch.load("graph/hetero_data.pt", weights_only=False)` in downstream phases. Document this in the loading code comment.
**Warning signs:** `UnpicklingError` or `AttributeError` at load time.

### Pitfall 6: Tanimoto Memory — Full All-Pairs Matrix
**What goes wrong:** Computing a full [2000 × 2000] float64 numpy matrix all at once allocates 32MB — manageable. But if molecules grow to 5000+, it becomes 200MB+. More importantly, storing ALL similarities before threshold filtering wastes memory.
**Why it happens:** Naive numpy pairwise approach allocates full matrix.
**How to avoid:** Use RDKit's `BulkTanimotoSimilarity` in a row-at-a-time loop, filter threshold inline, accumulate only (src, dst) pairs that exceed 0.7. For ~2000 molecules this is fast enough without batching.
**Warning signs:** MemoryError or OOM on M2/8GB during Tanimoto step.

---

## Code Examples

### Tanimoto-to-Edge Construction (for GRAPH-06)

```python
# Source: RDKit DataStructs docs + verified pattern
from rdkit import DataStructs
from tqdm import tqdm

# fps_list: list of ExplicitBitVect objects, one per molecule, aligned to mol_df index
# mol_idx_list: corresponding molecule indices (0..N-1)
# threshold: 0.7

src_indices, dst_indices, sim_values = [], [], []

for i in tqdm(range(len(fps_list)), desc="Tanimoto edges"):
    if fps_list[i] is None:
        continue  # skip molecules with no SMILES / failed fingerprint
    # BulkTanimotoSimilarity: compare fps_list[i] against all molecules with lower index
    # Only compute lower triangle to avoid duplicate edges
    sims = DataStructs.BulkTanimotoSimilarity(fps_list[i], fps_list[:i])
    for j, sim in enumerate(sims):
        if sim > 0.7:
            src_indices.append(mol_idx_list[i])
            dst_indices.append(mol_idx_list[j])
            sim_values.append(float(sim))

# struct_edge_index is directed; make undirected by adding reverse edges
if src_indices:
    fwd = torch.tensor([src_indices, dst_indices], dtype=torch.long)
    rev = torch.tensor([dst_indices, src_indices], dtype=torch.long)
    struct_edge_index = torch.cat([fwd, rev], dim=1)
    struct_weights = torch.tensor(sim_values + sim_values, dtype=torch.float32)
else:
    struct_edge_index = torch.zeros((2, 0), dtype=torch.long)
    struct_weights = torch.zeros(0, dtype=torch.float32)
```

**Complexity:** O(N^2/2) similarity computations. For N=2000: 2M calls, each in C++ — completes in seconds on M2. For N=5000: ~12M calls — still fast but tqdm helps track progress.

### HeteroData validate() Usage

```python
# Run before the validation gate to catch structural errors early
try:
    data.validate(raise_on_error=True)
except Exception as e:
    logger.error("HeteroData structural validation failed: %s", e)
    raise
```

### Summary Table (matching Phase 1 pattern)

```python
def _print_graph_summary(train_data, val_data, test_data, ingredient_id_to_idx, molecule_id_to_idx):
    print()
    print("=== Phase 3 Graph Construction Summary ===")
    print(f"Ingredient nodes:   {len(ingredient_id_to_idx):>8,}")
    print(f"Molecule nodes:     {len(molecule_id_to_idx):>8,}")
    print(f"Contains edges:     {train_data['ingredient','contains','molecule'].num_edges:>8,}")
    print(f"Co-occurs edges:    {train_data['ingredient','co_occurs','ingredient'].num_edges:>8,}  (train message-passing)")
    print(f"Structural edges:   {train_data['molecule','structurally_similar','molecule'].num_edges:>8,}")
    print(f"Link pred split:    train={train_data['ingredient','co_occurs','ingredient'].edge_label_index.size(1)}")
    print(f"                    val  ={val_data['ingredient','co_occurs','ingredient'].edge_label_index.size(1)}")
    print(f"                    test ={test_data['ingredient','co_occurs','ingredient'].edge_label_index.size(1)}")
    print(f"Output:             graph/hetero_data.pt")
    print(f"                    graph/index_maps.json")
    print("==========================================")
    print()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `from_networkx()` for HeteroData | Manual dict-style assignment | PyG 1.7+ | Manual construction is unambiguous, required by spec |
| Separate .pkl for index maps | Embedded in .pt dict + JSON sidecar | PyG 2.x community pattern | Atomic load, no sync risk |
| `weights_only=True` default | Must use `weights_only=False` for non-tensor objects | PyTorch 2.4+ | Breaks naive torch.load of HeteroData |
| disjoint supervision edges (disjoint_train_ratio>0) | All-training-edges participate in message passing | PyG 2.0+ | Standard for transductive link prediction |

**Deprecated/outdated:**
- `torch.load(path)` without `weights_only=False`: Emits FutureWarning in 2.5, raises error in 2.6+ for non-tensor objects.
- `neg_sampling_ratio=0.0` + manual negative sampling: RandomLinkSplit handles this automatically.

---

## Open Questions

1. **Morgan fingerprint serialization format from Phase 2**
   - What we know: Phase 2 CONTEXT.md specifies `morgan_fp_bytes` column with "serialized bytes"
   - What's unclear: Exact bytes format (RDKit `ToBitString()`, `ToBase64()`, raw `__getstate__`, or `numpy_fp.tobytes()`)
   - Recommendation: At start of build_graph.py, probe `mol_df['morgan_fp_bytes'].iloc[0]` type and length; add a one-line comment to the deserialization code documenting the format once confirmed. Plan should include a defensive probe step.

2. **cooccurrence.parquet ingredient name format vs ingredients.parquet ingredient_id**
   - What we know: Phase 2 will forward cooccurrence.parquet from Phase 1 recipes.csv; Phase 1 used ingredient names, not IDs
   - What's unclear: Whether Phase 2 adds ingredient_id column to cooccurrence.parquet or keeps name-based join
   - Recommendation: Plan should include a name-normalization step (lowercase, strip) and log the match rate. If > 20% fail to match, raise a warning (not a hard stop).

3. **Whether to include val_data and test_data in hetero_data.pt**
   - What we know: CONTEXT.md specifies saving train_data as "graph" key; val/test needed for Phase 4 AUC
   - What's unclear: Whether Phase 4 expects val_data/test_data embedded in same .pt file or separate
   - Recommendation: Include all three in the .pt dict (train_data under "graph", val_data and test_data under their own keys). This matches the "atomic load" principle from CONTEXT.md decisions.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed in project env, used in Phase 1) |
| Config file | none — run from project root |
| Quick run command | `pytest tests/test_graph.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GRAPH-01 | HeteroData loads, has ingredient and molecule node types | smoke | `pytest tests/test_graph.py::test_graph_loads -x` | Wave 0 |
| GRAPH-02 | ingredient.x shape is [N, expected_dim] and is float32 | unit | `pytest tests/test_graph.py::test_ingredient_features -x` | Wave 0 |
| GRAPH-03 | molecule.x shape is [M, 1030] and is float32 | unit | `pytest tests/test_graph.py::test_molecule_features -x` | Wave 0 |
| GRAPH-04 | contains edge_index has valid bounds; weights all > 0 | unit | `pytest tests/test_graph.py::test_contains_edges -x` | Wave 0 |
| GRAPH-05 | co_occurs edge_index has valid bounds; weights in [0,1] | unit | `pytest tests/test_graph.py::test_cooccurs_edges -x` | Wave 0 |
| GRAPH-06 | structurally_similar edge_index present; all weights > 0.7 | unit | `pytest tests/test_graph.py::test_structural_edges -x` | Wave 0 |
| GRAPH-07 | Validation gate raises ValueError when node count < threshold | unit | `pytest tests/test_graph.py::test_validation_gate -x` | Wave 0 |
| GRAPH-08 | Zero overlap between test edge_label_index and train edge_index | integration | `pytest tests/test_graph.py::test_no_leakage -x` | Wave 0 |
| GRAPH-09 | hetero_data.pt loads; contains graph, ingredient_id_to_idx, molecule_id_to_idx keys | smoke | `pytest tests/test_graph.py::test_saved_artifact -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_graph.py -x -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_graph.py` — covers all GRAPH-01 through GRAPH-09 (does not exist yet)

*(All other test infrastructure exists — pytest installed, tests/__init__.py present, conftest.py not needed for these tests)*

---

## Sources

### Primary (HIGH confidence)
- [PyG HeteroData official docs](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.data.HeteroData.html) — node/edge access API, validate(), node_types, edge_types
- [PyG Heterogeneous Graph Learning guide](https://pytorch-geometric.readthedocs.io/en/latest/notes/heterogeneous.html) — manual HeteroData construction patterns, HeteroConv
- [PyG RandomLinkSplit official docs](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.transforms.RandomLinkSplit.html) — full API signature, all parameters with defaults
- [PyG RandomLinkSplit source](https://pytorch-geometric.readthedocs.io/en/latest/_modules/torch_geometric/transforms/random_link_split.html) — edge_types behavior, copy.copy semantics for unlisted edge types

### Secondary (MEDIUM confidence)
- [PyG Discussion #4453: RandomLinkSplit in custom HeteroData](https://github.com/pyg-team/pytorch_geometric/discussions/4453) — confirmed edge_types parameter usage; revealed tensor dimensionality requirement
- [PyG Issue #5206: RandomLinkSplit in HeteroData](https://github.com/pyg-team/pytorch_geometric/issues/5206) — confirmed is_undirected behavior; gotcha on rev_edge_types for same-type undirected edges (fixed in PyG 2.1)
- [RDKit DataStructs BulkTanimotoSimilarity docs](https://www.rdkit.org/docs/source/rdkit.DataStructs.cDataStructs.html) — BulkTanimotoSimilarity signature and performance characteristics
- [WebSearch: PyG edge_types only split one type 2024](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.transforms.RandomLinkSplit.html) — cross-verified: only listed edge_types are split; others unchanged

### Tertiary (LOW confidence — flag for validation)
- Phase 2 Morgan fingerprint byte format: inferred from CONTEXT.md "serialized bytes" — exact format must be probed at runtime

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are project-pinned and well-documented
- HeteroData construction API: HIGH — verified against official PyG docs
- RandomLinkSplit edge_types behavior: MEDIUM-HIGH — source analysis confirms unlisted edges unchanged via copy.copy; rev_edge_types behavior confirmed from docs + issues
- Tanimoto-to-edge construction: HIGH — RDKit BulkTanimotoSimilarity is stable, well-documented
- Feature vector concatenation: HIGH — numpy/sklearn patterns, verified
- Morgan fp deserialization format: LOW — depends on Phase 2 implementation detail not yet written
- torch.load weights_only=False requirement: HIGH — PyTorch 2.6 breaking change confirmed

**Research date:** 2026-03-11
**Valid until:** 2026-06-11 (PyG 2.7 is stable; PyTorch 2.6 API is stable; no active breaking changes expected within 90 days)
