---
phase: 3
slug: graph-construction
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed in project env, used in Phase 1) |
| **Config file** | none — run from project root |
| **Quick run command** | `pytest tests/test_graph.py -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds (graph artifact load + assertions) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_graph.py -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 0 | GRAPH-01–09 | stub | `pytest tests/test_graph.py -x -q` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 1 | GRAPH-01 | smoke | `pytest tests/test_graph.py::test_graph_loads -x` | ❌ W0 | ⬜ pending |
| 3-02-02 | 02 | 1 | GRAPH-02 | unit | `pytest tests/test_graph.py::test_ingredient_features -x` | ❌ W0 | ⬜ pending |
| 3-02-03 | 02 | 1 | GRAPH-03 | unit | `pytest tests/test_graph.py::test_molecule_features -x` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 1 | GRAPH-04 | unit | `pytest tests/test_graph.py::test_contains_edges -x` | ❌ W0 | ⬜ pending |
| 3-03-02 | 03 | 1 | GRAPH-05 | unit | `pytest tests/test_graph.py::test_cooccurs_edges -x` | ❌ W0 | ⬜ pending |
| 3-03-03 | 03 | 1 | GRAPH-06 | unit | `pytest tests/test_graph.py::test_structural_edges -x` | ❌ W0 | ⬜ pending |
| 3-04-01 | 04 | 2 | GRAPH-07 | unit | `pytest tests/test_graph.py::test_validation_gate -x` | ❌ W0 | ⬜ pending |
| 3-04-02 | 04 | 2 | GRAPH-08 | integration | `pytest tests/test_graph.py::test_no_leakage -x` | ❌ W0 | ⬜ pending |
| 3-04-03 | 04 | 2 | GRAPH-09 | smoke | `pytest tests/test_graph.py::test_saved_artifact -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_graph.py` — test stubs for GRAPH-01 through GRAPH-09 (9 test functions, all skipped until graph artifact exists)

*All other test infrastructure exists — pytest installed, `tests/__init__.py` present, no conftest needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Validation gate diagnostics table formatting | GRAPH-07 | Visual formatting check (✓/✗ symbols, column alignment) | Run `python graph/build_graph.py` with artificially low thresholds; verify table prints correctly and ValueError message is readable |
| tqdm progress bars display correctly | CONTEXT (logging) | Terminal rendering can't be asserted in pytest | Run script manually; confirm bars appear for each edge construction loop |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
