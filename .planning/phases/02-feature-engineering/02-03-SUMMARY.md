---
phase: 02-feature-engineering
plan: 03
subsystem: cheminformatics
tags: [rdkit, morgan-fingerprints, tanimoto, parquet, pyarrow, pandas]

# Dependency graph
requires:
  - phase: 02-feature-engineering/02-02
    provides: data/raw/pubchem_cache.json with 1788 SMILES entries (100% coverage)
  - phase: 02-feature-engineering/02-01
    provides: data/raw/molecules.csv with 1788 unique molecule rows
provides:
  - data/build_features.py with compute_molecule_features, compute_tanimoto_edges, build_molecule_df
  - data/processed/molecules.parquet: 1788 rows, 9 columns (pubchem_id, smiles, MW, logP, HBD, HBA, rotatable_bonds, TPSA, morgan_fp_bytes)
  - data/processed/tanimoto_edges.parquet: 1678 structural similarity edges (threshold > 0.7)
  - Multimodal encoding stubs: encode_texture, encode_temperature, build_cultural_context_vectors, build_flavor_vocab, encode_flavor_profile (ready for Plan 04)
affects:
  - 02-04-PLAN (multimodal features: adds to build_features.py)
  - Phase 3 graph construction: tanimoto_edges.parquet becomes GRAPH-06 structural similarity edges
  - Phase 3 molecule decoding: morgan_fp_bytes decoded via (np.frombuffer(fp_bytes, dtype=np.uint8) == ord('1')).astype(np.float32)

# Tech tracking
tech-stack:
  added:
    - rdFingerprintGenerator.GetMorganGenerator (RDKit 2025 non-deprecated API)
    - DataStructs.BulkTanimotoSimilarity (C++ all-pairs, ~0.4s for 1788 molecules)
    - DataStructs.CreateFromBitString (reconstruct ExplicitBitVect from stored ASCII bytes)
  patterns:
    - TDD with xfail scaffold: tests pre-existed as xfail; implementation makes them xpass
    - Skip-if-exists guard in build_molecule_df for idempotent pipeline runs
    - pubchem_cache.json gate check: set(cache.keys()) == set(str(id) for id in molecules_df.pubchem_id)
    - Morgan fingerprint stored as 1024-byte ASCII bit string (fp.ToBitString().encode())
    - Phase 3 decode pattern documented at write site in build_features.py

key-files:
  created:
    - data/build_features.py
    - data/processed/molecules.parquet
    - data/processed/tanimoto_edges.parquet
  modified: []

key-decisions:
  - "Use rdFingerprintGenerator.GetMorganGenerator instead of deprecated GetMorganFingerprintAsBitVect — produces identical fingerprints, no deprecation warnings"
  - "fps_and_ids tuple order is (fp, pubchem_id) not (pubchem_id, fp) — matched to test_tanimoto_edges scaffold which uses (fp_a, 1) ordering"
  - "HBD, HBA, rotatable_bonds stored as float (not int) — RDKit Descriptors return floats; consistency with MW/logP/TPSA avoids mixed-type parquet columns"

patterns-established:
  - "Pattern: Morgan fingerprint bytes round-trip — write fp.ToBitString().encode(); reconstruct via DataStructs.CreateFromBitString(fp_bytes.decode())"
  - "Pattern: Pipeline gate check before compute — verify pubchem_cache coverage before starting RDKit loop"
  - "Pattern: All descriptor failures return null_row dict — never raise, always log WARNING with pubchem_id and common_name"

requirements-completed: [FEAT-02, FEAT-03, FEAT-04]

# Metrics
duration: 4min
completed: 2026-03-11
---

# Phase 2 Plan 03: RDKit Molecular Features Summary

**RDKit descriptor + Morgan fingerprint pipeline producing molecules.parquet (1788 rows, 9 cols) and tanimoto_edges.parquet (1678 pairs > 0.7 Tanimoto similarity) via BulkTanimotoSimilarity in ~0.4s**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-11T22:33:47Z
- **Completed:** 2026-03-11T22:37:30Z
- **Tasks:** 2
- **Files modified:** 3 (1 created + 2 parquet outputs)

