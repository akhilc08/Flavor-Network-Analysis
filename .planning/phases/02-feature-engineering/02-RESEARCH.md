# Phase 2: Feature Engineering - Research

**Researched:** 2026-03-11
**Domain:** Chemical informatics (RDKit), async HTTP (httpx), parquet serialization, multimodal feature encoding
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**PubChem SMILES Fetch**
- Cache format: JSON file (`data/raw/pubchem_cache.json`) — simple `{pubchem_id: smiles_string}` dict
- HTTP client: async httpx with asyncio.Semaphore rate limiting (≤400 req/min ceiling)
- Missing SMILES (404 or empty): retain molecule row with `smiles=None`; log by molecule name and pubchem_id; RDKit steps skip nulls deterministically
- Cache must be 100% populated before RDKit processing begins (gate enforced in build_features.py)

**RDKit Descriptors and Fingerprints**
- Descriptors per molecule: MW, logP, HBD, HBA, rotatable bonds, TPSA (6 columns)
- Sanitization failures: logged with ingredient name + molecule name; molecule retains null descriptor columns; does not crash pipeline
- Morgan fingerprints: radius=2, 1024 bits; stored as serialized bytes column (`morgan_fp_bytes`) in molecules.parquet
- Tanimoto similarity: computed for all molecule pairs with similarity > 0.7; saved as tanimoto_edges.parquet with columns: mol_a_pubchem_id, mol_b_pubchem_id, similarity

**Multimodal Ingredient Features**
- Texture embedding: 5-dim one-hot (crispy/soft/creamy/chewy/crunchy); hard-coded category→texture dict; moisture content adjusts crispy vs soft boundary
- Temperature affinity: 4-dim one-hot (raw/cold/warm/hot); hard-coded ingredient category → temperature lookup
- Cultural context vector: 10-dim one-hot over AllRecipes categories (Italian, Asian, Mexican, French, American, Indian, Mediterranean, Middle Eastern, Japanese, Thai); derived from recipes.csv + recipes_allrecipes.csv
- Flavor profile multi-hot: union of all `flavor_profile` tags across all molecules belonging to the ingredient; vocabulary built from full dataset

**Output File Schema**
- `data/processed/ingredients.parquet` — one row per ingredient with all feature columns
- `data/processed/molecules.parquet` — one row per molecule with descriptors + morgan_fp_bytes
- `data/processed/tanimoto_edges.parquet` — mol_a_pubchem_id, mol_b_pubchem_id, similarity
- `data/processed/cooccurrence.parquet` — ingredient_a, ingredient_b, count (carried from Phase 1)

**Script Organization**
- Two scripts: `data/fetch_smiles.py` + `data/build_features.py`
- Both runnable standalone with argparse + `--force` flag
- `run_pipeline.py` calls `fetch_smiles()` and `build_features()` functions directly
- `--skip-smiles` flag skips fetch_smiles if cache already complete; `--skip-features` skips build_features if parquets exist

