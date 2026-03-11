---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `pytest tests/test_environment.py tests/test_project_structure.py -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_environment.py tests/test_project_structure.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | ENV-01 | smoke | `pytest tests/test_environment.py::test_imports -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | ENV-02 | smoke | `pytest tests/test_environment.py::test_mps_available -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 0 | ENV-03 | smoke | `pytest tests/test_environment.py::test_versions -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 0 | ENV-04 | unit | `pytest tests/test_project_structure.py::test_directories -x` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | DATA-01 | integration | `pytest tests/test_flavordb.py::test_cache_populated -x` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | DATA-02 | unit | `pytest tests/test_flavordb.py::test_ingredients_schema -x` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 1 | DATA-03 | integration | `pytest tests/test_foodb.py::test_join_count -x` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 1 | DATA-04 | integration | `pytest tests/test_recipes.py::test_cooccurrence_count -x` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 1 | DATA-05 | integration | `pytest tests/test_allrecipes.py::test_scraper_runs -x` | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 2 | DATA-06 | unit | `pytest tests/test_outputs.py::test_output_files_exist -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — test package init
- [ ] `tests/test_environment.py` — stubs for ENV-01, ENV-02, ENV-03
- [ ] `tests/test_project_structure.py` — stubs for ENV-04
- [ ] `tests/test_flavordb.py` — stubs for DATA-01, DATA-02
- [ ] `tests/test_foodb.py` — stubs for DATA-03
- [ ] `tests/test_recipes.py` — stubs for DATA-04
- [ ] `tests/test_allrecipes.py` — stubs for DATA-05
- [ ] `tests/test_outputs.py` — stubs for DATA-06
- [ ] `pytest` install — add to environment.yml pip section

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FooDB tar.gz manually downloaded to data/raw/ | DATA-03 | 952MB archive requires user license acknowledgment (CC BY-NC 4.0) | Verify `data/raw/foodb/` exists and `ls data/raw/foodb/*.csv` returns results |
| MPS backend produces numerically correct output | ENV-02 | Hardware verification requires physical M2 chip | Run `python -c "import torch; t = torch.tensor([1.0]).to('mps'); print(t)"` — should print `tensor([1.], device='mps:0')` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
