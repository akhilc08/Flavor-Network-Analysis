"""Tests for Page 3 — Flavor Graph Explorer (UI-04)."""
import pytest
from types import SimpleNamespace


def _make_pairs(center="strawberry", n=60):
    """Create n mock pair objects for center ingredient."""
    import random
    random.seed(42)
    return [
        SimpleNamespace(
            ingredient_a=center,
            ingredient_b=f"ingredient_{i}",
            pairing_score=random.uniform(0.1, 0.9),
            surprise_score=random.uniform(0.0, 1.0),
            label="Surprising" if random.random() > 0.5 else "Classic",
        )
        for i in range(n)
    ]


def test_build_pyvis_graph_node_count():
    """UI-04: Graph has at most 50 nodes."""
    from app.utils.graph import build_pyvis_graph
    pairs = _make_pairs(n=60)
    net = build_pyvis_graph("strawberry", pairs)
    assert len(net.nodes) <= 50


def test_build_pyvis_graph_center_node_largest():
    """UI-04: Center node size (40) is larger than all pair nodes (10-30)."""
    from app.utils.graph import build_pyvis_graph
    pairs = _make_pairs(n=10)
    net = build_pyvis_graph("strawberry", pairs)
    center = next(n for n in net.nodes if n["id"] == "strawberry")
    others = [n for n in net.nodes if n["id"] != "strawberry"]
    assert center["size"] >= max(n["size"] for n in others)


def test_build_pyvis_graph_edge_colors():
    """UI-04: Edges with surprise_score > 0.6 have red color; others blue."""
    from app.utils.graph import build_pyvis_graph
    pairs = [
        SimpleNamespace(
            ingredient_a="strawberry", ingredient_b="vanilla",
            pairing_score=0.8, surprise_score=0.9, label="Surprising"
        ),
        SimpleNamespace(
            ingredient_a="strawberry", ingredient_b="tomato",
            pairing_score=0.7, surprise_score=0.3, label="Classic"
        ),
    ]
    net = build_pyvis_graph("strawberry", pairs)
    edge_map = {e["to"]: e["color"]["color"] for e in net.edges}
    assert edge_map["vanilla"] == "#d62728"
    assert edge_map["tomato"] == "#1f77b4"