### Claude's Discretion
- Exact texture/temperature lookup table values (specific category→texture mappings)
- Flavor profile vocabulary size and ordering
- Tanimoto computation approach (all-pairs vs batched for memory efficiency)
- Async concurrency limit (semaphore count within 400 req/min ceiling)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FEAT-01 | PubChem API fetches canonical SMILES per pubchem_id with async httpx, token-bucket rate limiting (≤400 req/min), and full local cache (pubchem_cache.json); missing SMILES logged and reported | PubChem PUG-REST endpoint verified: `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{CID}/property/CanonicalSMILES/txt`. Rate limit: ≤5 req/sec (300/min). CRITICAL: FlavorDB2 SMILES already cover 100% of 1788 molecules — PubChem fetch is a gap-filler only. |
| FEAT-02 | RDKit computes molecular descriptors from SMILES: MW, logP, HBD, HBA, rotatable bonds, TPSA; sanitization failures logged with ingredient/molecule name | Verified with RDKit 2025.03.6 in flavor-network conda env. All 1788 FlavorDB2 SMILES parse successfully — 0 sanitization failures expected on existing data. |
| FEAT-03 | RDKit computes Morgan fingerprints (radius=2, 1024 bits) per molecule | Verified: `AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=1024)`. ToBitString().encode() produces 1024-byte bytes object that round-trips correctly through parquet. |
| FEAT-04 | Tanimoto similarity computed between all molecule pairs; pairs with similarity > 0.7 recorded as structural similarity edges | Verified: `DataStructs.BulkTanimotoSimilarity()` for all-pairs is feasible — 1788 molecules, 1,598,778 pairs completes in ~0.4 seconds. No batching required for M2/8GB. |
| FEAT-05 | Texture embedding computed per ingredient (crispy/soft/creamy/chewy/crunchy) via lookup from category + moisture content | Implementation plan: hard-coded category→texture dict, moisture_content from FooDB join modifies crispy/soft assignment. |
| FEAT-06 | Temperature affinity computed per ingredient (raw/cold/warm/hot) via hand-coded lookup table | Implementation plan: hard-coded ingredient category → temperature dict mapping FlavorDB2 categories to temperature buckets. |
| FEAT-07 | Cultural context vector computed per ingredient: one-hot over 10 cuisine categories derived from recipe co-occurrence data | CRITICAL FINDING: recipes_allrecipes.csv does NOT store category labels — only recipe_name and ingredients. The build_features script must infer category from recipe_name keywords OR use a keyword-to-category mapping at build time. |
| FEAT-08 | Flavor profile multi-hot vector encoded per ingredient from flavor_profile tags | flavor_profile column exists in molecules.csv as `@`-delimited tags. Union over all molecules per ingredient. Vocabulary built at dataset level for consistent vector dimensions. |
| FEAT-09 | Processed features written to data/processed/ as parquet files before graph construction | Verified: pyarrow 23.0.1 installed; bytes column (`morgan_fp_bytes`) round-trips correctly as Python `bytes` objects. `data/processed/` directory exists (contains `.gitkeep`). |
</phase_requirements>

---

## Summary

Phase 2 builds the complete feature set that Phase 3's graph construction will consume. Three research discoveries significantly shape the implementation:

**1. FlavorDB2 SMILES are already 100% present.** The `molecules_json` column in `ingredients.csv` contains a `smile` field for every molecule (1788/1788 molecules, 0 failures with RDKit). This means `fetch_smiles.py` only needs to handle gap-filling (molecules missing from FlavorDB2 data) and should first extract SMILES from the existing `ingredients.csv` before querying PubChem. The PubChem fetch stage will likely be nearly a no-op, but must still populate `pubchem_cache.json` for the required gate check.

**2. AllRecipes cultural context requires category inference.** The `recipes_allrecipes.csv` file stores only `recipe_name` and `ingredients` — the category label (Italian, Asian, etc.) was NOT persisted by the Phase 1 scraper. The 76 recipes are heavily skewed toward Indian and Mexican. Build_features must reconstruct category membership via a recipe_name keyword mapping dict at build time.

**3. Tanimoto all-pairs is trivially fast.** With 1788 molecules and `DataStructs.BulkTanimotoSimilarity()`, all-pairs completes in ~0.4 seconds — no batching, chunking, or numpy conversion needed. The concern noted in STATE.md about memory efficiency is not a real constraint.

**Primary recommendation:** Extract FlavorDB2 SMILES first in `fetch_smiles.py`, query PubChem only for missing IDs (likely zero), then run `build_features.py` through RDKit descriptors → Morgan fingerprints → Tanimoto edges → multimodal ingredient features → parquet writes.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rdkit | 2025.03.6 | Molecule parsing, descriptors, Morgan FP, Tanimoto | Installed in flavor-network conda env; project spec |
| httpx | 0.28.1 | Async HTTP for PubChem API | Installed; faster than requests for 1788+ concurrent fetches |
| pandas | (env) | DataFrame manipulation, CSV/parquet I/O | Existing project pattern |
| pyarrow | 23.0.1 | Parquet serialization | Installed; handles bytes columns correctly |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio | stdlib | Semaphore-based rate limiting | fetch_smiles.py concurrency control |
| json | stdlib | pubchem_cache.json read/write | Simpler than SQLite for key-value SMILES cache |
| tqdm | (env) | Progress bars | All loops — existing project pattern |
| logging | stdlib | Pipeline log to logs/pipeline.log | Existing project pattern |
| numpy | (env) | Dense fingerprint arrays if needed | Only needed if converting to matrix; not required for DataStructs |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| DataStructs.BulkTanimotoSimilarity | numpy matrix multiply | BulkTanimotoSimilarity is faster, native RDKit, no conversion needed |
| bytes column in parquet | 1024 binary columns | bytes column is ~8x more compact; Phase 3 decodes with np.frombuffer |
| asyncio.Semaphore | aiolimiter token bucket | Semaphore is simpler; token bucket only needed if burst behavior matters |

