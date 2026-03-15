"""
Search utilities for Page 1 — Ingredient Search (UI-01, UI-02).

All functions are pure (no Streamlit calls) so they can be unit-tested directly.
"""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

CATEGORIES = ["Sweet", "Sour", "Umami", "Bitter", "Floral", "Smoky"]
_CAT_KEYS = [c.lower() for c in CATEGORIES]


def get_top_pairings(query: str, pairs, ingredients=None) -> list:
    """
    Return up to 10 pairs where either ingredient matches *query* (case-insensitive),
    sorted by surprise_score descending.  ingredient_b is always the partner name.

    pairs:       pandas DataFrame with integer ingredient_id columns (from scored_pairs.pkl)
    ingredients: pandas DataFrame with columns [ingredient_id, name] for name resolution
    Returns [] on no match or any exception — never raises.
    """
    try:
        import pandas as pd
        from types import SimpleNamespace

        q = query.strip().lower()

        if isinstance(pairs, pd.DataFrame) and ingredients is not None:
            # Build id <-> name maps
            id_to_name = dict(zip(ingredients["ingredient_id"], ingredients["name"]))
            name_to_id = {
                name.lower(): ing_id
                for ing_id, name in id_to_name.items()
            }

            if q not in name_to_id:
                return []

            ing_id = name_to_id[q]

            mask_a = pairs["ingredient_a"] == ing_id
            mask_b = pairs["ingredient_b"] == ing_id

            df_a = pairs[mask_a].copy()
            df_a["partner_id"] = df_a["ingredient_b"]

            df_b = pairs[mask_b].copy()
            df_b["partner_id"] = df_b["ingredient_a"]

            combined = (
                pd.concat([df_a, df_b])
                .sort_values("surprise_score", ascending=False)
                .head(10)
            )

            results = []
            for row in combined.itertuples(index=False):
                d = row._asdict()
                d["ingredient_a"] = query.strip()
                d["ingredient_b"] = id_to_name.get(d["partner_id"], str(d["partner_id"]))
                del d["partner_id"]
                d.setdefault("shared_molecules", None)
                d.setdefault("flavor_profile_a", {})
                d.setdefault("flavor_profile_b", {})
                results.append(SimpleNamespace(**d))
            return results

        # Fallback: list of objects with string names
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
    Return a prose sentence describing why these molecules make a good pairing.

    Used inside HTML cards so returns plain text (no markdown).
    Caps output at 5 molecules.
    """
    if not molecules:
        return "No shared flavor molecules found between these two ingredients."

    mol_list = ", ".join(molecules[:5])
    return (
        f"Both ingredients share the aromatic compound{'' if len(molecules) == 1 else 's'} "
        f"{mol_list} — a molecular bridge that makes this pairing work at a chemical level."
    )
