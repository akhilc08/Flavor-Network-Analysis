---
phase: 03-graph-construction
verified: 2026-03-12T08:00:00Z
status: human_needed
score: 9/9 must-haves verified
re_verification: false
human_verification:
  - test: "Confirm graph/hetero_data.pt loads correctly end-to-end in a Phase 4 context"
    expected: "All 5 keys accessible; train_data can be fed into a HeteroConv forward pass without shape errors"
    why_human: "Graph is structurally valid per tests, but downstream GNN compatibility (HeteroConv with these exact edge types and feature dims) requires a real forward pass to confirm"
  - test: "Inspect logs/pipeline.log after a fresh run of python run_pipeline.py --skip-scrape --skip-foodb --skip-recipes --skip-smiles --skip-features"
    expected: "'[SKIP] Graph construction — graph/hetero_data.pt already exists' appears; no import errors for graph.build_graph"
    why_human: "Cannot invoke run_pipeline.py end-to-end in this environment; wiring is verified by code inspection but live orchestrator execution should be confirmed once"
  - test: "Confirm GRAPH-07 molecule node threshold (1500 actual vs 2000 in REQUIREMENTS.md) is an accepted product decision"
    expected: "Team confirms 1,788 molecules from FlavorDB2 is sufficient and REQUIREMENTS.md should be updated to >=1500 (or coverage matches Phase 2 data reality)"
    why_human: "This is a product/scope decision. The current threshold is 1500 (matching actual data), but REQUIREMENTS.md still says 2000. A human must either update REQUIREMENTS.md or re-examine data coverage."
---

# Phase 3: Graph Construction Verification Report

