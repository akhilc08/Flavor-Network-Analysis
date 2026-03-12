"""
Phase 3 graph construction test stubs.

All tests that require graph/hetero_data.pt skip automatically until the
artifact is built by graph/build_graph.py. test_validation_gate skips only
if graph.build_graph cannot be imported.

GRAPH-01 through GRAPH-09 requirement coverage.
"""

import os

import pytest

PT_PATH = "graph/hetero_data.pt"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _load_payload():
    """Load graph/hetero_data.pt; skip if not present."""
    if not os.path.exists(PT_PATH):
        pytest.skip("graph/hetero_data.pt not found — run graph/build_graph.py first")
    import torch  # noqa: PLC0415
    return torch.load(PT_PATH, weights_only=False)


# ---------------------------------------------------------------------------
# GRAPH-01: graph loads with expected keys and node types
# ---------------------------------------------------------------------------


def test_graph_loads():
    """GRAPH-01: Payload has required keys and both node types present."""
    payload = _load_payload()
    import torch  # noqa: PLC0415

    assert "graph" in payload, "key 'graph' missing from payload"
    assert "ingredient_id_to_idx" in payload, "key 'ingredient_id_to_idx' missing"
    assert "molecule_id_to_idx" in payload, "key 'molecule_id_to_idx' missing"

    train_data = payload["graph"]
    assert "ingredient" in train_data.node_types, "'ingredient' not in node_types"
    assert "molecule" in train_data.node_types, "'molecule' not in node_types"


# ---------------------------------------------------------------------------
# GRAPH-02: ingredient feature matrix
# ---------------------------------------------------------------------------


def test_ingredient_features():
    """GRAPH-02: Ingredient feature matrix is float32 with shape >= (500, 1)."""
    payload = _load_payload()
    import torch  # noqa: PLC0415
    data = payload["graph"]
    x = data["ingredient"].x

    assert x.dtype == torch.float32, f"Expected float32, got {x.dtype}"
    assert x.dim() == 2, f"Expected 2-D tensor, got {x.dim()}-D"
    assert x.shape[0] >= 500, f"Expected >= 500 ingredient nodes, got {x.shape[0]}"
    assert x.shape[1] > 0, "Feature dimension must be > 0"


# ---------------------------------------------------------------------------
# GRAPH-03: molecule feature matrix
# ---------------------------------------------------------------------------


def test_molecule_features():
    """GRAPH-03: Molecule feature matrix is float32, shape >= (1500, 1030)."""
    payload = _load_payload()
    import torch  # noqa: PLC0415
    data = payload["graph"]
    x = data["molecule"].x

    assert x.dtype == torch.float32, f"Expected float32, got {x.dtype}"
    assert x.dim() == 2, f"Expected 2-D tensor, got {x.dim()}-D"
    assert x.shape[0] >= 1500, f"Expected >= 1500 molecule nodes, got {x.shape[0]}"
    assert x.shape[1] == 1030, (
        f"Expected 1030 features (6 descriptors + 1024 Morgan bits), got {x.shape[1]}"
    )


# ---------------------------------------------------------------------------
# GRAPH-04: ingredient→molecule 'contains' edges
# ---------------------------------------------------------------------------


def test_contains_edges():
    """GRAPH-04: contains edges are valid and all weights positive."""
    payload = _load_payload()
    data = payload["graph"]

    edge_store = data["ingredient", "contains", "molecule"]
    edge_index = edge_store.edge_index
    edge_attr = edge_store.edge_attr

    assert edge_index.shape[0] == 2, "edge_index must be shape (2, E)"
    assert edge_index.shape[1] > 0, "No contains edges found"
    assert edge_index[0].max() < data["ingredient"].num_nodes, (
        "Source index out of range for ingredient nodes"
    )
    assert edge_index[1].max() < data["molecule"].num_nodes, (
        "Dest index out of range for molecule nodes"
    )
    assert (edge_attr > 0).all(), "All contains edge weights must be positive"


# ---------------------------------------------------------------------------
# GRAPH-05: ingredient↔ingredient 'co_occurs' edges
# ---------------------------------------------------------------------------


