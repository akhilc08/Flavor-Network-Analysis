"""Page 2 — Active Learning Rating (UI-03)."""
import streamlit as st
from app.utils.theme import inject_theme, pill_html
from app.utils.cache import require_scored_pairs, invalidate_scored_pairs
from app.utils.rate import get_uncertain_pairs_for_display, submit_all_ratings

inject_theme()
st.title("Rate Uncertain Pairs")
st.markdown(
    '<p class="subtext">Help improve the model by rating these uncertain ingredient pairings</p>',
    unsafe_allow_html=True,
)

try:
    # Gate check: active learning requires AUC >= 0.70
    try:
        from model.active_learning import is_active_learning_enabled
        enabled, current_auc = is_active_learning_enabled()
    except ImportError:
        # Model not yet built — show warning
        enabled, current_auc = False, 0.0

    if not enabled:
        st.warning(
            f"Active learning requires AUC \u2265 0.70. "
            f"Current AUC: {current_auc:.3f}. "
            "Complete model training first (python run_pipeline.py)."
        )
        # Don't st.stop() — still show pairs for browsing but disable submit

    pairs = require_scored_pairs()
    uncertain = get_uncertain_pairs_for_display(pairs, n=5)

    if not uncertain:
        st.info("No uncertain pairs found. The model may be well-calibrated.")
        st.stop()

    st.markdown(f"**5 pairs the model is least certain about** (pairing score near 0.5)")

    # Collect ratings in session state
    if "ratings" not in st.session_state:
        st.session_state.ratings = {}

    for pair in uncertain:
        pair_key = f"{pair.ingredient_a}|{pair.ingredient_b}"
        with st.container():
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(
                    f"**{pair.ingredient_a.title()}** + **{pair.ingredient_b.title()}**"
                )
                st.markdown(pill_html(pair.label), unsafe_allow_html=True)
                st.markdown(
                    f'<span class="subtext">Pairing score: {pair.pairing_score:.3f} '
                    f"(uncertainty: {abs(pair.pairing_score - 0.5):.3f})</span>",
                    unsafe_allow_html=True,
                )
            with col2:
                rating = st.slider(
                    "Your rating",
                    min_value=0,
                    max_value=5,
                    value=st.session_state.ratings.get(pair_key, 3),
                    key=f"slider_{pair_key}",
                    help="0 = skip, 1 = poor pairing, 5 = excellent pairing",
                    format="%d \u2605",
                )
                st.session_state.ratings[pair_key] = rating
                # Show star display
                stars = "\u2605" * rating + "\u2606" * (5 - rating)
                st.markdown(f"**{stars}**")

    # Submit button — disabled if gate not met
    submit_disabled = not enabled
    if st.button("Submit Ratings", disabled=submit_disabled, type="primary"):
        rated_count = sum(1 for v in st.session_state.ratings.values() if v > 0)
        if rated_count == 0:
            st.warning("Please rate at least one pair before submitting.")
        else:
            with st.spinner("Fine-tuning model... This takes ~30 seconds."):
                result = submit_all_ratings(st.session_state.ratings, uncertain)

            # Clear cache so next page visit shows updated pairings
            invalidate_scored_pairs()
            st.session_state.ratings = {}

            # Show AUC delta
            auc_before = result.get("auc_before")
            auc_after = result.get("auc_after")
            if auc_before is not None and auc_after is not None:
                delta = auc_after - auc_before
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("AUC Before", f"{auc_before:.4f}")
                with col2:
                    st.metric("AUC After", f"{auc_after:.4f}",
                              delta=f"{delta:+.4f}")
                if delta > 0:
                    st.success(f"Model improved! AUC increased by {delta:.4f}")
                elif delta < 0:
                    st.warning(f"AUC decreased by {abs(delta):.4f}. The ratings may conflict with existing data.")
                else:
                    st.info("AUC unchanged — ratings consistent with existing model knowledge.")
            else:
                st.success("Ratings submitted. Model updated.")

except Exception as e:
    st.error(f"Something went wrong on the rating page. ({type(e).__name__})")
    st.stop()
