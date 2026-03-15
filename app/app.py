"""
Flavor Pairing Network — Streamlit Demo
Entry point. Run with: streamlit run app/app.py
Pages auto-discovered from app/pages/ directory.
"""
import streamlit as st
from utils.theme import inject_theme

st.set_page_config(
    page_title="Flavor Pairing Network",
    page_icon="🍓",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

# Editorial topbar
st.markdown(
    """
    <div style="
        height:64px;
        background:#fdf6ec;
        border-bottom:1px solid #e8d5bc;
        display:flex;
        align-items:center;
        justify-content:space-between;
        padding:0 32px;
        margin:-16px -32px 32px;
    ">
      <div>
        <span style="font-family:Georgia,serif;font-size:22px;font-weight:400;color:#2d1b0e;letter-spacing:-0.01em">
          Flavor Pairing <span style="color:#c4622a">Network</span>
        </span>
      </div>
      <div style="font-family:system-ui;font-size:12px;color:#7a5c42;letter-spacing:0.06em;text-transform:uppercase">
        Molecular gastronomy &middot; Ingredient discovery
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<h1 style="font-family:Georgia,serif;font-size:36px;font-weight:400;color:#2d1b0e;margin-bottom:8px">'
    'Discover hidden pairings</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="font-family:system-ui;font-size:14px;color:#7a5c42;line-height:1.6;max-width:600px;margin-bottom:32px">'
    'Flavor compounds are the invisible threads connecting seemingly unrelated ingredients. '
    'This tool uses a graph neural network trained on molecular co-occurrence to surface '
    'pairings that are scientifically compatible but culinarily underexplored.'
    '</p>',
    unsafe_allow_html=True,
)

# Navigation cards
st.markdown(
    """
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;max-width:800px">
      <div style="background:#fff8f0;border:1px solid #e8d5bc;border-radius:4px;padding:24px;box-shadow:0 2px 8px rgba(45,27,14,0.05)">
        <div style="font-family:system-ui;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#c4622a;margin-bottom:8px">Search</div>
        <div style="font-family:Georgia,serif;font-size:18px;color:#2d1b0e;margin-bottom:8px">Ingredient pairings</div>
        <div style="font-family:system-ui;font-size:13px;color:#7a5c42;line-height:1.5">Find the top 10 molecular pairings for any ingredient. Cards show pairing strength, surprise score, and shared flavor compounds.</div>
      </div>
      <div style="background:#fff8f0;border:1px solid #e8d5bc;border-radius:4px;padding:24px;box-shadow:0 2px 8px rgba(45,27,14,0.05)">
        <div style="font-family:system-ui;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#c4622a;margin-bottom:8px">Rate</div>
        <div style="font-family:Georgia,serif;font-size:18px;color:#2d1b0e;margin-bottom:8px">Improve the model</div>
        <div style="font-family:system-ui;font-size:13px;color:#7a5c42;line-height:1.5">Rate uncertain pairs to trigger active learning fine-tuning. Watch the AUC rise in real time.</div>
      </div>
      <div style="background:#fff8f0;border:1px solid #e8d5bc;border-radius:4px;padding:24px;box-shadow:0 2px 8px rgba(45,27,14,0.05)">
        <div style="font-family:system-ui;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#c4622a;margin-bottom:8px">Graph</div>
        <div style="font-family:Georgia,serif;font-size:18px;color:#2d1b0e;margin-bottom:8px">Flavor network</div>
        <div style="font-family:system-ui;font-size:13px;color:#7a5c42;line-height:1.5">Explore the ingredient graph visually. Red edges are surprising pairings; select any ingredient to re-center.</div>
      </div>
      <div style="background:#fff8f0;border:1px solid #e8d5bc;border-radius:4px;padding:24px;box-shadow:0 2px 8px rgba(45,27,14,0.05)">
        <div style="font-family:system-ui;font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#c4622a;margin-bottom:8px">Recipe</div>
        <div style="font-family:Georgia,serif;font-size:18px;color:#2d1b0e;margin-bottom:8px">AI recipe generation</div>
        <div style="font-family:system-ui;font-size:13px;color:#7a5c42;line-height:1.5">Pick 2–3 surprising ingredients and generate a recipe with molecular rationale written by Claude.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