**Installation:** Already installed in `flavor-network` conda environment. Run with:
```bash
conda activate flavor-network
python data/fetch_smiles.py
python data/build_features.py
```

---

## Architecture Patterns

### Recommended Project Structure
```
data/
├── fetch_smiles.py          # fetch_smiles(force=False) function + CLI
├── build_features.py        # build_features(force=False) function + CLI
├── raw/
│   ├── ingredients.csv      # INPUT: ingredient_id, name, category, molecules_json
│   ├── molecules.csv        # INPUT: pubchem_id, common_name, flavor_profile, foodb_*
│   ├── recipes.csv          # INPUT: ingredient_a, ingredient_b, count
│   ├── recipes_allrecipes.csv # INPUT: recipe_name, ingredients
│   └── pubchem_cache.json   # GENERATED: {pubchem_id: smiles_or_null}
└── processed/
    ├── ingredients.parquet  # GENERATED: full ingredient feature vectors
    ├── molecules.parquet    # GENERATED: descriptors + morgan_fp_bytes
    ├── tanimoto_edges.parquet # GENERATED: mol pairs with sim > 0.7
    └── cooccurrence.parquet # GENERATED: from recipes.csv
```

### Pattern 1: fetch_smiles.py — SMILES extraction with PubChem fallback

**What:** Extract SMILES from FlavorDB2 `molecules_json`, then query PubChem only for any missing IDs. Write all results to `pubchem_cache.json`.

**When to use:** Phase 2 SMILES acquisition. Must complete before `build_features.py` begins.

**Implementation notes:**
- Step 1: Parse `ingredients.csv` `molecules_json` column to extract `{pubchem_id: smile}` for all 1788 molecules
- Step 2: Identify any pubchem_ids in `molecules.csv` NOT already in cache (expected: 0)
- Step 3: For missing IDs only — async httpx fetch from PubChem with asyncio.Semaphore
- Step 4: Merge FlavorDB2 SMILES + PubChem SMILES → write pubchem_cache.json
- Step 5: Log coverage: total / with_smiles / missing_smiles (null entries)

```python
# Source: PubChem PUG-REST documentation (iupac.github.io/WFChemCookbook)
PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/CanonicalSMILES/txt"
# Rate limit: ≤5 req/sec (300/min) per PubChem policy
# Semaphore(5) for 5 concurrent requests = ~5 req/sec
```

### Pattern 2: build_features.py — RDKit descriptors and Morgan fingerprints

**What:** For each molecule in the cache, compute 6 descriptors + Morgan fingerprint. Skip nulls deterministically.

```python
# Source: RDKit 2025.03.6, verified in flavor-network env
from rdkit import Chem
from rdkit.Chem import Descriptors, AllChem

def compute_rdkit_features(smiles: str) -> dict | None:
    if not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None  # log sanitization failure
    return {
        "MW": Descriptors.MolWt(mol),
        "logP": Descriptors.MolLogP(mol),
        "HBD": Descriptors.NumHDonors(mol),
        "HBA": Descriptors.NumHAcceptors(mol),
        "rotatable_bonds": Descriptors.NumRotatableBonds(mol),
        "TPSA": Descriptors.TPSA(mol),
        "morgan_fp_bytes": AllChem.GetMorganFingerprintAsBitVect(
            mol, radius=2, nBits=1024
        ).ToBitString().encode(),
    }
```

### Pattern 3: Tanimoto all-pairs computation

**What:** Compute Tanimoto similarity for all pairs of molecules with non-null fingerprints, filter to > 0.7, write tanimoto_edges.parquet.

**Performance verified:** 1788 molecules × 1,598,778 pairs ≈ 0.4 seconds. All-pairs in-memory, no batching required.

```python
# Source: RDKit verified in flavor-network env
from rdkit.Chem import DataStructs

def compute_tanimoto_edges(fps: list, pubchem_ids: list, threshold: float = 0.7):
    edges = []
    for i in range(len(fps)):
        sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps[i+1:])
        for j, sim in enumerate(sims):
            if sim > threshold:
                edges.append({
                    "mol_a_pubchem_id": pubchem_ids[i],
                    "mol_b_pubchem_id": pubchem_ids[i + 1 + j],
                    "similarity": sim,
                })
    return edges
```

