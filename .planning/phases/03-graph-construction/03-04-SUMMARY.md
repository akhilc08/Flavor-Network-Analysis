---
phase: 03-graph-construction
plan: "04"
subsystem: graph
tags: [pytorch-geometric, HeteroData, RandomLinkSplit, link-prediction, graph-construction]

# Dependency graph
requires:
  - phase: 03-02
    provides: edge builder functions (_build_contains_edges, _build_cooccurs_edges, _build_structural_edges)
  - phase: 03-03
    provides: validation gate (run_validation_gate) and build_graph() skeleton
  - phase: 02-feature-engineering
    provides: data/processed/*.parquet (ingredients, molecules, cooccurrence)

provides:
  - "graph/build_graph.py — complete standalone graph builder with HeteroData assembly, PyG validation, RandomLinkSplit, leakage assertion, save"
  - "graph/hetero_data.pt — torch payload with 5 keys (graph, val_data, test_data, ingredient_id_to_idx, molecule_id_to_idx)"
  - "graph/index_maps.json — human-readable sidecar with ingredient and molecule index maps"
  - "run_pipeline.py — Stage 4 (graph construction) wired with skip-if-exists logic"
  - "_print_graph_summary() helper for structured console/log output"

affects:
  - phase-04-model-training
  - phase-05-recommendation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HeteroData assembly: ingredient + molecule nodes, 3 edge types (contains, co_occurs, structurally_similar)"
    - "data.validate(raise_on_error=True) before validation gate — PyG structural check"
    - "run_validation_gate() as hard stop before RandomLinkSplit — blocks save if thresholds not met"
    - "RandomLinkSplit on co_occurs edges only (70/15/15, is_undirected=True, neg_sampling_ratio=1.0)"
    - "Leakage assertion before torch.save — AssertionError blocks write if any test edge in train edge_index"
    - "Payload dict with 5 keys: graph (train_data), val_data, test_data, ingredient_id_to_idx, molecule_id_to_idx"

key-files:
  created:
    - graph/hetero_data.pt
    - graph/index_maps.json
  modified:
    - graph/build_graph.py
    - run_pipeline.py

key-decisions:
  - "RandomLinkSplit rev_edge_types set to same type as edge_types (ingredient, co_occurs, ingredient) — co-occurrence is symmetric"
  - "Leakage check uses both (s,d) and (d,s) in train_set to catch both directions"
  - "run_pipeline.py Stage 4 skips if hetero_data.pt already exists (--force to rebuild) — consistent with Phase 1 skip-if-exists pattern"
  - "Summary table printed via _print_graph_summary() matching Phase 1 summary pattern and logged to logs/pipeline.log"

patterns-established:
  - "Graph payload saved as dict with named keys (not bare HeteroData) for easy partial loading"
  - "JSON sidecar (index_maps.json) for human-readable debugging of index mappings"

requirements-completed:
  - GRAPH-01
  - GRAPH-07
  - GRAPH-08
  - GRAPH-09

# Metrics
duration: 3min
completed: 2026-03-12
---

# Phase 3 Plan 04: Complete Graph Builder Summary

**HeteroData assembled with 3 edge types, RandomLinkSplit on co-occurs edges, zero-leakage assertion, and torch.save to graph/hetero_data.pt — graph construction wired as Stage 4 in run_pipeline.py**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-12T04:11:41Z
- **Completed:** 2026-03-12T04:14:21Z
- **Tasks:** 2 of 3 (Task 3 is human-verify checkpoint — awaiting Phase 2 artifacts)
- **Files modified:** 2

## Accomplishments

- Replaced the TODO stub in build_graph() with full HeteroData assembly, PyG structural validation, validation gate, RandomLinkSplit, leakage assertion, save, and summary table
- Added `_print_graph_summary()` helper that prints to both console and logs/pipeline.log
- Wired graph construction as Stage 4 in run_pipeline.py with skip-if-exists logic and `_print_summary()` extension to report graph artifacts
- Task 3 is a human-verify checkpoint awaiting Phase 2 data artifacts (data/processed/ parquets)

## Task Commits

Each task was committed atomically:

1. **Task 1: Complete build_graph() — assemble HeteroData, validate, split, assert leakage, save** - `dfec4f4` (feat)
2. **Task 2: Wire graph construction into run_pipeline.py** - `53c3cd4` (feat)
3. **Task 3: Human verify** - checkpoint (pending)

## Files Created/Modified

- `graph/build_graph.py` - Added _print_graph_summary(), replaced TODO stub with full build pipeline (128 lines added)
- `run_pipeline.py` - Added Stage 4 graph construction block, updated _import_stages(), extended _print_summary() with graph artifact info

## Decisions Made

- `rev_edge_types` for RandomLinkSplit set to `[('ingredient', 'co_occurs', 'ingredient')]` (same as edge_types) — co-occurrence graph is symmetric and undirected
- Leakage check tests both `(s, d)` and `(d, s)` against `train_set` to handle both edge directions
- `run_pipeline.py` skip-if-exists logic checks `graph/hetero_data.pt` directly (not a flag), consistent with Phase 1 pattern

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `graph/build_graph.py` is complete; run `python graph/build_graph.py` once Phase 2 data/processed/ parquets exist
- Task 3 (human-verify) checkpoint: run build, verify 9 tests pass, confirm artifact keys, approve
- Phase 4 model training requires `graph/hetero_data.pt` with 5 keys

---
*Phase: 03-graph-construction*
*Completed: 2026-03-12*
