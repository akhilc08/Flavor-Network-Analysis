---
phase: 6
slug: streamlit-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — discovered by pytest default |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-W0-01 | 01 | 0 | UI-01, UI-02 | smoke | `pytest tests/test_ui_search.py -x -q` | ❌ W0 | ⬜ pending |
| 6-W0-02 | 01 | 0 | UI-03 | smoke | `pytest tests/test_ui_rate.py -x -q` | ❌ W0 | ⬜ pending |
| 6-W0-03 | 01 | 0 | UI-04 | unit | `pytest tests/test_ui_graph.py -x -q` | ❌ W0 | ⬜ pending |
| 6-W0-04 | 01 | 0 | UI-06 | unit | `pytest tests/test_ui_cache.py -x -q` | ❌ W0 | ⬜ pending |
| 6-W0-05 | 01 | 0 | UI-07 | smoke | `pytest tests/test_ui_errors.py -x -q` | ❌ W0 | ⬜ pending |
| 6-01-01 | 01 | 1 | UI-01, UI-02 | smoke | `pytest tests/test_ui_search.py -x -q` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 1 | UI-03 | smoke | `pytest tests/test_ui_rate.py -x -q` | ❌ W0 | ⬜ pending |
| 6-01-03 | 01 | 1 | UI-04 | unit | `pytest tests/test_ui_graph.py -x -q` | ❌ W0 | ⬜ pending |
| 6-01-04 | 01 | 1 | UI-06 | unit | `pytest tests/test_ui_cache.py -x -q` | ❌ W0 | ⬜ pending |
| 6-01-05 | 01 | 1 | UI-07 | smoke | `pytest tests/test_ui_errors.py -x -q` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 2 | UI-05 | manual | N/A — requires live ANTHROPIC_API_KEY | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ui_search.py` — stubs for UI-01, UI-02 (search page utility functions)
- [ ] `tests/test_ui_rate.py` — stubs for UI-03 (rating submission, gate check)
- [ ] `tests/test_ui_graph.py` — stubs for UI-04 (graph builder: node count ≤50, edge colors)
- [ ] `tests/test_ui_cache.py` — stubs for UI-06 (cache clear after fine-tune)
- [ ] `tests/test_ui_errors.py` — stubs for UI-07 (friendly error when files missing)
- [ ] `app/utils/__init__.py` — package init for utility module imports
- [ ] Install new packages: `streamlit==1.55.*`, `plotly==5.*`, `pyvis==0.3.*`, `anthropic==0.84.*` in `environment.yml`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Recipe streams via Claude API with molecular rationale | UI-05 | Requires live ANTHROPIC_API_KEY and subjective quality review | Run app, set ANTHROPIC_API_KEY, select 2-3 ingredients, click Generate, verify recipe names compounds and includes dish with steps |
| PyVis graph click visual feedback + selectbox pivot | UI-04 | In-browser interaction; no headless click simulation for components.html iframe | Run app, open Page 3, click node in graph (should highlight), then select from dropdown to confirm re-render |
| AUC delta displayed correctly after fine-tuning | UI-03 | Requires model training round-trip | Run app, submit 5 ratings, verify st.metric shows before/after AUC with delta |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
