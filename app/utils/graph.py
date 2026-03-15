"""Utility for building PyVis flavor network graphs (UI-04)."""
from __future__ import annotations
import os
import tempfile

from pyvis.network import Network


PHYSICS_OPTIONS = """{
  "physics": {
    "barnesHut": {
      "gravitationalConstant": -8000,
      "centralGravity": 0.3,
      "springLength": 120
    },
    "stabilization": {"iterations": 150}
  },
  "interaction": {"hover": true, "tooltipDelay": 200}
}"""


def build_pyvis_graph(center_name: str, pairs: list) -> Network:
    """
    Build a PyVis Network centered on center_name.
    Returns Network with <= 50 nodes.
    Does NOT generate HTML — call get_graph_html(net) for that.
    """
    net = Network(
        height="600px",
        width="100%",
        bgcolor="#fdf6ec",
        font_color="#2d1b0e",
    )
    net.set_options(PHYSICS_OPTIONS)

    # Filter to pairs where this ingredient is ingredient_a
    relevant = [
        p for p in pairs
        if getattr(p, "ingredient_a", "").lower() == center_name.lower()
    ]
    # Top 49 by pairing_score (leaves room for center = 50 total)
    top_pairs = sorted(
        relevant,
        key=lambda p: getattr(p, "pairing_score", 0),
        reverse=True,
    )[:49]

    # Center node
    net.add_node(
        center_name,
        size=40,
        color={"background": "#c4622a", "border": "#8a3a10"},
        label=center_name.title(),
        title=f"Center: {center_name.title()}",
        font={"size": 16, "bold": True},
    )

    # Pair nodes and edges
    for pair in top_pairs:
        node_size = 10 + getattr(pair, "pairing_score", 0.5) * 20
        surprise = getattr(pair, "surprise_score", 0.0)
        edge_color = "#d62728" if surprise > 0.6 else "#1f77b4"

        net.add_node(
            pair.ingredient_b,
            size=node_size,
            color={"background": "#fff8f0", "border": "#e8d5bc"},
            label=pair.ingredient_b.title(),
            title=(
                f"{pair.ingredient_b.title()}\n"
                f"Pairing: {getattr(pair, 'pairing_score', 0):.3f}\n"
                f"Surprise: {surprise:.3f}\n"
                f"Label: {getattr(pair, 'label', 'Unknown')}"
            ),
        )
        net.add_edge(
            center_name,
            pair.ingredient_b,
            color={"color": edge_color, "opacity": 0.8},
            width=1 + surprise * 2,
        )

    return net


def get_graph_html(net: Network) -> str:
    """
    Generate HTML string from a PyVis Network.
    Uses generate_html() if available (pyvis 0.3.2+), else falls back to tmp file.
    """
    try:
        return net.generate_html()
    except AttributeError:
        # Fallback for older pyvis versions
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
            tmp_path = f.name
        net.save_graph(tmp_path)
        try:
            with open(tmp_path, encoding="utf-8") as f:
                return f.read()
        finally:
            os.unlink(tmp_path)
