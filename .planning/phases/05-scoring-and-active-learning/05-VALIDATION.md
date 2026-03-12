---
phase: 5
slug: scoring-and-active-learning
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.* (already installed, see requirements.txt) |
| **Config file** | none — pytest discovers `tests/` directory by convention |
| **Quick run command** | `pytest tests/test_scoring.py tests/test_active_learning.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds (unit tests use synthetic data; integration tests skip if Phase 4 artifacts missing) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_scoring.py tests/test_active_learning.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 0 | SCORE-01, SCORE-02, SCORE-04, LEARN-01, LEARN-02, LEARN-03, LEARN-05, LEARN-06 | unit stubs | `pytest tests/test_scoring.py tests/test_active_learning.py -x -q` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 0 | SCORE-03, LEARN-04 | integration stubs | `pytest tests/test_scoring.py::test_scored_pairs_file tests/test_active_learning.py::test_checkpoint_and_rescore -x -q` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 1 | SCORE-01, SCORE-02, SCORE-03, SCORE-04 | unit + integration | `pytest tests/test_scoring.py -x -q` | ❌ W0 | ⬜ pending |
| 5-03-01 | 03 | 2 | LEARN-01, LEARN-02, LEARN-03, LEARN-04, LEARN-05, LEARN-06 | unit + integration | `pytest tests/test_active_learning.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_scoring.py` — stubs for SCORE-01, SCORE-02, SCORE-03, SCORE-04, LEARN-02
- [ ] `tests/test_active_learning.py` — stubs for LEARN-01, LEARN-03, LEARN-04, LEARN-05, LEARN-06
- [ ] `scoring/__init__.py` — empty init to make scoring importable as package
- [ ] `scoring/score.py` — stub with public API signatures
- [ ] `model/active_learning.py` — stub with public API signatures
- [ ] Verify `graph/val_edges.pt` exists (Phase 4 boundary check)
- [ ] Verify `model/training_metadata.json` exists with `best_val_auc` key

*All unit tests use synthetic data (3–5 ingredients, fabricated embeddings as random tensors). Integration tests use `pytest.mark.skipif` to skip unless Phase 4 artifacts exist.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `scored_pairs.pkl` label distribution is reasonable (not 99% "Classic") | SCORE-04 | Distribution depends on real embedding quality; thresholds may need tuning | After scoring: `import pickle; df=pickle.load(open('scoring/scored_pairs.pkl','rb')); print(df['label'].value_counts())` — flag if any label is >80% |
| MPS memory does not accumulate during repeated `submit_rating()` calls | LEARN-03 | Memory profiling required; no automated fixture | Call `submit_rating()` 5 times in a loop; verify `mps_driver_allocated_memory` stays stable in Activity Monitor |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
