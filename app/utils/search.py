"""
Search utilities for Page 1 — Ingredient Search (UI-01, UI-02).

All functions are pure (no Streamlit calls) so they can be unit-tested directly.
"""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

CATEGORIES = ["Sweet", "Sour", "Umami", "Bitter", "Floral", "Smoky"]
_CAT_KEYS = [c.lower() for c in CATEGORIES]


def get_top_pairings(query: str, pairs: list) -> list:
    """
    Return up to 10 pairs where ingredient_a matches *query* (case-insensitive),
    sorted by surprise_score descending.

    Returns [] on no match or any exception — never raises.
    """
    try:
        q = query.strip().lower()
        matches = [p for p in pairs if p.ingredient_a.lower() == q]
        matches.sort(key=lambda p: p.surprise_score, reverse=True)
        return matches[:10]
    except Exception:
        return []


def build_radar_chart(
    name_a: str,
    profile_a: dict[str, float],
    name_b: str,
    profile_b: dict[str, float],
) -> go.Figure:
    """
    Build a dual-polygon radar chart comparing two flavor profiles.

    Trace 0: name_a — filled terracotta (#c4622a).
    Trace 1: name_b — dashed sage (#4a7c4e).
    Chart is 250 px tall with a transparent background.
    """
    # Collect values; close the polygon by repeating the first value
    values_a = [profile_a.get(k, 0.0) for k in _CAT_KEYS] + [profile_a.get(_CAT_KEYS[0], 0.0)]
    values_b = [profile_b.get(k, 0.0) for k in _CAT_KEYS] + [profile_b.get(_CAT_KEYS[0], 0.0)]
    theta = CATEGORIES + [CATEGORIES[0]]

    trace_a = go.Scatterpolar(
        r=values_a,
        theta=theta,
        fill="toself",
        fillcolor="rgba(196, 98, 42, 0.2)",
        line=dict(color="#c4622a"),
        name=name_a,
    )
    trace_b = go.Scatterpolar(
        r=values_b,
        theta=theta,
        fill="toself",
        fillcolor="rgba(74, 124, 78, 0.15)",
        line=dict(color="#4a7c4e", dash="dot"),
        name=name_b,
    )

    fig = go.Figure(data=[trace_a, trace_b])
    fig.update_layout(
        height=250,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=20, b=20),
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1]),
        ),
        showlegend=True,
    )
    return fig


def format_why_it_works(molecules: list[str]) -> str:
    """
    Return a markdown string listing each shared molecule with a flavor descriptor.

    Uses a generic "aromatic" fallback when no per-molecule descriptor is available.
    Caps output at 5 molecules.
    """
    if not molecules:
        return "No shared flavor molecules found."

    lines = [
        f"- **{mol}**: contributes aromatic notes"
        for mol in molecules[:5]
    ]
    return "\n".join(lines)