## Accomplishments
- Implemented `compute_molecule_features` returning 6 RDKit descriptors + 1024-byte Morgan fingerprint per molecule; null/invalid SMILES handled gracefully
- Implemented `compute_tanimoto_edges` using `DataStructs.BulkTanimotoSimilarity` for all-pairs similarity in ~0.4s; 1678 edges above 0.7 threshold
- Ran pipeline on all 1788 molecules (0 SMILES null, 0 sanitization failures); both parquet files verified correct schema
- Added multimodal encoding stubs (`encode_texture`, `encode_temperature`, `build_cultural_context_vectors`, `build_flavor_vocab`, `encode_flavor_profile`) ready for Plan 04 expansion
- Pipeline is idempotent: second run prints `[SKIP]`

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement RDKit descriptor and Morgan fingerprint computation** - `e86113a` (feat)
2. **Task 2: Run pipeline to produce molecules.parquet and tanimoto_edges.parquet** - `572a5c1` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `data/build_features.py` - Full RDKit feature computation module with CLI, gate check, skip-if-exists, tqdm progress, pipeline log
- `data/processed/molecules.parquet` - 1788 rows x 9 columns: pubchem_id, smiles, MW, logP, HBD, HBA, rotatable_bonds, TPSA, morgan_fp_bytes
- `data/processed/tanimoto_edges.parquet` - 1678 rows x 3 columns: mol_a_pubchem_id, mol_b_pubchem_id, similarity

## Decisions Made
- **rdFingerprintGenerator over deprecated GetMorganFingerprintAsBitVect:** RDKit 2025 emits deprecation warnings for the old API. The new `GetMorganGenerator` produces identical bit vectors. Switched to eliminate warnings (Rule 2 auto-fix).
- **fps_and_ids tuple order:** Test scaffold uses `(fp, id)` ordering; implementation matches the test (not the plan description which said `(int, object)`).
- **Descriptor dtypes as float:** RDKit Descriptors return Python floats for all six measures; storing as float avoids mixed-type columns in parquet.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Switched to non-deprecated MorganGenerator API**
- **Found during:** Task 1 (descriptor computation verification)
- **Issue:** RDKit 2025 prints `DEPRECATION WARNING: please use MorganGenerator` for every call to `GetMorganFingerprintAsBitVect`. This is a forward-compatibility issue.
- **Fix:** Import `rdFingerprintGenerator`, instantiate `GetMorganGenerator(radius=2, fpSize=1024)` at module level as `_MORGAN_GEN`, use `_MORGAN_GEN.GetFingerprint(mol)` in `compute_molecule_features`. Verified same bit vectors produced (`ToBitString()` comparison confirmed equal).
- **Files modified:** `data/build_features.py`
- **Verification:** 3 Task 1 tests still pass after fix; no deprecation warnings
- **Committed in:** `e86113a` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 - forward-compatibility)
**Impact on plan:** Auto-fix eliminates noisy deprecation output without changing behavior. No scope creep.

## Issues Encountered
None. pubchem_cache.json gate check passed immediately (0 null entries as predicted by research). All 1788 FlavorDB2 SMILES parsed by RDKit without sanitization failures (confirmed by research).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `molecules.parquet` and `tanimoto_edges.parquet` ready for Phase 3 graph construction (GRAPH-06 structural similarity edges)
- `build_features.py` has multimodal stubs ready for Plan 04 expansion (texture, temperature, cultural context, flavor profile)
- Morgan fingerprint decode pattern documented in code for Phase 3 consumers

---
*Phase: 02-feature-engineering*
*Completed: 2026-03-11*

## Self-Check: PASSED

- data/build_features.py: FOUND
- data/processed/molecules.parquet: FOUND
- data/processed/tanimoto_edges.parquet: FOUND
- .planning/phases/02-feature-engineering/02-03-SUMMARY.md: FOUND
- Commit e86113a: FOUND
- Commit 572a5c1: FOUND