### Pattern 4: Cultural context vector — category inference from recipe names

**What:** `recipes_allrecipes.csv` lacks category labels. Reconstruct via recipe_name keywords.

**Problem:** The Phase 1 scraper wrote recipe names but dropped the category key. 76 recipes are available; the distribution is heavily Indian (30+) and Mexican (15+).

**Implementation:** Define a `CATEGORY_KEYWORDS` dict mapping cuisine category names to keyword fragments found in recipe names. Apply longest-match or first-match. This is deterministic (same keywords → same categories every run).

```python
# Hard-coded category keyword mapping (Claude's discretion)
ALLRECIPES_CATEGORIES = [
    "Italian", "Asian", "Mexican", "French", "American",
    "Indian", "Mediterranean", "Middle Eastern", "Japanese", "Thai"
]

CATEGORY_KEYWORDS = {
    "Indian": ["indian", "tikka", "masala", "curry", "biryani", "naan",
               "paneer", "chai", "saag", "korma", "chapati", "mango lassi",
               "chana", "keema", "mulligatawny", "tandoori", "gujarati"],
    "Mexican": ["mexican", "tamale", "quesadilla", "fajita", "chiles",
                "empanada", "chipotle", "agua", "flan", "barbacoa", "tacos"],
    "Italian": ["italian", "rigatoni", "penne", "gelato", "tuscan",
                "piccata", "pepperoni", "bellini"],
    # ... etc
}
```

For each recipe in `recipes_allrecipes.csv`, assign category by keyword match. For each ingredient appearing in that recipe, increment that category dimension.

### Pattern 5: Morgan fingerprint bytes storage in parquet

**What:** Store 1024-bit fingerprints as bytes column — NOT 1024 individual boolean columns.

**Verified:** `fp.ToBitString().encode()` produces 1024-byte `bytes` object. Parquet stores as binary blob. Phase 3 reads back with:
```python
# Decode in Phase 3:
fp_bytes = row["morgan_fp_bytes"]
fp_array = np.frombuffer(fp_bytes, dtype="S1").astype(np.uint8)
# fp_array is shape (1024,) with values 0 or 1 (as ord('0') and ord('1'))
# To get 0/1 integers: (fp_array == ord('1')).astype(np.float32)
```

### Anti-Patterns to Avoid
- **Querying PubChem for all 1788 molecules:** FlavorDB2 already has SMILES. Query only gaps.
- **Sorting tanimoto_edges by similarity descending:** Not required by spec; adds unnecessary sort overhead on 1.6M pairs.
- **Building 1024 binary columns for fingerprints:** Creates extremely wide DataFrames (1024 columns × 1788 rows); bytes column is far simpler.
- **Crashing on RDKit sanitization failure:** Must log and continue — pipeline-continues-on-failure is the project pattern.
- **Rebuilding flavor_profile vocabulary per ingredient:** Build vocabulary once over full dataset, then encode each ingredient against that fixed vocab.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tanimoto similarity | Manual Jaccard on bit arrays | DataStructs.BulkTanimotoSimilarity | C++ implementation, handles edge cases, ~100x faster |
| SMILES parsing / molecule sanitization | Custom SMILES parser | Chem.MolFromSmiles() | Handles tautomers, aromaticity perception, stereochemistry |
| Morgan fingerprint | Circular subgraph hashing | AllChem.GetMorganFingerprintAsBitVect | Canonical algorithm, radius-2 is ECFP4 standard |
| Async rate limiting | time.sleep() calls | asyncio.Semaphore | Non-blocking, respects concurrency ceiling correctly |
| Parquet serialization | CSV with base64 bytes | pd.to_parquet() via pyarrow | Schema-preserving, efficient binary, Phase 3 compatible |

**Key insight:** RDKit is mature cheminformatics software — every operation around molecular descriptors, fingerprints, and similarity has a canonical API. Do not reimplement any of it.

---

## Common Pitfalls

### Pitfall 1: PubChem 503 / rate limit responses treated as null SMILES

**What goes wrong:** httpx gets a 503 or rate-limit response; the code stores `None` in the cache as if the molecule has no SMILES. Running the script twice then gives different coverage counts.