**Phase Goal:** Build a heterogeneous graph (HeteroData) from processed parquets, with ingredient and molecule nodes, three edge types (contains, co_occurs, structurally_similar), and a validated train/val/test split saved to disk.
**Verified:** 2026-03-12T08:00:00Z
**Status:** human_needed (all automated checks pass; 3 items need human confirmation)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | HeteroData built with ingredient and molecule nodes | VERIFIED | 935 ingredient + 1,788 molecule nodes confirmed via torch.load inspection |
| 2 | Three edge types present: contains, co_occurs, structurally_similar | VERIFIED | `train.edge_types` = all 3; counts: 60,208 / 27,912 / 3,195,156 |
| 3 | Ingredient node features are float32 [N, D] | VERIFIED | shape (935, 1641), dtype float32 |
| 4 | Molecule node features are float32 [N, 1030] | VERIFIED | shape (1788, 1030), dtype float32 — 6 descriptors + 1024 Morgan bits |
| 5 | Contains edge weights all positive | VERIFIED | test_contains_edges passes; weight=1.0 fallback when no concentration |
| 6 | Co-occurs edge weights normalized to [0, 1] | VERIFIED | test_cooccurs_edges passes |
| 7 | Structural edges all have Tanimoto > 0.7 | VERIFIED | test_structural_edges passes |
| 8 | Validation gate raises ValueError on insufficient graph | VERIFIED | test_validation_gate passes unconditionally |
| 9 | Train/val/test split with zero leakage saved to disk | VERIFIED | test_no_leakage + test_saved_artifact both pass; leakage assertion in build_graph() runs before torch.save |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graph/build_graph.py` | Standalone graph builder with all functions | VERIFIED | 884 lines; all required exports importable; no TODO stubs in build_graph() |
| `graph/hetero_data.pt` | Torch payload with 5 keys | VERIFIED | 77 MB; keys: graph, val_data, test_data, ingredient_id_to_idx, molecule_id_to_idx |
| `graph/index_maps.json` | Human-readable index sidecar | VERIFIED | 47 KB; JSON with both maps |
| `tests/test_graph.py` | 9 test functions covering all GRAPH requirements | VERIFIED | 9/9 pass; no skips |
| `run_pipeline.py` | Stage 4 graph construction wired with skip-if-exists | VERIFIED | from graph.build_graph import build_graph present; skip-if-exists logic at line 316 |
| `data/processed/ingredient_molecule.parquet` | 60,208 ingredient-molecule links | VERIFIED | exists; used as authoritative contains-edge source |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `build_graph.py` | `data/processed/*.parquet` | `pandas.read_parquet` | WIRED | Line 176, 182 |
| `build_graph.py` | `logs/pipeline.log` | `logging.FileHandler` | WIRED | Line 40 |
| `_build_cooccurs_edges` | `name_to_ingredient_idx` | `.lower().strip()` normalization | WIRED | Lines 519-520 |
| `_build_structural_edges` | `DataStructs.BulkTanimotoSimilarity` | lower-triangle loop with tqdm | WIRED | Line 609 |
| `build_graph()` | `run_validation_gate()` | called before RandomLinkSplit | WIRED | Lines 796-803 (data.validate first, then run_validation_gate) |
| `build_graph()` | `RandomLinkSplit` | PyG transform on HeteroData | WIRED | Lines 809-818 |
| `build_graph()` | leakage assertion | `leakage_count == 0` before torch.save | WIRED | Lines 835-843 |
| `run_pipeline.py` | `graph.build_graph.build_graph` | direct function import | WIRED | Line 86 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| GRAPH-01 | 03-01, 03-02, 03-04 | HeteroData built manually with explicit index dicts | SATISFIED | ingredient_id_to_idx and molecule_id_to_idx dicts in payload; HeteroData not from_networkx() |
| GRAPH-02 | 03-01, 03-02 | Ingredient features = multimodal + mean-pooled Morgan fps | SATISFIED | shape (935, 1641): 617 multimodal cols + 1024 Morgan bits; test passes |
| GRAPH-03 | 03-01, 03-02 | Molecule features = RDKit descriptors + Morgan fps | SATISFIED | shape (1788, 1030) = 6 descriptors + 1024 bits; test passes |
| GRAPH-04 | 03-01, 03-03 | Contains edges with FooDB concentration weight | SATISFIED | 60,208 edges; 1.0 fallback used; all weights positive; test passes |
| GRAPH-05 | 03-01, 03-03 | Co-occurs edges with normalized count weight | SATISFIED | 27,912 train edges; weights in [0,1]; test passes |
| GRAPH-06 | 03-01, 03-03 | Structural similarity edges Tanimoto > 0.7 | SATISFIED | 3,195,156 edges; undirected (fwd+rev); test passes |
| GRAPH-07 | 03-01, 03-02, 03-04 | Validation gate blocks training if thresholds not met | SATISFIED with NOTE | Gate raises ValueError on insufficient graph (test passes). HOWEVER: REQUIREMENTS.md specifies ">=2000 molecule nodes" but implementation uses 1500. Actual count is 1788. Threshold was deliberately lowered to match FlavorDB2 coverage (documented in 03-04-SUMMARY.md). REQUIREMENTS.md has not been updated. |
| GRAPH-08 | 03-01, 03-04 | Train/val/test split with zero test-edge leakage | SATISFIED | RandomLinkSplit 70/15/15 on co_occurs; leakage assertion in code; test_no_leakage passes |
| GRAPH-09 | 03-01, 03-04 | Graph saved to graph/hetero_data.pt | SATISFIED | File exists (77 MB); all 5 keys present; graph/index_maps.json also exists |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `graph/build_graph.py` | 260 | "using [N, 1] zero placeholder" | Info | Text in a log warning string (not a code stub); fires only when no multimodal feature columns found, which does not occur with actual data |

No blocker or warning anti-patterns found. The one match is a warning message string, not a stub implementation.

### Requirements Threshold Discrepancy

**GRAPH-07 vs REQUIREMENTS.md:**

- REQUIREMENTS.md (line 44): ">=2000 molecule nodes"
- `run_validation_gate()` in code (line 655): `check("Molecule nodes", n_mol, 1500)`
- `test_molecule_features` (line 82): `assert x.shape[0] >= 1500`
- Actual molecule count: 1,788

The implementation deliberately uses 1500 to match actual FlavorDB2 data coverage (1,788 molecules). The decision is documented in 03-04-SUMMARY.md under "Decisions Made". However, REQUIREMENTS.md still reads ">= 2000 molecule nodes" and has not been updated. This is a documentation gap, not a code failure — the system works correctly with real data. A human must confirm whether to update REQUIREMENTS.md to >=1500 or to note coverage as intentionally reduced.

### Human Verification Required

**1. Phase 4 GNN Forward Pass Compatibility**

**Test:** Load `graph/hetero_data.pt` and run a minimal HeteroConv forward pass using the `ingredient` and `molecule` nodes with all three edge types.
**Expected:** No shape errors; embeddings produced for both node types.
**Why human:** The graph passes all structural PyG tests, but downstream GNN compatibility with feature dims (935x1641, 1788x1030) and 3.2M structural edges must be confirmed to avoid OOM or shape mismatches in Phase 4.

**2. Live run_pipeline.py Stage 4 Skip-If-Exists**

**Test:** Run `python run_pipeline.py --skip-scrape --skip-foodb --skip-recipes --skip-smiles --skip-features` and observe output.
**Expected:** Log shows "[SKIP] Graph construction — graph/hetero_data.pt already exists" and pipeline completes without errors.
**Why human:** Stage 4 wiring is verified by code inspection but live orchestrator execution has not been confirmed in this session.

**3. GRAPH-07 Molecule Threshold Decision**

**Test:** Review whether REQUIREMENTS.md should be updated from ">=2000 molecule nodes" to ">=1500 molecule nodes" given actual FlavorDB2 coverage.
**Expected:** Team confirms the threshold change and REQUIREMENTS.md is updated to reflect actual data reality.
**Why human:** This is a product/scope decision with documentation implications — the code is correct but the requirements doc is inconsistent with implementation.

### Gaps Summary

No blocking gaps. All 9 tests pass. All artifacts exist and are substantive. All key links are wired. Three items require human confirmation:

1. Phase 4 GNN forward pass compatibility (can't verify without running the full model).
2. Live pipeline orchestrator execution (Stage 4 skip-if-exists behavior confirmed by code only).
3. REQUIREMENTS.md GRAPH-07 molecule threshold discrepancy (1500 in code vs 2000 in spec — deliberate decision, not documented back to REQUIREMENTS.md).

---

## Commit Verification

All commits referenced in phase summaries confirmed present in git log:

- `95d5328` — test(03-01): 9 skip-guarded stubs
- `4431021` — feat(03-02): build_graph.py node features, test_validation_gate update
- `0c32954` — feat(03-03): three edge construction functions
- `dfec4f4` — feat(03-04): full HeteroData assembly, split, assert, save
- `53c3cd4` — feat(03-04): Stage 4 wired in run_pipeline.py
- `2ca784d` — fix(03-04): ingredient_molecule.parquet + validation threshold fix

---

_Verified: 2026-03-12T08:00:00Z_
_Verifier: Claude (gsd-verifier)_
