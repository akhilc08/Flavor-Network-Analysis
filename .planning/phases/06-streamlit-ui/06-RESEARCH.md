# Phase 6: Streamlit UI - Research

**Researched:** 2026-03-11
**Domain:** Streamlit multi-page app, PyVis graph visualization, Plotly radar charts, Anthropic SDK streaming
**Confidence:** HIGH (stack) / MEDIUM (PyVis click workaround)

## Summary

Phase 6 builds a 4-page Streamlit demo app consuming APIs from Phase 5. The decisions in CONTEXT.md are highly specific and well-considered; research focuses on verifying exact API behavior, confirming known pitfalls, and surfacing one important constraint the planner must handle.

The primary technical challenge is Page 3 (PyVis graph): PyVis click events **cannot natively communicate back to Python** via `st.components.v1.html`. This is a confirmed open issue in PyVis (GitHub issue #85, open since 2022) and a verified limitation of `st.components.v1.html` (which returns no value and has no session state integration). The planner must implement click-to-pivot via a `st.selectbox` widget that triggers a Python rerun — the PyVis graph re-renders centered on the newly selected ingredient. This is a UI-visible design tradeoff that should be called out explicitly.

The Anthropic SDK streaming pattern requires a wrapper generator because `st.write_stream()` receives raw JSON when iterating the response directly; the fix is a generator that yields from `stream.text_stream` instead of the stream object itself (confirmed GitHub issue #8963).

All other libraries are stable and well-understood. The earthy theme is implemented entirely via CSS injection in `st.markdown(..., unsafe_allow_html=True)` — no `config.toml` needed for the custom palette.

**Primary recommendation:** Build the app in the order: 1. theme+layout scaffold → 2. Search page → 3. Recipe page (streaming) → 4. Rate page (active learning) → 5. Graph page (PyVis + selectbox workaround). This order derisks the two hardest integrations early before the graph page.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**App Structure**
- Multi-file Streamlit pages (`app/pages/`) with sidebar navigation — auto-generated sidebar from file structure
- Entry point: `app/app.py`; pages: `1_Search.py`, `2_Rate.py`, `3_Graph.py`, `4_Recipe.py`
- Sidebar shows app name/logo and page links; active page highlighted
- `@st.cache_resource` for loading embeddings and scored_pairs (loaded once per process); cache explicitly cleared after each active learning fine-tune round

**Visual Theme — Earthy / Food-forward (Theme A)**
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

**Page 1 — Ingredient Search**
- Search box at top (`st.text_input`), results appear below on input
- Top 10 pairings shown as expandable cards (`st.expander`); first result expanded by default
- Each card shows: ingredient name (serif, large), colored pill badge (Surprising/Unexpected/Classic), score bar (score number + `st.progress`), top 5 shared molecules as inline tags, Plotly radar chart comparing flavor profiles, "Why it works" plain-English explanation of shared compounds
- Radar chart: polygon comparing strawberry vs pairing ingredient across flavor dimensions (sweet, sour, umami, bitter, floral, smoky); two overlapping polygons in accent color vs herb green

**Page 2 — Active Learning Rating**
- Shows top 5 most uncertain pairs (pairing_score closest to 0.5)
- Each pair shown as a card with `st.slider` (1–5 stars rendered as ★ via markdown)
- Single "Submit Ratings" button triggers `submit_rating()` for each rated pair
- Fine-tuning blocks UI with `st.spinner("Fine-tuning model...")` — synchronous, not async
- After completion: show AUC before and after as `st.metric` with delta (e.g. `AUC: 0.73 ▲ +0.02`)
- If active learning gate not met (AUC < 0.70): show friendly warning, disable submit button

**Page 3 — Flavor Graph Explorer**
- Ingredient selector (`st.selectbox`) to choose center ingredient
- PyVis graph rendered via `st.components.v1.html()` with the generated HTML
- ≤50 nodes: center ingredient + top-49 pairings by pairing_score
- Node size proportional to pairing_score with center ingredient (center node largest)
- Edge color: red=surprising, blue=expected (mapped from surprise_score)
- Click a node to re-center graph on that ingredient (handled via PyVis click events → st.session_state)

**Page 4 — Recipe Generation**
- Multiselect of 2–3 ingredients from top surprise pairs (`st.multiselect`, max 3)
- "Generate Recipe" button calls Anthropic SDK (`claude-sonnet-4-6`)
- Recipe streams token-by-token via `st.write_stream()` with the SDK's streaming response
- Prompt instructs Claude to: name the dish, explain the molecular pairing rationale, list specific shared compounds, include full recipe with ingredients + steps
- Anthropic API key loaded from environment variable `ANTHROPIC_API_KEY`; friendly error if missing

**Error Handling**
- All pages wrapped in try/except; errors shown as `st.error("...")` with plain English message — no raw tracebacks
- Missing model files (scored_pairs.pkl not found): show `st.warning` with instructions to run the pipeline first
- Active learning fine-tune failure: show `st.error` with message, do not crash app

### Claude's Discretion
- Exact CSS injection approach for custom theme (inline style tags vs config.toml)
- Radar chart axis labels and polygon smoothing
- PyVis physics settings for graph layout
- Exact prompt wording for Claude recipe generation
- Loading skeleton vs spinner for initial data load

### Deferred Ideas (OUT OF SCOPE)
- v2 Polish (POLISH-01 to 04): uncertainty badges, t-SNE visualization, cross-cultural pairing flag, model details panel
- Score percentile rank display (UI-V2-01)
- Loading indicators for fine-tune (UI-V2-02) — partially addressed (spinner), full async progress bar is v2
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-01 | Page 1 — Ingredient search box; top 10 pairings sorted by surprise_score; shows name, scores, top 5 molecules, Plotly radar chart, cuisine overlap | `st.text_input` + `st.expander` + `go.Scatterpolar` for radar; scoring API `get_top_pairings()` from Phase 5 |
| UI-02 | Page 1 — "Why this works" section: shared flavor compounds listed in plain English | Display logic only; data comes from shared_molecules field in scored_pairs |
| UI-03 | Page 2 — Top 5 uncertain pairs; 1–5 star rating; submit triggers fine-tuning; AUC delta shown | `st.slider` + `st.metric`; `submit_rating()` + `is_active_learning_enabled()` from Phase 5 |
| UI-04 | Page 3 — PyVis graph; ≤50 nodes; sized by score; edges colored by surprise; click to pivot | PyVis `Network` + `st.components.v1.html`; click-to-pivot requires selectbox workaround (see pitfall) |
| UI-05 | Page 4 — 2–3 ingredient multiselect; Anthropic SDK `claude-sonnet-4-6`; recipe with molecular rationale | `st.multiselect` + `anthropic.Anthropic().messages.stream()` + generator wrapping `text_stream` |
| UI-06 | All pages use `@st.cache_resource`; cache cleared after active learning fine-tune | `load_scored_pairs.clear()` called explicitly after `submit_rating()` completes |
| UI-07 | No raw stack traces visible; all errors as friendly messages | All page bodies in `try/except`; `st.error()` / `st.warning()` for display |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | 1.55.0 | Multi-page app framework | Latest stable (March 3, 2026); pages/ directory convention stable since 1.28 |
| plotly | 5.x | Radar chart (`go.Scatterpolar`) | Already in ecosystem; official Streamlit chart integration |
| pyvis | 0.3.x | Interactive network graph HTML | Only pure-Python vis.js wrapper; renders via `st.components.v1.html` |
| anthropic | 0.84.0 | Claude API SDK | Target model `claude-sonnet-4-6`; confirmed in STATE.md |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| streamlit.components.v1 | (built-in) | Render PyVis HTML iframe | Page 3 graph rendering only |
| pathlib | (stdlib) | File existence checks | Checking for scored_pairs.pkl before loading |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pyvis | streamlit-agraph | agraph has true click callbacks but requires vis.js config knowledge; pyvis is simpler and locked by CONTEXT.md |
| pyvis | networkx + plotly | plotly network has no physics layout; pyvis is visually better for demos |
| go.Scatterpolar | px.line_polar | px.line_polar is simpler but less control over dual-polygon overlay with different fill opacities |

**Installation (new packages to add to environment.yml):**
```bash
pip install streamlit==1.55.0 plotly pyvis anthropic==0.84.0
```

Or add to `environment.yml` under pip section:
```yaml
- streamlit==1.55.*
- plotly==5.*
- pyvis==0.3.*
- anthropic==0.84.*
```

---

## Architecture Patterns

### Recommended Project Structure
```
app/
├── app.py              # Entry point: sets page config, renders landing or redirects
├── pages/
│   ├── 1_Search.py     # UI-01, UI-02
│   ├── 2_Rate.py       # UI-03
│   ├── 3_Graph.py      # UI-04
│   └── 4_Recipe.py     # UI-05
└── utils/
    ├── theme.py        # CSS injection string (shared across all pages)
    └── cache.py        # @st.cache_resource wrappers for scored_pairs, embeddings
```

**Note on pages/ naming convention (HIGH confidence — official docs):**
Streamlit sorts pages by leading number prefix, then alphabetically. `1_Search.py` → sidebar label "Search". Underscores become spaces in the sidebar. The entry point `app.py` always appears first.

### Pattern 1: Shared Cache Layer
**What:** A single `app/utils/cache.py` module holds all `@st.cache_resource` decorated loaders. Pages import from this module, not from Phase 5 directly.
**When to use:** Every page that reads scored_pairs or embeddings — avoids duplicate cache keys.
**Example:**
```python
# app/utils/cache.py
import streamlit as st
from scoring.score import load_scored_pairs

@st.cache_resource
def get_scored_pairs():
    return load_scored_pairs()

def clear_scored_pairs():
    """Call after active learning fine-tune completes."""
    get_scored_pairs.clear()
```

### Pattern 2: CSS Theme Injection
**What:** A single CSS string defined in `app/utils/theme.py`, injected via `st.markdown(..., unsafe_allow_html=True)` at the top of each page.
**When to use:** All four pages call `inject_theme()` as their first action.
**Example:**
```python
# app/utils/theme.py
THEME_CSS = """
<style>
  .stApp { background-color: #fdf6ec; }
  [data-testid="stSidebar"] { background-color: #f0e6d3; }
  h1, h2, h3 { font-family: Georgia, serif; color: #2d1b0e; }
  /* ... full palette ... */
</style>
"""

def inject_theme():
    import streamlit as st
    st.markdown(THEME_CSS, unsafe_allow_html=True)
```

**Discretion note:** `config.toml` can set `primaryColor`, `backgroundColor`, `secondaryBackgroundColor`, and `textColor` — but not font-family or card border styles. CSS injection is necessary for the full earthy theme.

### Pattern 3: Anthropic Streaming via Generator Wrapper
**What:** `st.write_stream()` must receive a generator that yields strings. The Anthropic SDK `.stream()` context manager's `text_stream` attribute is exactly this.
**When to use:** Page 4 recipe generation.
**Example:**
```python
# Source: Streamlit GitHub issue #8963 + Anthropic SDK docs
import anthropic
import streamlit as st

def stream_recipe(client, prompt: str):
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text

# In page:
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
response_text = st.write_stream(stream_recipe(client, prompt))
```

**Do NOT** pass the stream object directly to `st.write_stream()` — it yields raw JSON events, not strings.

### Pattern 4: PyVis Graph Rendering
**What:** Build a `pyvis.network.Network` in Python, call `.generate_html()` (or `.save_graph()` to temp file), pass the HTML string to `st.components.v1.html()`.
**When to use:** Page 3 graph rendering.
**Example:**
```python
from pyvis.network import Network
import streamlit.components.v1 as components

net = Network(height="600px", width="100%", bgcolor="#fdf6ec", font_color="#2d1b0e")
net.set_options("""{ "physics": { "barnesHut": { "gravitationalConstant": -8000 } } }""")

# Add nodes and edges
net.add_node(center_id, size=40, color="#c4622a", label=center_name)
for pair in top_pairs[:49]:
    net.add_node(pair.id, size=10 + pair.score * 20, label=pair.name)
    edge_color = "#d62728" if pair.surprise_score > 0.6 else "#1f77b4"
    net.add_edge(center_id, pair.id, color=edge_color)

html_content = net.generate_html()
components.html(html_content, height=620, scrolling=False)
```

### Pattern 5: Plotly Radar Chart (Dual Polygon)
**What:** Two `go.Scatterpolar` traces on a single `go.Figure` — one per ingredient.
**When to use:** Inside each search result expander on Page 1.
**Example:**
```python
# Source: plotly.com/python/radar-chart/
import plotly.graph_objects as go

categories = ["Sweet", "Sour", "Umami", "Bitter", "Floral", "Smoky"]

fig = go.Figure()
fig.add_trace(go.Scatterpolar(
    r=ingredient_a_values + [ingredient_a_values[0]],
    theta=categories + [categories[0]],
    fill="toself",
    fillcolor="rgba(196, 98, 42, 0.2)",
    line=dict(color="#c4622a"),
    name=ingredient_a_name,
))
fig.add_trace(go.Scatterpolar(
    r=ingredient_b_values + [ingredient_b_values[0]],
    theta=categories + [categories[0]],
    fill="toself",
    fillcolor="rgba(74, 124, 78, 0.15)",
    line=dict(color="#4a7c4e", dash="dot"),
    name=ingredient_b_name,
))
fig.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
    showlegend=True,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=20, r=20, t=20, b=20),
    height=250,
)
st.plotly_chart(fig, use_container_width=True)
```

### Anti-Patterns to Avoid
- **Passing `stream` object to `st.write_stream`:** Yields JSON blocks, not readable text. Always use `stream.text_stream` in a generator.
- **Calling `st.cache_resource.clear()` globally:** This clears ALL cached resources including embeddings. Call `load_scored_pairs.clear()` (function-level) after fine-tuning.
- **Using `st.cache_data` for model objects:** `@st.cache_data` pickles/unpickles on every read. Heavy objects (embeddings dict, model) belong in `@st.cache_resource`.
- **Building PyVis graph outside a function:** Graph construction with 50 nodes is fast but should be inside a function (not `@st.cache_resource`) since it depends on the selected center ingredient which changes per interaction.
- **Accessing `ANTHROPIC_API_KEY` with `os.environ["KEY"]`:** Raises `KeyError` if missing. Use `os.environ.get("ANTHROPIC_API_KEY")` and show `st.error` if None.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Interactive network graph | Custom D3 or canvas graph | PyVis + components.html | PyVis wraps vis.js; physics layout, hover tooltips, zoom all built in |
| Radar chart | Matplotlib polar plot | `go.Scatterpolar` | Plotly renders natively in Streamlit; matplotlib needs `st.pyplot()` and loses interactivity |
| Token streaming display | Manual st.empty() loop | `st.write_stream()` | Handles buffering, progressive rendering, and final value capture |
| CSS theme | Streamlit config.toml only | CSS injection via `st.markdown` | config.toml cannot set font-family, card styles, or pill colors |
| Active learning gate check | Re-implement AUC check | `is_active_learning_enabled()` from Phase 5 | Phase 5 owns this logic; UI only calls it |

**Key insight:** Streamlit handles all the browser-server communication complexity. The app is stateless per rerun — all "state" lives in `st.session_state` or `@st.cache_resource`.

---

## Common Pitfalls

### Pitfall 1: PyVis Click Events Do Not Communicate to Python (CRITICAL)
**What goes wrong:** The CONTEXT.md spec says "click a node to re-center graph on that ingredient (handled via PyVis click events → st.session_state)". PyVis click events exist in the vis.js frontend but `st.components.v1.html` has no return value and no session state bridge. Attempting to use `window.parent.postMessage` with `streamlit:setSessionState` does not work in `st.components.v1.html` — confirmed by official Streamlit docs ("does not return values") and community discussion.
**Why it happens:** `st.components.v1.html` is a display-only iframe. Bidirectional communication requires a formally declared custom component (separate npm build). PyVis issue #85 (open since 2022) confirms native Python click callbacks are not implemented.
**How to avoid:** The click-to-pivot behavior must be implemented using a `st.selectbox` above the graph. When the user clicks a node in the PyVis graph (which works fine in the browser for visual highlighting), they then select that ingredient from the selectbox to pivot — Streamlit reruns and re-renders the graph centered on the new ingredient. The selectbox is the _actual_ pivot control; the graph's built-in click behavior provides visual feedback only.
**Warning signs:** If the plan calls for "JavaScript postMessage to Python" or "PyVis click callback", flag for redesign.

### Pitfall 2: st.write_stream + Anthropic SDK JSON Output
**What goes wrong:** Passing the stream manager object directly to `st.write_stream()` outputs raw JSON event blocks instead of text.
**Why it happens:** Streamlit's `st.write_stream` iterates whatever generator it receives. The Anthropic stream object yields `MessageStreamEvent` objects (dicts), not strings.
**How to avoid:** Always wrap in a generator that iterates `stream.text_stream` and yields strings. See Pattern 3 above.
**Warning signs:** Output displays `{"type": "content_block_delta", ...}` on the page.

### Pitfall 3: Cache Not Cleared After Fine-Tuning
**What goes wrong:** After active learning fine-tuning re-exports `scored_pairs.pkl`, the app still serves stale cached data from before the fine-tune.
**Why it happens:** `@st.cache_resource` caches the return value of the loader function. The file on disk changes, but Python never re-calls the function.
**How to avoid:** Call `get_scored_pairs.clear()` (not `st.cache_resource.clear()`) immediately after `submit_rating()` returns. The next page access will reload from the updated file.
**Warning signs:** AUC delta shown correctly but pairing results haven't changed after rating submission.

### Pitfall 4: Mutating Cached Resource Objects
**What goes wrong:** Code modifies a dict or list returned by a `@st.cache_resource` function, permanently altering the cached object for all future calls.
**Why it happens:** `@st.cache_resource` returns the same object (singleton). Unlike `@st.cache_data`, it does not copy.
**How to avoid:** Treat objects from `@st.cache_resource` as read-only. If filtering or slicing is needed, do it on a copy: `pairs = list(get_scored_pairs()[:10])`.

### Pitfall 5: PyVis Height Mismatch
**What goes wrong:** PyVis generates HTML with its own internal height declaration; `st.components.v1.html(height=...)` cuts off the graph or adds unwanted scrollbars.
**Why it happens:** Both PyVis and the Streamlit component wrapper independently set heights.
**How to avoid:** Set `height=` consistently in both the `Network(height="600px")` constructor and `components.html(height=620)`. Add a few pixels buffer in the component height.

### Pitfall 6: Missing Upstream Files at App Startup
**What goes wrong:** App crashes with `FileNotFoundError` on import or at top of page if `scoring/scored_pairs.pkl` doesn't exist (pipeline hasn't run).
**Why it happens:** Phase 5 must complete before Phase 6 is useful. During development, files may be missing.
**How to avoid:** All data loading must be inside `try/except FileNotFoundError`. Show `st.warning("Run the pipeline first: python run_pipeline.py")` and `st.stop()` to halt page rendering gracefully.

---

## Code Examples

### Cache Resource with Clear Pattern
```python
# app/utils/cache.py
import streamlit as st
from pathlib import Path
import pickle

SCORED_PAIRS_PATH = Path("scoring/scored_pairs.pkl")

@st.cache_resource
def load_scored_pairs_cached():
    if not SCORED_PAIRS_PATH.exists():
        return None
    with open(SCORED_PAIRS_PATH, "rb") as f:
        return pickle.load(f)

def invalidate_scored_pairs():
    load_scored_pairs_cached.clear()
```

### Error Guard Pattern (UI-07)
```python
# Top of every page
try:
    pairs = load_scored_pairs_cached()
    if pairs is None:
        st.warning("Pipeline hasn't run yet. Execute: python run_pipeline.py")
        st.stop()
    # ... page content ...
except Exception as e:
    st.error(f"Something went wrong loading the ingredient data. ({type(e).__name__})")
    st.stop()
```

### Active Learning Gate Check (UI-03)
```python
from model.active_learning import is_active_learning_enabled

enabled, current_auc = is_active_learning_enabled()
if not enabled:
    st.warning(f"Active learning requires AUC ≥ 0.70. Current AUC: {current_auc:.3f}. "
               "Complete model training first.")
    st.stop()
```

### Session State for Graph Pivot (UI-04 Workaround)
```python
# 3_Graph.py
import streamlit as st

# Initialize session state for selected ingredient
if "graph_center" not in st.session_state:
    st.session_state.graph_center = None

all_ingredients = [p.ingredient_name for p in get_scored_pairs()]
selected = st.selectbox(
    "Center ingredient",
    all_ingredients,
    key="graph_center",
)
# Graph renders below using selected as center; changing selectbox causes rerun
```

### Multiselect with Max Selection Enforcement (UI-05)
```python
# 4_Recipe.py
top_surprise = [p.ingredient_name for p in get_scored_pairs()[:20] if p.label == "Surprising"]
selected = st.multiselect("Choose 2–3 ingredients", top_surprise, max_selections=3)
if len(selected) < 2:
    st.info("Select at least 2 ingredients to generate a recipe.")
    st.stop()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pages/` directory auto-nav only | `st.Page` + `st.navigation` for custom nav | Streamlit 1.36 (2024) | More control but pages/ convention still fully supported and simpler |
| `@st.cache` (deprecated) | `@st.cache_resource` / `@st.cache_data` | Streamlit 1.18 (2022) | Never use `@st.cache` — removed |
| `st.experimental_rerun()` | `st.rerun()` | Streamlit 1.27 (2023) | `experimental_rerun` is removed |
| Manual streaming loop with `st.empty()` | `st.write_stream()` | Streamlit 1.31 (2023) | Use `write_stream` for all LLM streaming |

**Deprecated/outdated:**
- `st.cache`: Removed. Use `@st.cache_resource` for objects, `@st.cache_data` for serializable data.
- `st.experimental_rerun`: Use `st.rerun()`.
- `net.show(filename)` for PyVis: Writes to disk; use `net.generate_html()` instead for in-memory string (avoids temp file management).

---

## Open Questions

1. **`net.generate_html()` availability in pyvis 0.3.x**
   - What we know: The PyVis docs reference `show()` which writes to a file. Community examples use temp files (`Path("graph.html")`).
   - What's unclear: Whether `generate_html()` is present in 0.3.x or if a temp file approach is needed.
   - Recommendation: Plan should use temp file approach (`net.save_graph("/tmp/graph.html"); html = open(...).read()`) as the safe fallback, and attempt `generate_html()` first.

2. **Flavor profile vector availability for radar chart**
   - What we know: FEAT-08 specifies a multi-hot flavor profile vector per ingredient (sweet/sour/umami/bitter/floral/smoky). This lives in scored_pairs or must be loaded separately.
   - What's unclear: Whether the scored_pairs payload from Phase 5 includes the 6-dim flavor profile or if a separate lookup is needed.
   - Recommendation: Plan for Page 1 should include loading `data/processed/features.parquet` as a fallback if flavor profile is not in scored_pairs. Phase 5 planning should expose this in the API.

3. **`st.multiselect` max_selections parameter**
   - What we know: The CONTEXT.md specifies max 3 selections.
   - What's unclear: Whether `max_selections` is available in Streamlit 1.55. It was added in 1.27 — almost certainly present.
   - Recommendation: HIGH confidence this exists; planner should add `max_selections=3` to the multiselect call.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x |
| Config file | none (discovered by pytest default) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | Page 1 renders top 10 pairings for searched ingredient | smoke | `pytest tests/test_ui_search.py -x` | ❌ Wave 0 |
| UI-02 | "Why it works" section present in search results | smoke | `pytest tests/test_ui_search.py::test_why_it_works -x` | ❌ Wave 0 |
| UI-03 | Page 2 shows 5 uncertain pairs, accepts ratings, triggers fine-tune, shows AUC delta | smoke | `pytest tests/test_ui_rate.py -x` | ❌ Wave 0 |
| UI-04 | Page 3 renders PyVis graph with ≤50 nodes centered on ingredient | unit | `pytest tests/test_ui_graph.py -x` | ❌ Wave 0 |
| UI-05 | Page 4 streaming recipe includes molecular rationale | manual-only | N/A — requires ANTHROPIC_API_KEY and live API | N/A |
| UI-06 | @st.cache_resource used; cache cleared after fine-tune | unit | `pytest tests/test_ui_cache.py -x` | ❌ Wave 0 |
| UI-07 | No raw tracebacks on page load with missing files | smoke | `pytest tests/test_ui_errors.py -x` | ❌ Wave 0 |

**UI-05 manual-only justification:** Recipe generation requires a live Anthropic API call. Mocking the SDK is possible but would only test the wrapper, not the actual streaming behavior. The success criterion ("recipe is readable and references specific shared compounds") is inherently subjective. Test by manual review during verification.

### Recommended Test Approach
The Streamlit app pages cannot be unit-tested in the traditional sense (they are scripts, not importable functions). The practical approach:

1. **Extract testable logic into utility functions** in `app/utils/` — e.g., `build_pyvis_graph(center, pairs)` returns a `Network` object; testable independently.
2. **Test the utility functions** in `tests/test_ui_*.py` — graph node/edge counts, cache clear behavior, error guard logic.
3. **Smoke-test page imports** — `import importlib; importlib.import_module("app.pages.1_Search")` to confirm no syntax errors or import failures.

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ui_search.py` — covers UI-01, UI-02 (search page utility functions)
- [ ] `tests/test_ui_rate.py` — covers UI-03 (rating submission, gate check)
- [ ] `tests/test_ui_graph.py` — covers UI-04 (graph builder: node count, edge colors)
- [ ] `tests/test_ui_cache.py` — covers UI-06 (cache clear after fine-tune)
- [ ] `tests/test_ui_errors.py` — covers UI-07 (friendly error when files missing)
- [ ] `app/utils/__init__.py` — package init for utility module imports
- [ ] Framework install: `pip install streamlit plotly pyvis anthropic` — if not yet in environment.yml

---

## Sources

### Primary (HIGH confidence)
- [Streamlit pages/ directory docs](https://docs.streamlit.io/develop/concepts/multipage-apps/pages-directory) — naming conventions, sorting, auto-sidebar
- [st.cache_resource docs](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource) — API, `.clear()`, mutation caveat
- [st.components.v1.html docs](https://docs.streamlit.io/develop/api-reference/custom-components/st.components.v1.html) — no return value, height/scrolling params
- [Plotly radar chart docs](https://plotly.com/python/radar-chart/) — `go.Scatterpolar` dual-trace pattern
- [Streamlit 2026 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) — 1.55.0 confirmed latest

### Secondary (MEDIUM confidence)
- [Streamlit GitHub issue #8963](https://github.com/streamlit/streamlit/issues/8963) — `st.write_stream` + Anthropic JSON output; generator workaround
- [PyVis GitHub issue #85](https://github.com/WestHealth/pyvis/issues/85) — click event callbacks not implemented; open since 2022
- [st.components.html session state forum thread](https://discuss.streamlit.io/t/how-can-i-set-value-to-session-state-from-st-components-html/86755) — confirmed: postMessage does not work; formal component required
- [PyVis tutorial](https://pyvis.readthedocs.io/en/latest/tutorial.html) — `add_node`, `add_edge`, `set_options`, `show` API

### Tertiary (LOW confidence)
- Anthropic SDK version 0.84.0 — from STATE.md decision log; not independently verified against PyPI

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against PyPI/official docs
- Architecture: HIGH — patterns from official Streamlit docs
- PyVis click workaround: MEDIUM — confirmed limitation via issue tracker + docs; workaround is established community practice
- Anthropic streaming: HIGH — confirmed via GitHub issue + SDK docs
- Pitfalls: HIGH — all confirmed with official sources or open issues

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable libraries; Streamlit moves fast but pages/ convention is stable)
