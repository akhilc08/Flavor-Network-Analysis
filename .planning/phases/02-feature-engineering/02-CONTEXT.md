# Phase 2: Feature Engineering - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Fetch canonical SMILES from PubChem for all molecules, compute RDKit descriptors and Morgan fingerprints, compute Tanimoto similarity edges, and build multimodal ingredient features (texture, temperature affinity, cultural context, flavor profile). Outputs all processed features to data/processed/ as parquet files. Graph construction is Phase 3.

</domain>

<decisions>
## Implementation Decisions

### PubChem SMILES Fetch
- Cache format: JSON file (`data/raw/pubchem_cache.json`) — simple `{pubchem_id: smiles_string}` dict; easier to inspect than SQLite for key-value lookups
- HTTP client: async httpx with asyncio.Semaphore rate limiting (≤400 req/min ceiling) — faster throughput for 1,789 molecules than sync requests
- Missing SMILES (404 or empty): retain molecule row in processed output with `smiles=None`; log by molecule name and pubchem_id; RDKit steps skip nulls deterministically
- Cache must be 100% populated before RDKit processing begins (gate enforced in build_features.py)

### RDKit Descriptors and Fingerprints
- Descriptors per molecule: MW, logP, HBD, HBA, rotatable bonds, TPSA (6 columns in molecules.parquet)
- Sanitization failures: logged with ingredient name + molecule name; molecule retains null descriptor columns; does not crash pipeline
- Morgan fingerprints: radius=2, 1024 bits; stored as serialized bytes column (`morgan_fp_bytes`) in molecules.parquet — not 1024 binary columns
- Tanimoto similarity: computed for all molecule pairs with similarity > 0.7; saved as tanimoto_edges.parquet with columns: mol_a_pubchem_id, mol_b_pubchem_id, similarity

### Multimodal Ingredient Features
- **Texture embedding**: 5-dim one-hot (crispy/soft/creamy/chewy/crunchy); hard-coded category→texture dict; moisture content adjusts crispy vs soft boundary
- **Temperature affinity**: 4-dim one-hot (raw/cold/warm/hot); hard-coded ingredient category → temperature lookup table
- **Cultural context vector**: 10-dim one-hot over AllRecipes categories (Italian, Asian, Mexican, French, American, Indian, Mediterranean, Middle Eastern, Japanese, Thai); derived from recipes.csv recipe-to-category tags
- **Flavor profile multi-hot**: union of all `flavor_profile` tags across all molecules belonging to the ingredient; deduplicated; vocabulary built from full dataset; stored as multi-hot vector

### Output File Schema
- `data/processed/ingredients.parquet` — one row per ingredient; columns: ingredient_id, name, category, foodb enrichment fields, texture (5 cols), temperature (4 cols), cultural_context (10 cols), flavor_profile_multihot (N cols where N = vocab size)
- `data/processed/molecules.parquet` — one row per molecule; columns: pubchem_id, smiles, MW, logP, HBD, HBA, rotatable_bonds, TPSA, morgan_fp_bytes
- `data/processed/tanimoto_edges.parquet` — molecule pair edges with similarity > 0.7; columns: mol_a_pubchem_id, mol_b_pubchem_id, similarity
- `data/processed/cooccurrence.parquet` — ingredient co-occurrence counts carried forward from Phase 1 recipes.csv; columns: ingredient_a, ingredient_b, count

### Script Organization
- Two scripts: `data/fetch_smiles.py` (PubChem async fetch → pubchem_cache.json) + `data/build_features.py` (RDKit descriptors, Morgan, Tanimoto, multimodal → parquets)
- Both runnable standalone: `python data/fetch_smiles.py`, `python data/build_features.py`
- `run_pipeline.py` calls `fetch_smiles()` and `build_features()` functions directly (same pattern as Phase 1)
- `--skip-smiles` skips fetch_smiles if pubchem_cache.json already complete; `--skip-features` skips build_features if parquets exist

### Claude's Discretion
- Exact texture/temperature lookup table values (specific category→texture mappings)
- Flavor profile vocabulary size and ordering
- Tanimoto computation approach (all-pairs vs batched for memory efficiency)
- Async concurrency limit (semaphore count within 400 req/min ceiling)

</decisions>

<specifics>
## Specific Ideas

- User deferred all implementation method choices to Claude — prioritize fewest bugs and simplest implementation
- Memory efficiency matters (M2/8GB): Tanimoto all-pairs on 1,789 molecules is ~1.6M pairs — compute in numpy batches if needed
- Pipeline continues on failure (Phase 1 pattern): log and skip, never crash

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `data/scrape_flavordb.py`: argparse + logging + tqdm pattern to replicate in new scripts
- `data/join_foodb.py`: shows how to read ingredients.csv and molecules.csv, RapidFuzz usage pattern
- `logs/pipeline.log`: shared log file — new scripts append to same file

### Established Patterns
- Standalone script pattern: `if __name__ == "__main__": main()` with argparse `--force` flag
- Logging: `os.makedirs("logs", exist_ok=True)` + file handler + tqdm-compatible console handler
- Summary table at end: print counts of processed/failed/skipped with percentages
- Skip-if-exists: check output file existence at script start, return early if present and not `--force`

### Integration Points
- Inputs: `data/raw/molecules.csv` (pubchem_id column), `data/raw/ingredients.csv`, `data/raw/recipes.csv`
- Output: `data/processed/*.parquet` — consumed by Phase 3 graph construction
- Cache: `data/raw/pubchem_cache.json` — persists between runs; Phase 3 does not need it directly
- `run_pipeline.py`: add `fetch_smiles` and `build_features` as new stages after existing Phase 1 stages

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-feature-engineering*
*Context gathered: 2026-03-11*
