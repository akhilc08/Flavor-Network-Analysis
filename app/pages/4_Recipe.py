"""Page 4 — Recipe Generation (UI-05)."""
from __future__ import annotations
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic
import streamlit as st

from utils.theme import inject_theme, molecule_tag_html
from utils.cache import require_scored_pairs

inject_theme()

# Editorial page header
st.markdown(
    """
    <div style="margin-bottom:32px">
      <h1 style="font-family:Georgia,serif;font-size:32px;font-weight:400;color:#2d1b0e;margin-bottom:4px">
        AI Recipe Generation
      </h1>
      <p style="font-family:system-ui;font-size:13px;color:#7a5c42;letter-spacing:0.02em;margin:0">
        Molecular rationale &middot; Written by Claude
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Check for API key early
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    st.markdown(
        '<div style="background:rgba(196,98,42,0.08);border:1px solid rgba(196,98,42,0.25);'
        'border-radius:4px;padding:20px 24px">'
        '<div style="font-family:system-ui;font-size:10px;font-weight:600;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#c4622a;margin-bottom:8px">API key required</div>'
        '<p style="font-family:system-ui;font-size:13px;color:#7a5c42;margin:0;line-height:1.6">'
        'Set <code style="background:#fdf6ec;border:1px solid #e8d5bc;border-radius:2px;'
        'padding:1px 6px;font-size:12px">ANTHROPIC_API_KEY</code> before running the app:'
        '<br><br><code style="background:#fdf6ec;border:1px solid #e8d5bc;border-radius:2px;'
        'padding:4px 8px;font-size:12px">export ANTHROPIC_API_KEY=sk-ant-...</code></p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()


def stream_recipe(client: anthropic.Anthropic, prompt: str):
    """
    Generator that yields text strings for st.write_stream().

    CRITICAL: Must iterate stream.text_stream, NOT the stream object directly.
    Passing stream object to st.write_stream yields raw JSON event dicts.
    See RESEARCH.md Pitfall 2 and Pattern 3.
    """
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def build_recipe_prompt(
    ingredients: list[str],
    shared_molecules_map: dict[str, list[str]],
    flavor_labels: dict[str, str],
) -> str:
    """Build the recipe generation prompt with molecular context."""
    ingredient_list = ", ".join(i.title() for i in ingredients)

    molecule_context_parts = []
    for pair_key, molecules in shared_molecules_map.items():
        if molecules:
            mol_str = ", ".join(molecules[:5])
            molecule_context_parts.append(f"  - {pair_key}: shares {mol_str}")
    molecule_context = (
        "\n".join(molecule_context_parts)
        if molecule_context_parts
        else "  - (molecular data not available)"
    )

    label_context = (
        "; ".join(f"{i.title()} is a '{v}' pairing" for i, v in flavor_labels.items())
        if flavor_labels
        else ""
    )

    return f"""You are a culinary scientist and chef. Create a recipe using these molecularly paired ingredients: {ingredient_list}.

Molecular flavor context:
{molecule_context}

{f"Pairing classification: {label_context}" if label_context else ""}

Your recipe MUST:
1. Give the dish a creative, evocative name
2. Explain in 2-3 sentences WHY these ingredients work together scientifically — reference the specific shared flavor compounds by name
3. List all ingredients with quantities
4. Provide clear step-by-step cooking instructions (6-10 steps)
5. End with a "Flavor Science" note explaining the molecular pairing rationale in plain English

Write for a curious food lover who appreciates both great cooking and the science behind it. Be specific about the flavor compounds."""


def pill_html_inline(label: str) -> str:
    """Compact pill for inline display next to ingredient names."""
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
    style = pill_styles.get(label_lower, pill_styles["classic"])
    base = (
        "font-family:system-ui;font-size:11px;font-weight:600;"
        "letter-spacing:0.08em;text-transform:uppercase;"
        "padding:3px 8px;border-radius:2px;display:inline-block;margin-right:8px;"
    )
    return f'<span style="{base}{style}">{label}</span>'


try:
    pairs = require_scored_pairs()

    top_surprise = [p for p in pairs if getattr(p, "label", "") == "Surprising"][:20]
    if not top_surprise:
        top_surprise = sorted(
            pairs, key=lambda p: getattr(p, "surprise_score", 0), reverse=True
        )[:20]

    ingredient_options = list(dict.fromkeys(
        name
        for p in top_surprise
        for name in [getattr(p, "ingredient_a", ""), getattr(p, "ingredient_b", "")]
        if name
    ))

    if not ingredient_options:
        st.warning("No ingredient data available. Run the pipeline first.")
        st.stop()

    st.markdown(
        '<p style="font-family:system-ui;font-size:13px;color:#7a5c42;line-height:1.6;margin-bottom:16px">'
        "Select 2\u20133 ingredients from the most surprising pairs in your dataset. "
        "Claude will generate a recipe with molecular flavor rationale."
        "</p>",
        unsafe_allow_html=True,
    )

    selected = st.multiselect(
        "SELECT INGREDIENTS",
        options=ingredient_options,
        max_selections=3,
        placeholder="Choose 2\u20133 ingredients\u2026",
    )

    if len(selected) < 2:
        st.markdown(
            '<p style="font-family:Georgia,serif;font-size:14px;font-style:italic;'
            'color:#7a5c42;margin-top:8px">Select at least 2 ingredients to continue.</p>',
            unsafe_allow_html=True,
        )
        st.stop()

    # Selected ingredients with editorial pill display
    st.markdown('<div style="margin:20px 0 8px">', unsafe_allow_html=True)
    for ing in selected:
        pair_match = next(
            (p for p in pairs
             if getattr(p, "ingredient_a", "") == ing
             or getattr(p, "ingredient_b", "") == ing),
            None,
        )
        label = getattr(pair_match, "label", "Classic") if pair_match else "Classic"
        st.markdown(
            f'<div style="display:flex;align-items:center;margin-bottom:8px">'
            f'{pill_html_inline(label)}'
            f'<span style="font-family:Georgia,serif;font-size:18px;color:#2d1b0e">{ing.title()}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # Build shared molecules map
    shared_molecules_map: dict[str, list[str]] = {}
    for i, ing_a in enumerate(selected):
        for ing_b in selected[i + 1:]:
            pair_match = next(
                (p for p in pairs
                 if (getattr(p, "ingredient_a", "") == ing_a and getattr(p, "ingredient_b", "") == ing_b)
                 or (getattr(p, "ingredient_a", "") == ing_b and getattr(p, "ingredient_b", "") == ing_a)),
                None,
            )
            molecules = getattr(pair_match, "shared_molecules", []) if pair_match else []
            shared_molecules_map[f"{ing_a} + {ing_b}"] = molecules[:5]

    # Show molecule tags with editorial styling
    for pair_label, molecules in shared_molecules_map.items():
        if molecules:
            st.markdown(
                f'<div style="margin-bottom:12px">'
                f'<div style="font-family:system-ui;font-size:10px;font-weight:600;letter-spacing:0.1em;'
                f'text-transform:uppercase;color:#7a5c42;margin-bottom:6px">{pair_label} shared molecules</div>'
                f'<div>{"".join(molecule_tag_html(m) for m in molecules)}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

    flavor_labels = {
        ing: getattr(
            next((p for p in pairs if getattr(p, "ingredient_a", "") == ing), None),
            "label",
            "",
        )
        for ing in selected
    }

    st.markdown('<hr style="border-color:#e8d5bc;margin:24px 0">', unsafe_allow_html=True)

    if st.button("Generate Recipe", type="primary"):
        prompt = build_recipe_prompt(selected, shared_molecules_map, flavor_labels)

        st.markdown(
            '<h2 style="font-family:Georgia,serif;font-size:24px;font-weight:400;'
            'color:#2d1b0e;margin-bottom:4px">Your Molecular Pairing Recipe</h2>'
            '<p style="font-family:system-ui;font-size:12px;color:#7a5c42;'
            'letter-spacing:0.04em;margin-bottom:20px">Generated by Claude claude-sonnet-4-6</p>',
            unsafe_allow_html=True,
        )

        try:
            client = anthropic.Anthropic(api_key=api_key)
            full_recipe = st.write_stream(stream_recipe(client, prompt))
            st.session_state["last_recipe"] = full_recipe
            st.success("Recipe complete. Scroll up to read it.")

        except anthropic.AuthenticationError:
            st.error(
                "Anthropic API key is invalid or expired. "
                "Check your ANTHROPIC_API_KEY environment variable."
            )
        except anthropic.RateLimitError:
            st.error("Anthropic rate limit reached. Wait a moment and try again.")
        except Exception as e:
            st.error(f"Recipe generation failed: {type(e).__name__}. Check the terminal for details.")

except Exception as e:
    st.error(f"Something went wrong on the recipe page. ({type(e).__name__})")
    st.stop()
