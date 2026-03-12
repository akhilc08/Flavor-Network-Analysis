# Phase 3: Graph Construction - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a validated heterogeneous PyTorch Geometric HeteroData graph from the processed feature parquet files produced by Phase 2. Delivers `graph/hetero_data.pt` (with embedded index mappings) and `graph/index_maps.json`. Model training, scoring, and UI are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All gray areas were delegated to Claude — decisions optimized for portfolio quality and minimum bugs.

### Link Prediction Split
- Split **co-occurs edges only** (ingredient→ingredient) for train/val/test — these are the edges the model ultimately predicts, and splitting contains/structural-similar edges would not match the downstream scoring goal
- Split ratios: 70 / 15 / 15 (train / val / test)
- Negative sampling ratio: 1.0 (1 negative per positive) — balanced batches, standard for link prediction
- Message-passing graph uses training edges only; val and test edges excluded from edge_index
- Zero test-edge leakage asserted with an explicit assertion before saving — if the assert fails, the script raises and never writes the file

### Validation Gate Failure Behavior
- Hard stop: when ≥500 ingredient nodes or ≥2000 molecule nodes or any of the 3 edge types is missing, print a formatted diagnostics table then raise ValueError
- Diagnostics table format (for each criterion):
  - `✓ Ingredient nodes: 612 found (≥500)` or `✗ Ingredient nodes: 412 found, 500 required`
  - Same format for molecule nodes and each edge type
- After the table, print a remediation hint: "Run Phase 2 feature engineering and verify data/processed/ parquet files exist"
- No partial graph saved on failure — clean exit, no ambiguous artifacts

### ID Mapping Persistence
- Save as a dict embedded in the .pt file: `torch.save({"graph": hetero_data, "ingredient_id_to_idx": ..., "molecule_id_to_idx": ...}, "graph/hetero_data.pt")`
- Single atomic load for downstream phases (no synchronization issues)
- Also save `graph/index_maps.json` (JSON-serialized dicts) for human readability and debugging — small file, easy to inspect during demo
- Downstream phases (model training, scoring) load from the .pt dict, not from JSON

### Logging and Progress (carrying forward from Phase 1)
- tqdm progress bars for edge construction loops (contains, co-occurs, structural-similar)
- Summary table printed on successful completion: node counts, edge counts per type, split sizes
- All output also logged to `logs/pipeline.log`
- Script runnable standalone: `python graph/build_graph.py`
- `run_pipeline.py` calls it in order; skip if `graph/hetero_data.pt` already exists

</decisions>

<specifics>
## Specific Ideas

- No specific implementation preferences from user — all decisions delegated to Claude
- Portfolio context: the validation gate diagnostics table is intentionally polished — it's the kind of output that reads well in a demo when showing "what happens if data is incomplete"

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `data/scrape_flavordb.py`: tqdm + summary table pattern to follow
- `run_pipeline.py`: integration point — graph build step goes between Phase 2 feature engineering and Phase 4 model training; skip-if-exists logic already in orchestrator
- `logs/pipeline.log`: unified logging target already established

### Established Patterns
- Always-continue + summarize for data warnings; hard-stop only for threshold violations
- tqdm per batch + summary counts at end of script
- Script accepts no required CLI args when called standalone (flags only, e.g., `--force` to overwrite)

### Integration Points
- **Input**: `data/processed/*.parquet` files from Phase 2 (ingredient features, molecule features, co-occurrence counts, Tanimoto similarity pairs)
- **Output**: `graph/hetero_data.pt` (dict with graph + index maps), `graph/index_maps.json`
- Phase 4 model training loads `graph/hetero_data.pt` and uses the embedded train/val/test edge splits directly
- Phase 5 scoring loads the same file for embedding lookup via index maps

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-graph-construction*
*Context gathered: 2026-03-11*
