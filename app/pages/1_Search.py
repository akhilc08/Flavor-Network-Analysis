"""Page 1 — Ingredient Search (UI-01, UI-02)."""
import streamlit as st
from app.utils.theme import inject_theme, pill_html, molecule_tag_html
from app.utils.cache import require_scored_pairs
from app.utils.search import get_top_pairings, build_radar_chart, format_why_it_works

inject_theme()
st.title("Ingredient Search")
st.markdown('<p class="subtext">Find molecular pairings for any ingredient</p>',
            unsafe_allow_html=True)

try:
    pairs = require_scored_pairs()  # stops page if file missing (UI-07)

    query = st.text_input("Search ingredient", placeholder="e.g. strawberry")

    if query.strip():
        results = get_top_pairings(query, pairs)
        if not results:
            st.info(f"No pairings found for '{query}'. Try another ingredient.")
        else:
            st.markdown(f"**Top {len(results)} pairings for {query.title()}**")
            for i, pair in enumerate(results):
                with st.expander(pair.ingredient_b.title(), expanded=(i == 0)):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        # Pill badge + score bar
                        st.markdown(pill_html(pair.label), unsafe_allow_html=True)
                        st.markdown(f"**Surprise score:** {pair.surprise_score:.3f}")
                        st.progress(float(pair.pairing_score),
                                    text=f"Pairing strength: {pair.pairing_score:.3f}")

                        # Shared molecules as inline tags
                        st.markdown("**Shared flavor molecules:**")
                        mol_tags = "".join(
                            molecule_tag_html(m)
                            for m in (pair.shared_molecules or [])[:5]
                        )
                        if mol_tags:
                            st.markdown(mol_tags, unsafe_allow_html=True)
                        else:
                            st.markdown("_No shared molecules_")

                        # Why it works
                        st.markdown("**Why this works:**")
                        st.markdown(format_why_it_works(
                            (pair.shared_molecules or [])[:5]
                        ))

                    with col2:
                        # Dual-polygon radar chart
                        profile_a = getattr(pair, "flavor_profile_a", {})
                        profile_b = getattr(pair, "flavor_profile_b", {})
                        if profile_a or profile_b:
                            fig = build_radar_chart(
                                query.title(), profile_a,
                                pair.ingredient_b.title(), profile_b
                            )
                            st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Something went wrong loading ingredient data. ({type(e).__name__})")
    st.stop()