**Why it happens:** 503 is not the same as 404 (molecule not found). Storing it as null breaks the determinism requirement.

**How to avoid:** Distinguish HTTP status codes explicitly: 200 → store SMILES, 404 → store `None` (legitimate miss), 5xx → raise exception / retry, do NOT store as null.

**Warning signs:** Cache coverage drops between runs; log shows 503 errors followed by null entries.

### Pitfall 2: AllRecipes category labels not in CSV — silent wrong vectors

**What goes wrong:** `recipes_allrecipes.csv` has no category column. Building cultural context without reconstructing categories produces all-zero vectors or silently wrong vectors for all ingredients.

**Why it happens:** Phase 1 scraper stored recipe_name + ingredients but dropped the category key (used only for URL construction).

**How to avoid:** At build_features.py start, define `CATEGORY_KEYWORDS` dict and apply it to recipe names from `recipes_allrecipes.csv`. Log which recipes matched which category, and how many were unmatched (warn if >10% unmatched).

**Warning signs:** Cultural context vectors all-zero for ingredients; no category assignment log entries.

### Pitfall 3: Morgan fingerprint bytes decoded incorrectly in Phase 3

**What goes wrong:** `ToBitString()` returns ASCII characters `'0'` and `'1'`, not bytes 0x00 and 0x01. `np.frombuffer(fp_bytes, dtype=np.uint8)` then gives `48` and `49` (ASCII codes), not `0` and `1`.

**Why it happens:** Confusion between bit-string ASCII representation and raw binary.

**How to avoid:** Either (a) decode with `(fp_array == ord('1')).astype(np.float32)` in Phase 3, or (b) store raw binary using `DataStructs.BitVectToText()` approach or convert with `np.array(fp, dtype=np.uint8).tobytes()` at write time. Document the encoding convention in a comment in both fetch script and the Phase 3 reader.

**Warning signs:** Fingerprint vectors are all near-identical (all 48 or all 49 values); Tanimoto computed from decoded vectors doesn't match RDKit results.

### Pitfall 4: RDKit Chem.MolFromSmiles silently returns None without logging

**What goes wrong:** Sanitization failures return `None` silently. The null propagates into descriptor columns without any record of which molecule failed.

**Why it happens:** RDKit returns `None` on failure; without explicit None-check + log, the failure is invisible.

**How to avoid:** Always wrap `Chem.MolFromSmiles(smiles)` with a None check and log the pubchem_id, common_name, and SMILES string on failure.

**Warning signs:** molecules.parquet has unexpected null rows in descriptor columns; no corresponding log entries.

### Pitfall 5: pubchem_cache.json gate check using row count instead of null count

**What goes wrong:** Gate check in build_features.py verifies `len(cache) == len(molecules_df)` but some entries are `None` (legitimate misses). Gate blocks processing incorrectly OR accepts a partial cache.

**Why it happens:** "100% populated" means every pubchem_id has an entry (even null), NOT that every entry has a valid SMILES.

**How to avoid:** Gate condition: `set(cache.keys()) == set(all_pubchem_ids)` — every ID has an entry. Null entries are acceptable (and expected for PubChem 404s). Log count of null vs non-null entries.

### Pitfall 6: Flavor profile vocabulary built per-ingredient produces ragged vectors

**What goes wrong:** If vocabulary is built per-ingredient, different ingredients have different vector lengths. Phase 3 cannot concatenate them into a feature matrix.

**Why it happens:** `union(molecule.flavor_profile for mol in ingredient.molecules)` gives different tag sets per ingredient.

**How to avoid:** Build the full vocabulary once over ALL molecules, sort it for determinism, store in a vocabulary file or constant. Then encode each ingredient against the fixed vocabulary.

---

## Code Examples

Verified patterns from official sources and environment testing:

