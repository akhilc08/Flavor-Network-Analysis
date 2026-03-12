---
phase: 4
slug: model-training
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/ (existing scaffold from Phase 1) |
| **Quick run command** | `pytest tests/test_model.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds (smoke tests only — no training run) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_model.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | MODEL-01 | unit stub | `pytest tests/test_model.py::test_model_stub -x -q` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | MODEL-01, MODEL-02 | unit | `pytest tests/test_model.py::test_gat_forward -x -q` | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 1 | MODEL-03 | unit | `pytest tests/test_model.py::test_batchnorm_dropout -x -q` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 1 | MODEL-04, MODEL-05 | unit | `pytest tests/test_model.py::test_loss_components -x -q` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 1 | MODEL-06 | unit | `pytest tests/test_model.py::test_infonce_loss -x -q` | ❌ W0 | ⬜ pending |
| 4-02-03 | 02 | 1 | MODEL-07 | unit | `pytest tests/test_model.py::test_combined_loss -x -q` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 2 | MODEL-08 | integration | `pytest tests/test_model.py::test_training_loop_smoke -x -q` | ❌ W0 | ⬜ pending |
| 4-03-02 | 03 | 2 | MODEL-08 | manual | See manual verifications | N/A | ⬜ pending |
| 4-04-01 | 04 | 2 | MODEL-09 | unit | `pytest tests/test_model.py::test_embedding_export -x -q` | ❌ W0 | ⬜ pending |
| 4-04-02 | 04 | 2 | MODEL-09 | unit | `pytest tests/test_model.py::test_auc_gate -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_model.py` — stubs for MODEL-01 through MODEL-09
- [ ] `tests/conftest.py` — shared fixtures (tiny synthetic HeteroData graph for unit tests, no real data required)

*Wave 0 creates all test stubs before any implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Training completes 200 epochs without OOM on M2 MPS | MODEL-08 | Requires real graph from Phase 3 and full training run (~hours on CPU) | Run `python model/train_gat.py`; confirm no RuntimeError; check logs/training_metrics.csv has 200 rows |
| AUC >= 0.70 achieved | MODEL-08 | Depends on actual data quality from Phases 1-3 | Check console output or training_metrics.csv for best_auc >= 0.70 |
| Checkpoint resumes correctly | MODEL-08 | Stateful behavior hard to test in unit | Run training 10 epochs, interrupt, resume with `--resume`, verify epoch counter continues |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
