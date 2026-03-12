---
phase: 2
slug: feature-engineering
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.4.4 |
| **Config file** | none — Wave 0 installs test file, no pytest.ini needed |
| **Quick run command** | `conda run -n flavor-network python -m pytest tests/test_features.py -x -q` |
| **Full suite command** | `conda run -n flavor-network python -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `conda run -n flavor-network python -m pytest tests/test_features.py -x -q`
- **After every plan wave:** Run `conda run -n flavor-network python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 0 | FEAT-01..09 | unit/integration | `pytest tests/test_features.py -x -q` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 1 | FEAT-01 | unit | `pytest tests/test_features.py::test_smiles_cache_coverage -x` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 1 | FEAT-01 | unit | `pytest tests/test_features.py::test_smiles_missing_logged -x` | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 2 | FEAT-02 | unit | `pytest tests/test_features.py::test_rdkit_descriptors -x` | ❌ W0 | ⬜ pending |
| 2-03-02 | 03 | 2 | FEAT-02 | unit | `pytest tests/test_features.py::test_rdkit_sanitization_logged -x` | ❌ W0 | ⬜ pending |
| 2-03-03 | 03 | 2 | FEAT-03 | unit | `pytest tests/test_features.py::test_morgan_fingerprint -x` | ❌ W0 | ⬜ pending |
| 2-03-04 | 03 | 2 | FEAT-04 | unit | `pytest tests/test_features.py::test_tanimoto_edges -x` | ❌ W0 | ⬜ pending |
| 2-04-01 | 04 | 2 | FEAT-05 | unit | `pytest tests/test_features.py::test_texture_encoding -x` | ❌ W0 | ⬜ pending |
| 2-04-02 | 04 | 2 | FEAT-06 | unit | `pytest tests/test_features.py::test_temperature_encoding -x` | ❌ W0 | ⬜ pending |
| 2-04-03 | 04 | 2 | FEAT-07 | unit | `pytest tests/test_features.py::test_cultural_context -x` | ❌ W0 | ⬜ pending |
| 2-04-04 | 04 | 2 | FEAT-08 | unit | `pytest tests/test_features.py::test_flavor_profile_vocab -x` | ❌ W0 | ⬜ pending |
| 2-04-05 | 04 | 2 | FEAT-09 | integration | `pytest tests/test_features.py::test_parquet_outputs_exist -x` | ❌ W0 | ⬜ pending |
| 2-04-06 | 04 | 2 | FEAT-09 | integration | `pytest tests/test_features.py::test_molecules_parquet_schema -x` | ❌ W0 | ⬜ pending |
| 2-04-07 | 04 | 2 | FEAT-09 | integration | `pytest tests/test_features.py::test_ingredients_parquet_schema -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_features.py` — stub tests for FEAT-01 through FEAT-09 (all test functions defined, marked xfail until implementation)
- [ ] No pytest.ini needed — pytest discovers tests/ by default

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Morgan fp bytes decode correctly in Phase 3 | FEAT-03 | Cross-phase contract; can't assert until Phase 3 exists | Load molecules.parquet, decode morgan_fp_bytes with `(np.frombuffer(fp_bytes, dtype=np.uint8) == ord('1')).astype(np.float32)`, verify shape (1024,) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