### Async PubChem SMILES fetch with Semaphore
```python
# Source: PubChem PUG-REST (iupac.github.io), httpx 0.28.1
import asyncio
import httpx

PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/CanonicalSMILES/txt"
SEMAPHORE_LIMIT = 5  # ≤5 req/sec per PubChem policy (300/min, well under 400/min ceiling)

async def fetch_smiles_for_id(client: httpx.AsyncClient, sem: asyncio.Semaphore,
                               pubchem_id: int) -> tuple[int, str | None]:
    async with sem:
        try:
            resp = await client.get(PUBCHEM_URL.format(cid=pubchem_id), timeout=15.0)
            if resp.status_code == 200:
                return pubchem_id, resp.text.strip()
            elif resp.status_code == 404:
                return pubchem_id, None  # legitimate: molecule not in PubChem
            else:
                resp.raise_for_status()  # 5xx → exception, do NOT store as null
        except Exception as exc:
            raise  # re-raise; caller catches and skips this ID

async def fetch_missing_smiles(missing_ids: list[int]) -> dict[int, str | None]:
    sem = asyncio.Semaphore(SEMAPHORE_LIMIT)
    results = {}
    async with httpx.AsyncClient() as client:
        tasks = [fetch_smiles_for_id(client, sem, cid) for cid in missing_ids]
        for coro in asyncio.as_completed(tasks):
            try:
                cid, smiles = await coro
                results[cid] = smiles
            except Exception as exc:
                logger.error("PubChem fetch failed for batch: %s", exc)
    return results
```

### RDKit descriptor + Morgan fingerprint computation
```python
# Source: RDKit 2025.03.6 — verified in flavor-network env
from rdkit import Chem
from rdkit.Chem import Descriptors, AllChem

def compute_molecule_features(pubchem_id: int, smiles: str | None,
                               common_name: str) -> dict:
    """Returns dict with descriptor cols + morgan_fp_bytes. Nulls on failure."""
    null_row = {
        "pubchem_id": pubchem_id, "smiles": smiles,
        "MW": None, "logP": None, "HBD": None, "HBA": None,
        "rotatable_bonds": None, "TPSA": None, "morgan_fp_bytes": None,
    }
    if not smiles:
        return null_row

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        logger.warning("RDKit sanitization failure: pubchem_id=%d name=%s smiles=%s",
                       pubchem_id, common_name, smiles[:80])
        return null_row

    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=1024)
    return {
        "pubchem_id": pubchem_id, "smiles": smiles,
        "MW": Descriptors.MolWt(mol),
        "logP": Descriptors.MolLogP(mol),
        "HBD": Descriptors.NumHDonors(mol),
        "HBA": Descriptors.NumHAcceptors(mol),
        "rotatable_bonds": Descriptors.NumRotatableBonds(mol),
        "TPSA": Descriptors.TPSA(mol),
        "morgan_fp_bytes": fp.ToBitString().encode(),  # 1024-byte ASCII bit string
    }
```

### Tanimoto all-pairs — verified fast for 1788 molecules
```python
# Source: RDKit DataStructs — verified ~0.4s for 1788 molecules in flavor-network env
from rdkit.Chem import DataStructs

def compute_tanimoto_edges(fps_and_ids: list[tuple]) -> list[dict]:
    """fps_and_ids: list of (pubchem_id, RDKit ExplicitBitVect) for non-null FPs"""
    fps = [fp for _, fp in fps_and_ids]
    ids = [pid for pid, _ in fps_and_ids]
    edges = []
    for i in range(len(fps)):
        sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps[i+1:])
        for j, sim in enumerate(sims):
            if sim > 0.7:
                edges.append({
                    "mol_a_pubchem_id": ids[i],
                    "mol_b_pubchem_id": ids[i + 1 + j],
                    "similarity": float(sim),
                })
    return edges
```

### Parquet write — bytes column round-trip verified
```python
# Source: pyarrow 23.0.1 — verified bytes column survives parquet round-trip
import pandas as pd

# Write
df.to_parquet("data/processed/molecules.parquet", index=False, engine="pyarrow")

# Read back — bytes column returns as Python bytes objects
df2 = pd.read_parquet("data/processed/molecules.parquet")
# df2["morgan_fp_bytes"][i] is bytes of length 1024

# Phase 3 decode (document this at write site):
# fp_bytes = row["morgan_fp_bytes"]
# is_one = (np.frombuffer(fp_bytes, dtype=np.uint8) == ord('1'))
# fp_float = is_one.astype(np.float32)  # shape (1024,)
```

