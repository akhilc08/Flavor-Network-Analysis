---
phase: 05-scoring-and-active-learning
plan: 02
subsystem: scoring
tags: [torch, numpy, pandas, vectorized, matmul, sigmoid, jaccard, pickle, atomic-write]

# Dependency graph
requires:
  - phase: 04-model-training
    provides: ingredient_embeddings.pkl (935 ingredient vectors, shape 128) and hetero_data.pt graph payload
  - phase: 03-graph-construction
    provides: hetero_data.pt with co_occurs and contains edge_index/edge_attr

provides:
  - scoring/score.py — full implementation of compute_all_pairs, save_scored_pairs, load_scored_pairs, get_top_pairings, get_uncertain_pairs
  - scoring/compute_scores.py — standalone orchestration script producing scoring/scored_pairs.pkl
  - scoring/scored_pairs.pkl — 436,645 ingredient pair rows sorted by surprise_score descending

affects: [06-api-and-interface, 05-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Vectorized all-pairs scoring: (n,128) matmul produces (n,n) similarity; torch.triu_indices extracts upper triangle without Python pair loop"
    - "Atomic file write: df.to_pickle(tmp) + os.replace(tmp, final) for POSIX-safe scored_pairs.pkl"
    - "Integer ID keying: embeddings and graph both use integer ingredient IDs — compute_all_pairs works with any hashable key type"
    - "Label assignment via pd.cut with explicit bins [-0.001, 0.33, 0.66, 1.001] and LABEL_NAMES"

key-files:
  created:
    - scoring/score.py
    - scoring/compute_scores.py
    - scoring/scored_pairs.pkl
  modified: []

key-decisions:
  - "Embeddings and graph use integer ingredient IDs as keys — compute_all_pairs accepts any hashable key; ingredient_a/ingredient_b columns contain integer IDs"
  - "compute_scores.py inverts ingredient_id_to_idx (idx->id) and molecule_id_to_idx (idx->id) from graph payload for consistent keying"
  - "co_occurrence dict built from graph edge_index + edge_attr; symmetric edges preserved as separate dict entries"
  - "molecule_sets built from ingredient/contains/molecule edge_index using inverted molecule_id_to_idx mapping"
  - "All 5 scoring tests pass (not 4+skip) because Phase 4 artifacts exist in this environment; test_scored_pairs_file runs and passes after compute_scores.py generates scored_pairs.pkl"

patterns-established:
  - "Scoring pattern: embeddings matmul -> sigmoid -> per-pair Jaccard/familiarity -> formula -> pd.cut labels"
  - "Orchestration script pattern: validate inputs -> load artifacts -> build dicts -> compute -> save atomically -> log summary"

requirements-completed: [SCORE-01, SCORE-02, SCORE-03, SCORE-04, LEARN-02]

# Metrics
duration: 15min
completed: 2026-03-15
---

# Phase 5 Plan 02: Vectorized Scoring Pipeline Summary

**Torch matmul-based all-pairs scoring producing 436,645 ingredient pair rows with surprise_score in 4 seconds; saved atomically to scoring/scored_pairs.pkl**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-15T18:09:01Z
- **Completed:** 2026-03-15T18:24:00Z
- **Tasks:** 2
- **Files modified:** 2 created

## Accomplishments

- Implemented compute_all_pairs() using torch matmul + sigmoid (no Python loop over pairs)
- Scored 436,645 pairs in ~4 seconds on M2: 18.5% Surprising, 55.2% Unexpected, 26.4% Classic
- All 5 pytest tests pass (test_scored_pairs_file runs and passes because Phase 4 artifacts present)
- compute_scores.py runs as standalone script and is importable as run_scoring()

## Task Commits

1. **Task 1: Implement scoring/score.py** - `f575d41` (feat)
2. **Task 2: Implement scoring/compute_scores.py** - `2e8e8cb` (feat)

## Files Created/Modified

- `scoring/score.py` — Full implementation: compute_all_pairs (vectorized matmul+sigmoid), save_scored_pairs (atomic), load_scored_pairs, get_top_pairings, get_uncertain_pairs
- `scoring/compute_scores.py` — Standalone orchestration script with run_scoring(force=False) entry point; reconstructs co_occurrence and molecule_sets from graph payload
- `scoring/scored_pairs.pkl` — 436,645 rows, sorted by surprise_score descending, columns: ingredient_a, ingredient_b, surprise_score, pairing_score, molecular_overlap, recipe_familiarity, label

## Decisions Made

- Embeddings and graph use integer ingredient IDs as keys (not string names). compute_all_pairs works with any hashable key type; ingredient_a/b columns contain integer IDs. Phase 6 will need to resolve IDs to names via a lookup table if human-readable output is needed.
- co_occurrence dict built directly from hetero_data edge_index + edge_attr by inverting ingredient_id_to_idx. The graph has 27,912 directed co-occurrence entries covering the symmetric relationship.
- molecule_sets built from ingredient/contains/molecule edges using inverted molecule_id_to_idx. All 935 ingredients have molecule sets.
- compute_scores.py adds sys.path manipulation is NOT needed (runs via `python -m scoring.compute_scores` from project root).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Integer ID keys in embeddings, not string ingredient names**
- **Found during:** Task 2 (compute_scores.py implementation)
- **Issue:** Plan interface shows `{ingredient_name: np.ndarray}` but actual embeddings.pkl uses `{int_id: np.ndarray}`. Graph payload also uses integer IDs throughout.
- **Fix:** compute_scores.py inverts both `ingredient_id_to_idx` and `molecule_id_to_idx` to reconstruct keyed dicts using the same integer IDs as the embeddings. compute_all_pairs works with any hashable key.
- **Files modified:** scoring/compute_scores.py
- **Verification:** All 5 tests pass; scored_pairs.pkl produced with 436,645 rows
- **Committed in:** 2e8e8cb (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (data contract mismatch between plan interface and actual artifact)
**Impact on plan:** Fix required for correctness. No scope creep.

## Issues Encountered

- Phase 4 artifacts exist in this environment (ingredient_embeddings.pkl, hetero_data.pt), so test_scored_pairs_file does NOT skip — it runs and passes after compute_scores.py generates scored_pairs.pkl. Plan expected 4 pass + 1 skip; actual result is 5 pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- scoring/scored_pairs.pkl ready for Phase 6 API consumption
- load_scored_pairs(), get_top_pairings(), get_uncertain_pairs() all implemented and tested
- Integer ID keys in scored_pairs — Phase 6 will need ingredient name lookup (e.g., from ingredients parquet or a reverse ID map)

---
*Phase: 05-scoring-and-active-learning*
*Completed: 2026-03-15*
