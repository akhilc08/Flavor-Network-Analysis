"""Page 2 — Active Learning Rating (UI-03)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from utils.theme import inject_theme
from utils.cache import require_scored_pairs, invalidate_scored_pairs
from utils.rate import get_uncertain_pairs_for_display, submit_all_ratings

inject_theme()

# Editorial page header
st.markdown(
    """
    <div style="margin-bottom:32px">
      <h1 style="font-family:Georgia,serif;font-size:32px;font-weight:400;color:#2d1b0e;margin-bottom:4px">
        Rate Uncertain Pairs
      </h1>
      <p style="font-family:system-ui;font-size:13px;color:#7a5c42;letter-spacing:0.02em;margin:0">
        Active learning &middot; Help the model improve
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)


def render_pair_card_html(pair) -> str:
    """Build editorial HTML card for a single uncertain pair."""
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
    uncertainty = abs(score - 0.5)
    name_a = getattr(pair, "ingredient_a", "?").title()
    name_b = getattr(pair, "ingredient_b", "?").title()
    molecules = getattr(pair, "shared_molecules", []) or []
    mol_tags = "".join(
        f'<span style="font-family:system-ui;font-size:11px;font-style:italic;'
        f'color:#7a5c42;background:#fdf6ec;border:1px solid #e8d5bc;'
        f'border-radius:2px;padding:3px 8px;margin:2px;display:inline-block">{m}</span>'
        for m in molecules[:5]
    )

    return f"""
    <div style="background:#fff8f0;border:1px solid #e8d5bc;border-radius:4px;padding:24px;box-shadow:0 2px 8px rgba(45,27,14,0.05);margin-bottom:4px">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:16px">
        <div style="font-family:Georgia,serif;font-size:22px;font-weight:400;color:#2d1b0e;line-height:1.2">
          {name_a} <span style="color:#7a5c42;font-size:16px">+</span> {name_b}
        </div>
        <span style="font-family:system-ui;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;padding:4px 10px;border-radius:2px;white-space:nowrap;flex-shrink:0;{pill_style}">{label}</span>
      </div>
      <div style="display:flex;gap:32px;margin-bottom:12px">
        <div>
          <div style="font-family:system-ui;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#7a5c42;font-weight:600;margin-bottom:2px">Pairing Score</div>
          <div style="font-family:Georgia,serif;font-size:18px;color:#2d1b0e">{score:.3f}</div>
        </div>
        <div>
          <div style="font-family:system-ui;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#7a5c42;font-weight:600;margin-bottom:2px">Uncertainty</div>
          <div style="font-family:Georgia,serif;font-size:18px;color:#2d1b0e">{uncertainty:.3f}</div>
        </div>
      </div>
      {f'<div style="display:flex;flex-wrap:wrap;gap:6px">{mol_tags}</div>' if mol_tags else ''}
    </div>
    """


try:
    # Gate check: active learning requires AUC >= 0.70
    try:
        from model.active_learning import is_active_learning_enabled
        enabled, current_auc = is_active_learning_enabled()
    except ImportError:
        enabled, current_auc = False, 0.0

    if not enabled:
        st.markdown(
            f'<div style="background:rgba(196,98,42,0.08);border:1px solid rgba(196,98,42,0.25);'
            f'border-radius:4px;padding:16px 20px;margin-bottom:24px">'
            f'<span style="font-family:system-ui;font-size:12px;font-weight:600;letter-spacing:0.08em;'
            f'text-transform:uppercase;color:#c4622a">Model not ready</span>'
            f'<p style="font-family:system-ui;font-size:13px;color:#7a5c42;margin:6px 0 0">'
            f'Active learning requires AUC \u2265 0.70. '
            f'Current AUC: <strong style="color:#2d1b0e">{current_auc:.3f}</strong>. '
            f'Complete model training first.</p></div>',
            unsafe_allow_html=True,
        )

    pairs = require_scored_pairs()
    uncertain = get_uncertain_pairs_for_display(pairs, n=5)

    if not uncertain:
        st.markdown(
            '<div style="font-family:Georgia,serif;font-size:15px;font-style:italic;color:#7a5c42;padding:24px 0">'
            "No uncertain pairs found. The model may be well-calibrated."
            "</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    st.markdown(
        '<p style="font-family:system-ui;font-size:13px;color:#7a5c42;margin-bottom:24px">'
        "These 5 pairs sit closest to the model\u2019s decision boundary (score \u2248 0.5). "
        "Your ratings give it signal to improve."
        "</p>",
        unsafe_allow_html=True,
    )

    # Collect ratings in session state
    if "ratings" not in st.session_state:
        st.session_state.ratings = {}

    for pair in uncertain:
        pair_key = f"{pair.ingredient_a}|{pair.ingredient_b}"

        # HTML card for visual context
        st.markdown(render_pair_card_html(pair), unsafe_allow_html=True)

        # Real Streamlit slider (cannot be CSS-faked)
        rating = st.slider(
            f"Your rating for {pair.ingredient_a.title()} + {pair.ingredient_b.title()}",
            min_value=0,
            max_value=5,
            value=st.session_state.ratings.get(pair_key, 3),
            key=f"slider_{pair_key}",
            help="0 = skip, 1 = poor pairing, 5 = excellent pairing",
            format="%d \u2605",
        )
        st.session_state.ratings[pair_key] = rating

        # Star display beneath slider
        stars = "\u2605" * rating + "\u2606" * (5 - rating)
        st.markdown(
            f'<div style="font-family:Georgia,serif;font-size:16px;color:#c4622a;'
            f'letter-spacing:2px;margin-bottom:24px">{stars}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr style="border-color:#e8d5bc;margin:8px 0 24px">', unsafe_allow_html=True)

    # Submit button
    submit_disabled = not enabled
    if st.button("Submit Ratings", disabled=submit_disabled, type="primary"):
        rated_count = sum(1 for v in st.session_state.ratings.values() if v > 0)
        if rated_count == 0:
            st.warning("Please rate at least one pair before submitting.")
        else:
            with st.spinner("Fine-tuning model\u2026 This takes ~30 seconds."):
                result = submit_all_ratings(st.session_state.ratings, uncertain)

            invalidate_scored_pairs()
            st.session_state.ratings = {}

            auc_before = result.get("auc_before")
            auc_after = result.get("auc_after")
            if auc_before is not None and auc_after is not None:
                delta = auc_after - auc_before
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("AUC Before", f"{auc_before:.4f}")
                with col2:
                    st.metric("AUC After", f"{auc_after:.4f}", delta=f"{delta:+.4f}")
                if delta > 0:
                    st.success(f"Model improved. AUC increased by {delta:.4f}")
                elif delta < 0:
                    st.warning(f"AUC decreased by {abs(delta):.4f}. Ratings may conflict with existing data.")
                else:
                    st.info("AUC unchanged \u2014 ratings consistent with existing model knowledge.")
            else:
                st.success("Ratings submitted. Model updated.")

except Exception as e:
    st.error(f"Something went wrong on the rating page. ({type(e).__name__})")
    st.stop()
