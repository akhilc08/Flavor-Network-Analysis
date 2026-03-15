"""
Flavor Pairing Network — Streamlit Demo
Entry point. Run with: streamlit run app/app.py
Pages auto-discovered from app/pages/ directory.
"""
import streamlit as st
from app.utils.theme import inject_theme

st.set_page_config(
    page_title="Flavor Pairing Network",
    page_icon="🍓",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

st.title("Flavor Pairing Network")
st.markdown(
    "Discover ingredient pairings that are molecularly compatible "
    "but culinarily underexplored. Use the sidebar to navigate."
)

st.markdown("""
| Page | What it does |
|------|-------------|
| **Search** | Find the top 10 molecular pairings for any ingredient |
| **Rate** | Rate uncertain pairs to improve the model |
| **Graph** | Explore the flavor network visually |
| **Recipe** | Generate an AI recipe with molecular rationale |
""")
