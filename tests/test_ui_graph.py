"""Tests for Page 3 — Flavor Graph Explorer (UI-04)."""
import pytest


@pytest.mark.xfail(reason="Wave 0 stub — implement in plan 06-04")
def test_build_pyvis_graph_node_count():
    """UI-04: build_pyvis_graph returns Network with at most 50 nodes."""
    from app.utils.graph import build_pyvis_graph
    assert False


@pytest.mark.xfail(reason="Wave 0 stub — implement in plan 06-04")
def test_build_pyvis_graph_center_node_largest():
    """UI-04: Center node has larger size attribute than all other nodes."""
    from app.utils.graph import build_pyvis_graph
    assert False


@pytest.mark.xfail(reason="Wave 0 stub — implement in plan 06-04")
def test_build_pyvis_graph_edge_colors():
    """UI-04: Edges with surprise_score > 0.6 are red; others are blue."""
    from app.utils.graph import build_pyvis_graph
    assert False
