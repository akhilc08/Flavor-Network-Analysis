"""
Shared cache layer for Streamlit app.
Use @st.cache_resource for heavy objects (loaded once per process).
Call invalidate_scored_pairs() after active learning fine-tune completes.

Anti-patterns to avoid (from RESEARCH.md):
- Do NOT call st.cache_resource.clear() — clears ALL caches
- Do NOT use @st.cache_data for model objects (pickles on every read)
- Do NOT mutate objects returned by these functions (treat as read-only)
"""
from __future__ import annotations
import pickle
from pathlib import Path

import streamlit as st

SCORED_PAIRS_PATH = Path("scoring/scored_pairs.pkl")
EMBEDDINGS_PATH = Path("model/embeddings/ingredient_embeddings.pkl")


@st.cache_resource
def load_scored_pairs_cached():
    """Load scored pairs from disk. Returns None if file not found."""
    if not SCORED_PAIRS_PATH.exists():
        return None
    with open(SCORED_PAIRS_PATH, "rb") as f:
        return pickle.load(f)


@st.cache_resource
def load_embeddings_cached():
    """Load ingredient embeddings dict. Returns None if file not found."""
    if not EMBEDDINGS_PATH.exists():
        return None
    with open(EMBEDDINGS_PATH, "rb") as f:
        return pickle.load(f)


def invalidate_scored_pairs() -> None:
    """Clear scored_pairs cache. Call after active learning fine-tune completes."""
    load_scored_pairs_cached.clear()


def require_scored_pairs():
    """
    Load scored pairs or stop page rendering with friendly error.
    Returns the scored pairs list. Never returns None.
    Use: pairs = require_scored_pairs()
    """
    pairs = load_scored_pairs_cached()
    if pairs is None:
        st.warning(
            "Scored pairs not found. Run the pipeline first:\n\n"
            "```\npython run_pipeline.py\n```"
        )
        st.stop()
    return pairs
