# Phase 6: Streamlit UI - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a polished 4-page Streamlit demo: ingredient search with pairings, active learning rating, flavor graph explorer, and Claude-powered recipe generation. Imports clean APIs from Phase 5 (`scoring.score`, `model.active_learning`). No new ML logic — UI only.

</domain>

<decisions>
## Implementation Decisions

### App Structure
- Multi-file Streamlit pages (`app/pages/`) with sidebar navigation — auto-generated sidebar from file structure
- Entry point: `app/app.py`; pages: `1_Search.py`, `2_Rate.py`, `3_Graph.py`, `4_Recipe.py`
- Sidebar shows app name/logo and page links; active page highlighted
- `@st.cache_resource` for loading embeddings and scored_pairs (loaded once per process); cache explicitly cleared after each active learning fine-tune round

### Visual Theme — Earthy / Food-forward (Theme A)
- Background: `#fdf6ec` (warm cream)
- Surface/cards: `#fff8f0` (lighter cream)
- Sidebar: `#f0e6d3` (warm tan)
- Accent: `#c4622a` (burnt orange)
- Text: `#2d1b0e` (dark brown)
- Subtext: `#7a5c42`
- Border: `#e8d5bc`
- Pill colors: Surprising=`#4a7c4e` (herb green), Unexpected=`#b8860b` (amber), Classic=`#888` (gray)
- Headings: serif (Georgia or Playfair Display via CSS injection)
- Body: system-ui / sans-serif, relaxed line-height
- Injected via `st.markdown("<style>...</style>", unsafe_allow_html=True)` in each page

### Page 1 — Ingredient Search
- Search box at top (`st.text_input`), results appear below on input
- Top 10 pairings shown as expandable cards (`st.expander`); first result expanded by default
- Each card shows: ingredient name (serif, large), colored pill badge (Surprising/Unexpected/Classic), score bar (score number + `st.progress`), top 5 shared molecules as inline tags, Plotly radar chart comparing flavor profiles, "Why it works" plain-English explanation of shared compounds
- Radar chart: polygon comparing strawberry vs pairing ingredient across flavor dimensions (sweet, sour, umami, bitter, floral, smoky); two overlapping polygons in accent color vs herb green

### Page 2 — Active Learning Rating
- Shows top 5 most uncertain pairs (pairing_score closest to 0.5)
- Each pair shown as a card with `st.slider` (1–5 stars rendered as ★ via markdown)
- Single "Submit Ratings" button triggers `submit_rating()` for each rated pair
- Fine-tuning blocks UI with `st.spinner("Fine-tuning model...")` — synchronous, not async
- After completion: show AUC before and after as `st.metric` with delta (e.g. `AUC: 0.73 ▲ +0.02`)
- If active learning gate not met (AUC < 0.70): show friendly warning, disable submit button

### Page 3 — Flavor Graph Explorer
- Ingredient selector (`st.selectbox`) to choose center ingredient
- PyVis graph rendered via `st.components.v1.html()` with the generated HTML
- ≤50 nodes: center ingredient + top-49 pairings by pairing_score
- Node size proportional to pairing_score with center ingredient (center node largest)
- Edge color: red=surprising, blue=expected (mapped from surprise_score)
- Click a node to re-center graph on that ingredient (handled via PyVis click events → st.session_state)

### Page 4 — Recipe Generation
- Multiselect of 2–3 ingredients from top surprise pairs (`st.multiselect`, max 3)
- "Generate Recipe" button calls Anthropic SDK (`claude-sonnet-4-6`)
- Recipe streams token-by-token via `st.write_stream()` with the SDK's streaming response
- Prompt instructs Claude to: name the dish, explain the molecular pairing rationale, list specific shared compounds, include full recipe with ingredients + steps
- Anthropic API key loaded from environment variable `ANTHROPIC_API_KEY`; friendly error if missing

### Error Handling
- All pages wrapped in try/except; errors shown as `st.error("...")` with plain English message — no raw tracebacks
- Missing model files (scored_pairs.pkl not found): show `st.warning` with instructions to run the pipeline first
- Active learning fine-tune failure: show `st.error` with message, do not crash app

### Claude's Discretion
- Exact CSS injection approach for custom theme (inline style tags vs config.toml)
- Radar chart axis labels and polygon smoothing
- PyVis physics settings for graph layout
- Exact prompt wording for Claude recipe generation
- Loading skeleton vs spinner for initial data load

</decisions>

<specifics>
## Specific Ideas

- Theme A (earthy/food-forward) chosen from 3 mockups — warm cream background, burnt orange accent, herb green for "Surprising" badges. Feels like a food magazine, not an ML dashboard.
- Serif headings (Georgia) give an editorial feel consistent with the food discovery angle
- Recipe page should stream — makes the Claude generation feel alive and impressive in a demo

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/` directory exists (empty, gitkeep) — ready for Streamlit files
- `run_pipeline.py`: established pattern of direct function imports — Phase 6 follows same pattern
- `logs/pipeline.log`: shared log file — app errors can log here too

### Established Patterns
- Direct Python imports (not subprocess) — locked since Phase 1
- Skip-if-exists / graceful degradation — app shows friendly message if pipeline hasn't run yet
- Summary/status display pattern (established in Phase 1 scripts) — adapted to `st.metric` widgets

### Integration Points
- **Reads from Phase 5:** `from scoring.score import load_scored_pairs, get_top_pairings, get_uncertain_pairs`
- **Reads from Phase 5:** `from model.active_learning import submit_rating, is_active_learning_enabled`
- **Phase 3:** `graph/hetero_data.pt` — needed by Page 3 for graph structure (ingredient neighbor lists)
- **Env:** `ANTHROPIC_API_KEY` must be set before running Page 4
- Launch: `streamlit run app/app.py` from project root

</code_context>

<deferred>
## Deferred Ideas

- v2 Polish (POLISH-01 to 04 from REQUIREMENTS.md): uncertainty badges, t-SNE visualization, cross-cultural pairing flag, model details panel — future milestone
- Score percentile rank display (UI-V2-01) — future milestone
- Loading indicators for fine-tune (UI-V2-02) — partially addressed (spinner), full async progress bar is v2

</deferred>

---

*Phase: 06-streamlit-ui*
*Context gathered: 2026-03-11*
