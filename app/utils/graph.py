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


def build_pyvis_graph(center_name: str, pairs, ingredients=None) -> Network:
    """
    Build a PyVis Network centered on center_name.
    Returns Network with <= 50 nodes.

    pairs:       pandas DataFrame with integer ingredient_id columns
    ingredients: pandas DataFrame with columns [ingredient_id, name]
    """
    import pandas as pd

    net = Network(
        height="600px",
        width="100%",
        bgcolor="#fdf6ec",
        font_color="#2d1b0e",
    )
    net.set_options(PHYSICS_OPTIONS)

    if isinstance(pairs, pd.DataFrame) and ingredients is not None:
        id_to_name = dict(zip(ingredients["ingredient_id"], ingredients["name"]))
        name_to_id = {name.lower(): ing_id for ing_id, name in id_to_name.items()}

        ing_id = name_to_id.get(center_name.lower())
        if ing_id is None:
            return net

        mask_a = pairs["ingredient_a"] == ing_id
        mask_b = pairs["ingredient_b"] == ing_id

        df_a = pairs[mask_a].copy()
        df_a["partner_id"] = df_a["ingredient_b"]
        df_b = pairs[mask_b].copy()
        df_b["partner_id"] = df_b["ingredient_a"]

        top = (
            pd.concat([df_a, df_b])
            .sort_values("pairing_score", ascending=False)
            .head(49)
        )

        net.add_node(
            center_name,
            size=40,
            color={"background": "#c4622a", "border": "#8a3a10"},
            label=center_name.title(),
            title=f"Center: {center_name.title()}",
            font={"size": 16, "bold": True},
        )

        for row in top.itertuples(index=False):
            partner_name = id_to_name.get(row.partner_id, str(row.partner_id))
            node_size = 10 + row.pairing_score * 20
            edge_color = "#d62728" if row.surprise_score > 0.6 else "#1f77b4"
            net.add_node(
                partner_name,
                size=node_size,
                color={"background": "#fff8f0", "border": "#e8d5bc"},
                label=partner_name.title(),
                title=(
                    f"{partner_name.title()}\n"
                    f"Pairing: {row.pairing_score:.3f}\n"
                    f"Surprise: {row.surprise_score:.3f}\n"
                    f"Label: {row.label}"
                ),
            )
            net.add_edge(
                center_name,
                partner_name,
                color={"color": edge_color, "opacity": 0.8},
                width=1 + row.surprise_score * 2,
            )
        return net

    # Fallback: list of objects with string names
    relevant = [
        p for p in pairs
        if getattr(p, "ingredient_a", "").lower() == center_name.lower()
    ]
    top_pairs = sorted(relevant, key=lambda p: getattr(p, "pairing_score", 0), reverse=True)[:49]

    net.add_node(
        center_name,
        size=40,
        color={"background": "#c4622a", "border": "#8a3a10"},
        label=center_name.title(),
        title=f"Center: {center_name.title()}",
        font={"size": 16, "bold": True},
    )
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
            center_name, pair.ingredient_b,
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
