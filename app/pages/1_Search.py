"""Page 1 — Ingredient Search (UI-01, UI-02)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import streamlit.components.v1 as components
from utils.theme import inject_theme
from utils.cache import require_scored_pairs, require_ingredients
from utils.search import get_top_pairings, format_why_it_works

inject_theme()

# Editorial page header
st.markdown(
    """
    <div style="margin-bottom:32px">
      <h1 style="font-family:Georgia,serif;font-size:32px;font-weight:400;color:#2d1b0e;margin-bottom:4px">
        Ingredient Search
      </h1>
      <p style="font-family:system-ui;font-size:13px;color:#7a5c42;letter-spacing:0.02em;margin:0">
        Molecular gastronomy &middot; Top 10 pairings ranked by surprise
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)


def render_cards_html(query: str, pairs: list) -> str:
    """Build complete HTML for the 2-col editorial card grid."""
    cards_html = []
    for pair in pairs:
        label = getattr(pair, "label", "Classic")
        label_lower = label.lower()
        pill_styles = {
            "surprising": (
                "background:rgba(74,124,78,0.12);color:#4a7c4e;"
                "border:1px solid rgba(74,124,78,0.25)"
            ),
            "unexpected": (
                "background:rgba(184,134,11,0.12);color:#b8860b;"
                "border:1px solid rgba(184,134,11,0.25)"
            ),
            "classic": (
                "background:rgba(196,98,42,0.1);color:#c4622a;"
                "border:1px solid rgba(196,98,42,0.25)"
            ),
        }
        pill_style = pill_styles.get(label_lower, pill_styles["classic"])

        score = getattr(pair, "pairing_score", 0.0)
        surprise = getattr(pair, "surprise_score", 0.0)
        molecules = getattr(pair, "shared_molecules", []) or []
        mol_tags = "".join(
            f'<span style="font-family:system-ui;font-size:11px;font-style:italic;'
            f'color:#7a5c42;background:#fdf6ec;border:1px solid #e8d5bc;'
            f'border-radius:2px;padding:3px 8px;margin:2px;display:inline-block">{m}</span>'
            for m in molecules[:5]
        )
        why = format_why_it_works(molecules[:5])
        name = getattr(pair, "ingredient_b", "Unknown")

        card = f"""
        <div style="background:#fff8f0;border:1px solid #e8d5bc;border-radius:4px;padding:28px 24px 24px;display:flex;flex-direction:column;gap:16px;box-shadow:0 2px 8px rgba(45,27,14,0.05)">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
            <div style="font-family:Georgia,serif;font-size:26px;font-weight:400;color:#2d1b0e;line-height:1.15">{name.title()}</div>
            <span style="font-family:system-ui;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;padding:4px 10px;border-radius:2px;white-space:nowrap;flex-shrink:0;margin-top:4px;{pill_style}">{label}</span>
          </div>
          <div style="display:flex;flex-direction:column;gap:6px">
            <div style="display:flex;justify-content:space-between;align-items:baseline">
              <span style="font-family:system-ui;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#7a5c42;font-weight:600">Pairing Score</span>
              <span style="font-family:Georgia,serif;font-size:15px;color:#2d1b0e">{score:.3f}</span>
            </div>
            <div style="height:3px;background:#e8d5bc;border-radius:2px;overflow:hidden">
              <div style="height:100%;width:{score * 100:.1f}%;background:linear-gradient(90deg,#c4622a,#e8845a);border-radius:2px"></div>
            </div>
          </div>
          <div style="display:flex;flex-direction:column;gap:6px">
            <div style="display:flex;justify-content:space-between;align-items:baseline">
              <span style="font-family:system-ui;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#7a5c42;font-weight:600">Surprise Score</span>
              <span style="font-family:Georgia,serif;font-size:15px;color:#2d1b0e">{surprise:.3f}</span>
            </div>
            <div style="height:3px;background:#e8d5bc;border-radius:2px;overflow:hidden">
              <div style="height:100%;width:{surprise * 100:.1f}%;background:linear-gradient(90deg,#4a7c4e,#6aab6e);border-radius:2px"></div>
            </div>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:6px">{mol_tags if mol_tags else '<span style="font-family:system-ui;font-size:11px;font-style:italic;color:#c4a882">No shared molecules</span>'}</div>
          <div style="font-family:Georgia,serif;font-size:13px;font-style:italic;color:#7a5c42;line-height:1.6;padding-top:12px;border-top:1px solid #e8d5bc">{why}</div>
        </div>
        """
        cards_html.append(card)

    # Pair up into 2-column grid
    rows = []
    for i in range(0, len(cards_html), 2):
        left = cards_html[i]
        right = cards_html[i + 1] if i + 1 < len(cards_html) else "<div></div>"
        rows.append(
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:24px">'
            f"{left}{right}</div>"
        )

    return f"""
    <div style="margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #e8d5bc;display:flex;align-items:baseline;justify-content:space-between">
      <div style="font-family:Georgia,serif;font-size:28px;font-weight:400;color:#2d1b0e">Pairings for <em style="font-style:italic;color:#c4622a">{query.title()}</em></div>
      <div style="font-family:system-ui;font-size:13px;color:#7a5c42;letter-spacing:0.03em">{len(pairs)} results</div>
    </div>
    {"".join(rows)}
    """


try:
    pairs = require_scored_pairs()
    ingredients = require_ingredients()

    query = st.text_input(
        "FIND PAIRINGS FOR ANY INGREDIENT",
        placeholder="e.g. strawberry, miso, cardamom",
        label_visibility="visible",
    )

    if query.strip():
        results = get_top_pairings(query, pairs, ingredients)
        if not results:
            st.markdown(
                f'<div style="font-family:Georgia,serif;font-size:15px;font-style:italic;'
                f'color:#7a5c42;padding:24px 0">No pairings found for \u201c{query}\u201d. '
                f"Try another ingredient.</div>",
                unsafe_allow_html=True,
            )
        else:
            html = render_cards_html(query, results)
            # Each card row is ~320px tall; header ~80px
            n_rows = (len(results) + 1) // 2
            height = 80 + n_rows * 340
            components.html(html, height=height, scrolling=False)

except Exception as e:
    st.error(f"Something went wrong loading ingredient data. ({type(e).__name__})")
    st.stop()
