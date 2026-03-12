---
phase: 03-graph-construction
plan: "03"
subsystem: graph
tags: [pytorch, rdkit, tanimoto, tqdm, pandas, torch-geometric, morgan-fingerprint, graph-edges]

# Dependency graph
requires:
  - phase: 03-graph-construction
    provides: graph/build_graph.py with node features, index dicts, and TODO edge stubs (Plan 03-02)
provides:
  - _build_contains_edges: ingredient->molecule edges with FooDB concentration weights (fallback 1.0)
  - _build_cooccurs_edges: co-occurrence edges normalized to [0,1] with match rate logging and <80% warning
  - _build_structural_edges: Tanimoto lower-triangle via BulkTanimotoSimilarity, threshold 0.7, undirected output
  - build_graph() TODOs replaced with real edge builder calls
affects:
  - 03-04-assembly

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Lower-triangle BulkTanimotoSimilarity loop for O(n^2/2) structural similarity without full matrix
    - Dual-strategy ingredient-molecule membership: molecule_ids column first, ingredient_id in mol_df fallback
    - Name normalization via .lower().strip() with match rate logging and threshold warning

key-files:
  created: []
  modified:
    - graph/build_graph.py

key-decisions:
  - "_build_structural_edges: ExplicitBitVect deserialization used for BulkTanimotoSimilarity; ascii_bits format (our actual format) is handled by the outer _deserialize_fp helper but structural edges need BitVect objects not numpy arrays — separate deserialization path in _build_structural_edges"
  - "Contains edges use dual-strategy: molecule_ids column in ingredients.parquet preferred; falls back to ingredient_id column in molecules.parquet; warns and returns empty if neither present"
  - "Co-occurs match rate warning threshold is <80% (not >20% skip rate) matching the plan's 'warns if >20% of names fail to match' requirement"

patterns-established:
  - "Edge builders return (edge_index, edge_attr) tuple — consistent signature for all three types"
  - "Empty-edge guard pattern: if not src_indices: return zeros tensors (avoids torch.tensor([]) errors)"

requirements-completed: [GRAPH-04, GRAPH-05, GRAPH-06]

# Metrics
duration: 6min
completed: 2026-03-12
---

# Phase 3 Plan 03: Edge Construction Functions Summary

**Three edge builders (_build_contains_edges, _build_cooccurs_edges, _build_structural_edges) added to build_graph.py using BulkTanimotoSimilarity lower-triangle loop, FooDB concentration weights, and co-occurrence name normalization with match rate logging**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-03-12T04:08:14Z
- **Completed:** 2026-03-12T04:14:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added _build_contains_edges with dual-strategy ingredient-molecule lookup (molecule_ids column or ingredient_id in mol_df) and FooDB concentration weights with 1.0 fallback
- Added _build_cooccurs_edges with .lower().strip() name normalization, [0,1] weight normalization by max count, match rate logging, and <80% warning
- Added _build_structural_edges with ExplicitBitVect deserialization, BulkTanimotoSimilarity lower-triangle loop, 0.7 threshold, and undirected output via reverse edge concatenation
- Replaced all three TODO stubs in build_graph() with real calls to edge builder functions
- Verified: import exits 0 with "Edge functions OK"; pytest 1 passed, 8 skipped, 0 failed

## Task Commits

1. **Task 1: Add three edge-building functions to build_graph.py** - `0c32954` (feat)

## Files Created/Modified

- `graph/build_graph.py` — Added 223 lines: _build_contains_edges, _build_cooccurs_edges, _build_structural_edges, and replaced TODO stubs in build_graph()

## Decisions Made

- `_build_structural_edges` deserializes fingerprints directly to ExplicitBitVect (required for BulkTanimotoSimilarity) rather than going through the existing _deserialize_fp numpy path — the two uses have incompatible output types.
- Contains edges: dual lookup strategy (molecule_ids column preferred, ingredient_id in mol_df as fallback) matches the pattern already used in _build_ingredient_features.
- Co-occurs warning threshold: match_rate < 0.80 (i.e., skip rate > 20%) — matches plan wording "warns if >20% of names fail to match".

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — import verified cleanly, tests unchanged at 1 passed / 8 skipped / 0 failed.

## Next Phase Readiness

- All three edge builders are importable and return (edge_index, edge_attr) tuples ready for HeteroData assembly
- Plan 03-04 can now call the edge builders and assemble the full HeteroData object, run run_validation_gate(), apply RandomLinkSplit, and save graph/hetero_data.pt
- The `# TODO: assemble, validate, split, save` comment remains as the Plan 03-04 entry point

---
*Phase: 03-graph-construction*
*Completed: 2026-03-12*
