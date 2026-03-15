"""Page 3 — Flavor Graph Explorer (UI-04)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import streamlit.components.v1 as components
from utils.theme import inject_theme
from utils.cache import require_scored_pairs
from utils.graph import build_pyvis_graph, get_graph_html

inject_theme()
st.title("Flavor Graph Explorer")
st.markdown(
    '<p class="subtext">Explore the molecular flavor network interactively</p>',
    unsafe_allow_html=True,
)

# DESIGN NOTE (from RESEARCH.md Pitfall 1):
# PyVis click events do NOT communicate back to Python via st.components.v1.html.
# The "click to pivot" behavior is implemented via st.selectbox below.
# Clicking a node in the graph provides visual highlighting only (built-in vis.js behavior).
# To pivot: user selects new ingredient from the selectbox → Streamlit reruns → graph re-centers.
st.info(
    "Click nodes in the graph for visual highlighting. "
    "To re-center the graph on a different ingredient, select it in the dropdown below."
)

try:
    pairs = require_scored_pairs()

    # Get all unique ingredient_a values as the selectable set
    all_ingredients = sorted(set(
        getattr(p, "ingredient_a", "") for p in pairs
        if getattr(p, "ingredient_a", "")
    ))

    if not all_ingredients:
        st.warning("No ingredient data available. Run the pipeline first.")
        st.stop()

    # Selectbox is the pivot control (per RESEARCH.md workaround)
    selected = st.selectbox(
        "Center ingredient",
        all_ingredients,
        key="graph_center",
        help="Select an ingredient to center the flavor graph on it.",
    )

    if selected:
        with st.spinner(f"Building graph for {selected.title()}..."):
            net = build_pyvis_graph(selected, pairs)
            html_content = get_graph_html(net)

        node_count = len(net.nodes)
        edge_count = len(net.edges)
        col1, col2, col3 = st.columns(3)
        col1.metric("Nodes", node_count)
        col2.metric("Edges", edge_count)
        col3.metric("Center", selected.title())

        st.markdown("**Edge colors:** Red = Surprising pairing | Blue = Expected pairing")

        # Render PyVis HTML in iframe component
        # Height in Network constructor (600px) + buffer = 620 in components.html
        components.html(html_content, height=620, scrolling=False)

except Exception as e:
    st.error(f"Something went wrong loading the flavor graph. ({type(e).__name__})")
    st.stop()
