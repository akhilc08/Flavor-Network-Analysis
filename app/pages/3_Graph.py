"""Page 3 — Flavor Graph Explorer (UI-04)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import streamlit.components.v1 as components
from utils.theme import inject_theme
from utils.cache import require_scored_pairs, require_ingredients
from utils.graph import build_pyvis_graph, get_graph_html

inject_theme()

# Editorial page header
st.markdown(
    """
    <div style="margin-bottom:24px">
      <h1 style="font-family:Georgia,serif;font-size:32px;font-weight:400;color:#2d1b0e;margin-bottom:4px">
        Flavor Graph Explorer
      </h1>
      <p style="font-family:system-ui;font-size:13px;color:#7a5c42;letter-spacing:0.02em;margin:0">
        Network visualization &middot; Up to 50 nodes per ingredient
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<p style="font-family:system-ui;font-size:13px;color:#7a5c42;line-height:1.6;'
    'max-width:680px;margin-bottom:20px">'
    "Each node is an ingredient. Edge width reflects surprise score \u2014 thicker edges are "
    "more unexpected pairings. "
    '<span style="color:#c4622a;font-weight:600">Terracotta edges</span> are surprising; '
    '<span style="color:#1f77b4;font-weight:600">blue edges</span> are expected. '
    "Click any node to highlight it. Use the dropdown to re-center the graph."
    "</p>",
    unsafe_allow_html=True,
)

# DESIGN NOTE (from RESEARCH.md Pitfall 1):
# PyVis click events do NOT communicate back to Python via st.components.v1.html.
# The "click to pivot" behavior is implemented via st.selectbox below.
# Clicking a node provides vis.js visual highlighting only.

try:
    pairs = require_scored_pairs()
    ingredients = require_ingredients()

    all_ingredients = sorted(ingredients["name"].tolist())

    if not all_ingredients:
        st.warning("No ingredient data available. Run the pipeline first.")
        st.stop()

    selected = st.selectbox(
        "CENTER INGREDIENT",
        all_ingredients,
        key="graph_center",
        help="Select an ingredient to center the flavor graph on it.",
    )

    if selected:
        with st.spinner(f"Building graph for {selected.title()}\u2026"):
            net = build_pyvis_graph(selected, pairs, ingredients)
            html_content = get_graph_html(net)

        node_count = len(net.nodes)
        edge_count = len(net.edges)

        # Editorial metrics row
        st.markdown(
            f"""
            <div style="display:flex;gap:40px;margin:16px 0 20px;padding:16px 24px;
                        background:#fff8f0;border:1px solid #e8d5bc;border-radius:4px;
                        box-shadow:0 2px 8px rgba(45,27,14,0.05)">
              <div>
                <div style="font-family:system-ui;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#7a5c42;margin-bottom:2px">Center</div>
                <div style="font-family:Georgia,serif;font-size:20px;color:#c4622a">{selected.title()}</div>
              </div>
              <div>
                <div style="font-family:system-ui;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#7a5c42;margin-bottom:2px">Nodes</div>
                <div style="font-family:Georgia,serif;font-size:20px;color:#2d1b0e">{node_count}</div>
              </div>
              <div>
                <div style="font-family:system-ui;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#7a5c42;margin-bottom:2px">Edges</div>
                <div style="font-family:Georgia,serif;font-size:20px;color:#2d1b0e">{edge_count}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Render PyVis HTML in iframe component
        # Height in Network constructor (600px) + buffer = 620 in components.html
        components.html(html_content, height=620, scrolling=False)

except Exception as e:
    st.error(f"Something went wrong loading the flavor graph. ({type(e).__name__})")
    st.stop()