def test_cooccurs_edges():
    """GRAPH-05: co_occurs edges normalized in [0, 1] and within node range."""
    payload = _load_payload()
    data = payload["graph"]

    edge_store = data["ingredient", "co_occurs", "ingredient"]
    edge_index = edge_store.edge_index
    edge_attr = edge_store.edge_attr

    assert edge_index.shape[0] == 2, "edge_index must be shape (2, E)"
    assert edge_index.shape[1] > 0, "No co_occurs edges found"
    assert (edge_attr >= 0).all() and (edge_attr <= 1).all(), (
        "co_occurs weights must be normalized to [0, 1]"
    )
    assert edge_index[0].max() < data["ingredient"].num_nodes, (
        "Source index out of range"
    )
    assert edge_index[1].max() < data["ingredient"].num_nodes, (
        "Dest index out of range"
    )


# ---------------------------------------------------------------------------
# GRAPH-06: molecule↔molecule 'structurally_similar' edges
# ---------------------------------------------------------------------------


def test_structural_edges():
    """GRAPH-06: structural similarity edges have Tanimoto > 0.7."""
    payload = _load_payload()
    data = payload["graph"]

    edge_store = data["molecule", "structurally_similar", "molecule"]
    edge_index = edge_store.edge_index
    edge_attr = edge_store.edge_attr

    assert edge_index.shape[0] == 2, "edge_index must be shape (2, E)"
    assert edge_index.shape[1] > 0, "No structurally_similar edges found"
    assert (edge_attr > 0.7).all(), (
        f"All structural edges must have Tanimoto > 0.7; min found: {edge_attr.min():.4f}"
    )


# ---------------------------------------------------------------------------
# GRAPH-07: validation gate raises ValueError on trivial graph
# ---------------------------------------------------------------------------


def test_validation_gate():
    """GRAPH-07: validation gate raises ValueError when thresholds not met."""
    from graph.build_graph import run_validation_gate  # noqa: PLC0415
    from torch_geometric.data import HeteroData  # noqa: PLC0415
    import torch  # noqa: PLC0415
    data = HeteroData()
    data['ingredient'].num_nodes = 10  # below 500 threshold
    # No edges — will also fail edge type checks
    with pytest.raises(ValueError, match="validation gate failed"):
        run_validation_gate(data)


# ---------------------------------------------------------------------------
# GRAPH-08: no train/test leakage in co_occurs edges
# ---------------------------------------------------------------------------


def test_no_leakage():
    """GRAPH-08: test positive edges do not appear in the training edge set."""
    payload = _load_payload()

    if "test_data" not in payload:
        pytest.skip("payload missing 'test_data' key — not yet produced by build_graph.py")

    train_data = payload["graph"]
    test_data = payload["test_data"]

    train_edge_index = train_data["ingredient", "co_occurs", "ingredient"].edge_index
    train_pairs = set(
        zip(train_edge_index[0].tolist(), train_edge_index[1].tolist())
    )

    test_store = test_data["ingredient", "co_occurs", "ingredient"]
    test_edge_label_index = test_store.edge_label_index
    test_edge_label = test_store.edge_label

    # Positive test edges only (label == 1)
    pos_mask = test_edge_label == 1
    pos_edges = test_edge_label_index[:, pos_mask]

    leaks = []
    for i in range(pos_edges.shape[1]):
        s = pos_edges[0, i].item()
        d = pos_edges[1, i].item()
        if (s, d) in train_pairs or (d, s) in train_pairs:
            leaks.append((s, d))

    assert len(leaks) == 0, (
        f"Found {len(leaks)} test positive edges leaking into training set: {leaks[:5]}"
    )


# ---------------------------------------------------------------------------
# GRAPH-09: saved artifact has all required keys on disk
# ---------------------------------------------------------------------------


def test_saved_artifact():
    """GRAPH-09: Persisted artifact has correct structure and index maps."""
    if not os.path.exists(PT_PATH):
        pytest.skip("graph/hetero_data.pt not found — run graph/build_graph.py first")
    if not os.path.exists("graph/index_maps.json"):
        pytest.skip("graph/index_maps.json not found — run graph/build_graph.py first")

    import torch  # noqa: PLC0415

    payload = torch.load(PT_PATH, weights_only=False)

    for key in ("graph", "val_data", "test_data", "ingredient_id_to_idx", "molecule_id_to_idx"):
        assert key in payload, f"Required key '{key}' missing from payload"

    assert isinstance(payload["ingredient_id_to_idx"], dict), (
        "ingredient_id_to_idx must be a dict"
    )
    assert isinstance(payload["molecule_id_to_idx"], dict), (
        "molecule_id_to_idx must be a dict"
    )
