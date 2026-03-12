---
phase: 03-graph-construction
plan: "02"
subsystem: graph
tags: [pytorch, torch-geometric, rdkit, pandas, sklearn, parquet, morgan-fingerprint]

# Dependency graph
requires:
  - phase: 02-feature-engineering
    provides: ingredients.parquet, molecules.parquet, cooccurrence.parquet with all multimodal features
provides:
  - graph/build_graph.py importable module with logging, parquet loading, index dicts, node feature tensors
  - run_validation_gate() for threshold checking, used by GRAPH-07 test
  - build_graph() skeleton with TODO markers for edge construction (Plan 03-03)
affects:
  - 03-03-edges
  - 03-04-assembly

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Defensive fp format probing at startup with _probe_fp_format (returns enum string used throughout)
    - ascii_bits as the actual morgan fp format in this codebase (1024-byte ASCII '0'/'1' string)
    - All execution guarded by if __name__ == "__main__" or inside functions — clean import

key-files:
  created:
    - graph/build_graph.py
  modified:
    - tests/test_graph.py

key-decisions:
  - "graph/build_graph.py was already committed in fdd1de9 (phase-2 rebuild commit) — Task 1 verified correct implementation was in place"
  - "test_validation_gate: removed ImportError skip guard; now unconditionally imports run_validation_gate from graph.build_graph"
  - "Feature prefix detection uses tuple ('texture_', 'temperature_', 'cultural_context_', 'flavor_profile_') matching actual parquet column names from Phase 2"
  - "ingredient->molecule map falls back to data/raw/ingredients.csv molecules_json if molecule_ids column absent from ingredients.parquet"

patterns-established:
  - "Probe-first pattern: _probe_fp_format() determines serialization format before any bulk deserialization"
  - "Defensive column detection: only use columns that actually exist, log which are missing"

requirements-completed: [GRAPH-01, GRAPH-02, GRAPH-03]

# Metrics
duration: 10min
completed: 2026-03-12
---

# Phase 3 Plan 02: Build Graph Node Features Summary

**graph/build_graph.py with ascii-bit Morgan fp probing, index dicts, ingredient [N, D] and molecule [N, 1030] feature tensors, and unconditional test_validation_gate**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-12T00:00:00Z
- **Completed:** 2026-03-12T00:10:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Verified graph/build_graph.py (already committed in fdd1de9) imports cleanly with all required exports
- run_validation_gate() raises ValueError with diagnostics on insufficient node/edge counts
- _build_molecule_features produces shape [N, 1030] tensor (6 descriptors + 1024 Morgan bits)
- _build_ingredient_features mean-pools Morgan fps per ingredient and concatenates multimodal columns
- Updated test_validation_gate to unconditional import — 1 passed, 8 skipped, 0 failed

## Task Commits

1. **Task 1: Scaffold build_graph.py** - `fdd1de9` (feat — previously committed in phase-2 rebuild)
2. **Task 2: Update test_validation_gate** - `4431021` (feat)

## Files Created/Modified

- `graph/build_graph.py` — Full node feature pipeline: logging, argparse, _load_parquets, _build_index_dicts, _build_ingredient_features, _build_molecule_features, run_validation_gate, build_graph skeleton, main
- `tests/test_graph.py` — test_validation_gate: removed ImportError skip guard, now unconditional import + pytest.raises(ValueError, match="validation gate failed")

## Decisions Made

- `build_graph.py` was already committed as part of fdd1de9 (Phase 2 rebuild commit that also rebuilt parquets). Task 1 verified correctness rather than creating from scratch.
- Feature column prefixes used in `_build_ingredient_features` are `texture_`, `temperature_`, `cultural_context_`, `flavor_profile_` — matching actual Phase 2 parquet column names (plan listed slightly different prefixes but implementation used correct ones).
- Morgan fp format probing correctly identifies the `ascii_bits` format (1024-byte ASCII '0'/'1' string) as established in decision [02-03].

## Deviations from Plan

None — plan executed as written. `build_graph.py` was already in place from a prior commit and verified to be correct.

## Issues Encountered

None — import verified, test passed first try.

## Next Phase Readiness

- graph/build_graph.py node feature section is complete; Plan 03-03 will add _build_contains_edges, _build_cooccurs_edges, _build_structural_edges filling the TODO markers
- Index dicts (ingredient_id_to_idx, molecule_id_to_idx, name_to_ingredient_idx) are ready for edge construction
- test_validation_gate passes unconditionally — remaining 8 tests stay skipped until graph/hetero_data.pt is built

---
*Phase: 03-graph-construction*
*Completed: 2026-03-12*