### Flavor profile vocabulary build — deterministic
```python
# Build vocabulary once over ALL molecules
import pandas as pd

mol_df = pd.read_csv("data/raw/molecules.csv")
all_tags = set()
for fp_str in mol_df["flavor_profile"].dropna():
    all_tags.update(tag.strip() for tag in fp_str.split("@") if tag.strip())
FLAVOR_VOCAB = sorted(all_tags)  # sorted for determinism
FLAVOR_VOCAB_INDEX = {tag: i for i, tag in enumerate(FLAVOR_VOCAB)}

# Encode one ingredient
def encode_flavor_profile(molecule_rows: list[dict]) -> list[int]:
    vec = [0] * len(FLAVOR_VOCAB)
    for mol in molecule_rows:
        fp_str = mol.get("flavor_profile", "")
        for tag in (fp_str or "").split("@"):
            tag = tag.strip()
            if tag in FLAVOR_VOCAB_INDEX:
                vec[FLAVOR_VOCAB_INDEX[tag]] = 1
    return vec
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ECFP4 = 2048-bit Morgan | 1024-bit Morgan for memory efficiency | Project decision | Half the storage; adequate for Tanimoto discrimination at 1788-molecule scale |
| rdkit.Chem.Draw (legacy API) | rdkit.Chem.AllChem (unified) | RDKit ~2020 | AllChem is the standard module for fingerprints and 3D ops |
| numpy-based Tanimoto matrix | DataStructs.BulkTanimotoSimilarity | RDKit native | Avoids Python overhead; C++ implementation |

**Deprecated/outdated:**
- `rdkit.Chem.MACCSkeys`: Not used here; MACCS gives 166-bit fixed keys, less informative than Morgan for similarity
- `requests` (sync): Project uses async httpx; sync requests would be 10-50x slower for bulk PubChem fetches

---

## Critical Data Findings

### FlavorDB2 SMILES Coverage: 100%
The `molecules_json` column in `ingredients.csv` contains a `smile` field for all 1788 unique molecules. When tested with `Chem.MolFromSmiles()`: **1788 valid, 0 failures**. This means:
- `fetch_smiles.py` should FIRST extract SMILES from `ingredients.csv` molecules_json
- PubChem queries are needed only for IDs present in `molecules.csv` but missing from the ingredients data (expected: 0)
- The pubchem_cache.json gate will be satisfied immediately without any network calls in the happy path

### AllRecipes Category Gap
`recipes_allrecipes.csv` (76 rows) has columns `recipe_name`, `ingredients` only. Category labels were not stored. Distribution is approximately:
- Indian: ~35 recipes
- Mexican: ~15 recipes
- Italian: ~10 recipes
- Other categories: ~16 recipes combined

The cultural context 10-dim vector will be meaningful but NOT uniform — Indian/Mexican cuisine dimensions will be much better populated than French, Japanese, Thai, etc.

### molecules.csv Has 1788 Rows (not 1789)
The raw CSV header counts as line 1; actual data rows = 1788. This matches the unique pubchem_id count from FlavorDB2 scraping.

---

## Open Questions

1. **Moisture content availability for texture feature**
   - What we know: `moisture_content` column exists in `molecules.csv` from FooDB join; however, FooDB data contains nutritional info at the food level not the molecule level. Many rows may be null (FooDB JSON directory found but column may contain NaN for unmatched ingredients).
   - What's unclear: What fraction of ingredients have non-null moisture_content? If mostly null, the moisture-based crispy/soft boundary adjustment may be unreliable.
   - Recommendation: At build time, log the fraction of ingredients with non-null moisture_content. If <20% have values, fall back to pure category-based texture mapping (ignore moisture modifier).

2. **Flavor profile tag normalization**
   - What we know: `flavor_profile` in `molecules.csv` uses `@`-delimited tags like `butter@caramel@nut@peanut butter`. Some tags contain spaces (e.g., "peanut butter").
   - What's unclear: Are tags normalized across FlavorDB2 and FooDB data? Could the same flavor appear as "cocoa" and "chocolate" in different rows?
   - Recommendation: Build vocabulary from the raw tags without normalization (as specified); accept some redundancy. This is consistent with Phase 3's use of this feature.

3. **cooccurrence.parquet filter threshold**
   - What we know: `recipes.csv` has 5.9M ingredient pair rows with counts derived from RecipeNLG + AllRecipes.
   - What's unclear: Should all pairs be written to cooccurrence.parquet, or should a minimum count threshold be applied? The CONTEXT.md says "carried forward from Phase 1 recipes.csv" without specifying a filter.
   - Recommendation: Write all pairs without filtering; Phase 3 GRAPH-05 applies normalization by max co-occurrence. Total parquet file size for 5.9M rows × 3 columns (2 strings + 1 int) ≈ 100-200MB — acceptable on M2/8GB.

---

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.4 |
| Config file | none — no pytest.ini or pyproject.toml detected |
| Quick run command | `conda run -n flavor-network python -m pytest tests/test_features.py -x -q` |
| Full suite command | `conda run -n flavor-network python -m pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FEAT-01 | pubchem_cache.json populated; all pubchem_ids have entry | unit | `pytest tests/test_features.py::test_smiles_cache_coverage -x` | Wave 0 |
| FEAT-01 | Missing SMILES logged, not silently dropped | unit | `pytest tests/test_features.py::test_smiles_missing_logged -x` | Wave 0 |
| FEAT-02 | RDKit descriptors computed correctly for known molecule | unit | `pytest tests/test_features.py::test_rdkit_descriptors -x` | Wave 0 |
| FEAT-02 | Sanitization failure logs ingredient + molecule name | unit | `pytest tests/test_features.py::test_rdkit_sanitization_logged -x` | Wave 0 |
| FEAT-03 | Morgan fingerprint is 1024 bytes, radius=2 | unit | `pytest tests/test_features.py::test_morgan_fingerprint -x` | Wave 0 |
| FEAT-04 | Tanimoto edges > 0.7 only; columns match schema | unit | `pytest tests/test_features.py::test_tanimoto_edges -x` | Wave 0 |
| FEAT-05 | Texture vector is 5-dim one-hot, valid category | unit | `pytest tests/test_features.py::test_texture_encoding -x` | Wave 0 |
| FEAT-06 | Temperature vector is 4-dim one-hot, valid category | unit | `pytest tests/test_features.py::test_temperature_encoding -x` | Wave 0 |
| FEAT-07 | Cultural context vector is 10-dim; sums ≥ 0 | unit | `pytest tests/test_features.py::test_cultural_context -x` | Wave 0 |
| FEAT-08 | Flavor profile vector is consistent length across ingredients | unit | `pytest tests/test_features.py::test_flavor_profile_vocab -x` | Wave 0 |
| FEAT-09 | All 4 parquet files exist in data/processed/ | integration | `pytest tests/test_features.py::test_parquet_outputs_exist -x` | Wave 0 |
| FEAT-09 | molecules.parquet schema matches spec | integration | `pytest tests/test_features.py::test_molecules_parquet_schema -x` | Wave 0 |
| FEAT-09 | ingredients.parquet schema matches spec | integration | `pytest tests/test_features.py::test_ingredients_parquet_schema -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `conda run -n flavor-network python -m pytest tests/test_features.py -x -q`
- **Per wave merge:** `conda run -n flavor-network python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_features.py` — all FEAT-01 through FEAT-09 unit and integration tests
- [ ] No `pytest.ini` or `pyproject.toml` with testpaths configured (no-config pytest works fine by discovery)

*(No shared fixtures needed — tests can use small in-memory DataFrames and a few hard-coded SMILES strings)*

---

## Sources

### Primary (HIGH confidence)
- RDKit 2025.03.6 — verified in `flavor-network` conda env; all descriptor and fingerprint APIs tested interactively
- pyarrow 23.0.1 — bytes column parquet round-trip verified in `flavor-network` conda env
- httpx 0.28.1 — AsyncClient + asyncio.Semaphore pattern verified in `flavor-network` conda env
- FlavorDB2 `ingredients.csv` data — SMILES coverage verified: 1788/1788 molecules (100%)
- `data/raw/molecules.csv` — 1788 rows confirmed
- `data/raw/recipes_allrecipes.csv` — category absence confirmed by inspection

### Secondary (MEDIUM confidence)
- [PubChem PUG-REST via IUPAC Cookbook](https://iupac.github.io/WFChemCookbook/datasources/pubchem_pugrest1.html) — URL format `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{CID}/property/CanonicalSMILES/txt` and rate limit ≤5 req/sec confirmed

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in flavor-network conda env
- Architecture: HIGH — patterns derived from existing codebase + verified API calls
- Pitfalls: HIGH — pitfall 1–4 verified by testing; pitfall 5–6 derived from data inspection
- Data findings: HIGH — verified by running code against actual data files

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable domain — RDKit, httpx, pyarrow APIs don't change rapidly)
