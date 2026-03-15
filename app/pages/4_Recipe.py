"""Page 4 — Recipe Generation (UI-05)."""
from __future__ import annotations
import os

import anthropic
import streamlit as st

from app.utils.theme import inject_theme, pill_html, molecule_tag_html
from app.utils.cache import require_scored_pairs

inject_theme()
st.title("AI Recipe Generation")
st.markdown(
    '<p class="subtext">Generate a recipe with molecular flavor pairing rationale</p>',
    unsafe_allow_html=True,
)

# Check for API key early — friendly error, not KeyError
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    st.error(
        "ANTHROPIC_API_KEY environment variable is not set.\n\n"
        "Set it before running the app:\n\n"
        "```\nexport ANTHROPIC_API_KEY=sk-ant-...\nstreamlit run app/app.py\n```"
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

    # Build molecular rationale context
    molecule_context_parts = []
    for pair_key, molecules in shared_molecules_map.items():
        if molecules:
            mol_str = ", ".join(molecules[:5])
            molecule_context_parts.append(f"  - {pair_key}: shares {mol_str}")
    molecule_context = "\n".join(molecule_context_parts) if molecule_context_parts else "  - (molecular data not available)"

    # Build label context
    label_context = "; ".join(
        f"{i.title()} is a '{v}' pairing" for i, v in flavor_labels.items()
    ) if flavor_labels else ""

    prompt = f"""You are a culinary scientist and chef. Create a recipe using these molecularly paired ingredients: {ingredient_list}.

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

    return prompt


try:
    pairs = require_scored_pairs()

    # Get top surprising pairs for ingredient selection
    top_surprise = [
        p for p in pairs
        if getattr(p, "label", "") == "Surprising"
    ][:20]

    if not top_surprise:
        # Fallback: use top pairs by surprise_score
        top_surprise = sorted(pairs, key=lambda p: getattr(p, "surprise_score", 0), reverse=True)[:20]

    ingredient_options = list(dict.fromkeys(
        name for p in top_surprise
        for name in [getattr(p, "ingredient_a", ""), getattr(p, "ingredient_b", "")]
        if name
    ))

    if not ingredient_options:
        st.warning("No ingredient data available. Run the pipeline first.")
        st.stop()

    st.markdown("**Select 2–3 ingredients from your top surprise pairs:**")
    selected = st.multiselect(
        "Ingredients",
        options=ingredient_options,
        max_selections=3,
        placeholder="Choose 2–3 ingredients...",
    )

    if len(selected) < 2:
        st.info("Select at least 2 ingredients to generate a recipe.")
        st.stop()

    # Display selected ingredients with their labels
    st.markdown("**Selected ingredients:**")
    for ing in selected:
        pair_match = next(
            (p for p in pairs if getattr(p, "ingredient_a", "") == ing
             or getattr(p, "ingredient_b", "") == ing),
            None
        )
        label = getattr(pair_match, "label", "Unknown") if pair_match else "Unknown"
        st.markdown(pill_html(label) + f" **{ing.title()}**", unsafe_allow_html=True)

    # Build shared molecules map for prompt context
    shared_molecules_map: dict[str, list[str]] = {}
    for i, ing_a in enumerate(selected):
        for ing_b in selected[i+1:]:
            pair_match = next(
                (p for p in pairs
                 if (getattr(p, "ingredient_a", "") == ing_a and getattr(p, "ingredient_b", "") == ing_b)
                 or (getattr(p, "ingredient_a", "") == ing_b and getattr(p, "ingredient_b", "") == ing_a)),
                None
            )
            molecules = getattr(pair_match, "shared_molecules", []) if pair_match else []
            shared_molecules_map[f"{ing_a} + {ing_b}"] = molecules[:5]

    # Show molecule tags for context
    for pair_label, molecules in shared_molecules_map.items():
        if molecules:
            st.markdown(f"**{pair_label}** shared molecules:")
            tags = "".join(molecule_tag_html(m) for m in molecules)
            st.markdown(tags, unsafe_allow_html=True)

    flavor_labels = {
        ing: getattr(
            next((p for p in pairs if getattr(p, "ingredient_a", "") == ing), None),
            "label", ""
        )
        for ing in selected
    }

    st.markdown("---")

    if st.button("Generate Recipe", type="primary"):
        prompt = build_recipe_prompt(selected, shared_molecules_map, flavor_labels)

        st.markdown("### Your Molecular Pairing Recipe")
        st.markdown('<p class="subtext">Generating with Claude claude-sonnet-4-6...</p>',
                    unsafe_allow_html=True)

        try:
            client = anthropic.Anthropic(api_key=api_key)
            # stream_recipe() is a generator yielding strings — correct pattern for st.write_stream
            full_recipe = st.write_stream(stream_recipe(client, prompt))

            # Save to session state for copy/reference after streaming completes
            st.session_state["last_recipe"] = full_recipe
            st.success("Recipe generated! Scroll up to read it.")

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
