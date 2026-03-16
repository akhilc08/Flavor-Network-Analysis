# Next.js Migration Design

**Date:** 2026-03-15
**Status:** Approved
**Scope:** Migrate Flavor Network Analysis app from Streamlit to Next.js + FastAPI

---

## Overview

Replace the Streamlit frontend with a Next.js (App Router) frontend and a FastAPI backend served via Modal web endpoint. The existing Python ML code (`model/`, `scoring/`, `graph/`) is unchanged — FastAPI wraps it with HTTP endpoints. The editorial visual design (earthy terracotta palette, Georgia serif, hairline bars) is preserved exactly.

---

## Architecture

### Repository Structure

Monorepo — everything added alongside existing Python code:

```
/
├── web/                        # Next.js app (NEW)
│   ├── app/
│   │   ├── layout.tsx          # Root layout with top nav
│   │   ├── page.tsx            # Landing page
│   │   ├── search/page.tsx
│   │   ├── rate/page.tsx
│   │   ├── graph/page.tsx
│   │   └── recipe/page.tsx
│   ├── components/
│   │   ├── TopNav.tsx
│   │   ├── ResultCard.tsx      # Pairing result card
│   │   ├── ScoreBar.tsx        # Hairline score bar
│   │   ├── MoleculeTag.tsx     # Italic molecule pill
│   │   ├── StarRating.tsx      # Interactive star input
│   │   └── FlavorGraph.tsx     # Sigma.js graph wrapper
│   └── lib/
│       ├── api.ts              # Typed API client
│       └── types.ts            # Shared TypeScript types
├── api/                        # FastAPI app (NEW)
│   ├── main.py                 # FastAPI app + Modal ASGI deployment
│   └── routes/
│       ├── search.py
│       ├── rate.py
│       ├── graph.py
│       └── recipe.py
├── model/                      # EXISTING (unchanged)
├── scoring/                    # EXISTING (unchanged)
├── graph/                      # EXISTING (unchanged)
├── data/                       # EXISTING (unchanged)
├── modal_train.py              # EXISTING (unchanged)
└── app/                        # OLD Streamlit (delete after migration)
```

### Data Flow

```
Browser → Next.js (Vercel) → FastAPI (Modal web endpoint)
                                      ↓
                         imports model/, scoring/, graph/
                         loads embeddings + scored pairs from Modal Volume
```

FastAPI loads `ingredient_embeddings.pkl` and `scored_pairs.pkl` once at container startup from a Modal Volume (see Deployment section). Subsequent requests within the same warm container are fast in-memory lookups.

### Shared Molecules

`scored_pairs.pkl` does not contain `shared_molecules`. The FastAPI search and rate routes compute this at request time by joining against `data/processed/ingredient_molecule.parquet`: for a pair `(a, b)`, shared molecules = intersection of molecule sets for ingredient a and ingredient b, limited to 5 by name. This parquet file is also stored on the Modal Volume and loaded at startup.

---

## API Endpoints

All endpoints served from FastAPI on a Modal ASGI web endpoint. Base URL stored in `NEXT_PUBLIC_API_URL` Vercel env var. CORS is configured in `api/main.py` via `CORSMiddleware` allowing the Vercel origin.

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/search?q={ingredient}&limit=10` | Top pairings ranked by surprise score |
| `GET` | `/uncertain-pairs` | 5 most uncertain pairs for active learning |
| `POST` | `/rate` | Submit star ratings, trigger Modal fine-tune |
| `GET` | `/graph?center={ingredient}&max_nodes=50&min_score=0.0` | Graph nodes + edges for Sigma.js |
| `POST` | `/recipe` | Stream Claude recipe generation (SSE) |
| `GET` | `/health` | Liveness check, returns model AUC |

### Request / Response Shapes

**`GET /search`**
```json
{
  "ingredient": "strawberry",
  "pairings": [
    {
      "name": "miso",
      "pairing_score": 0.91,
      "surprise_score": 0.87,
      "label": "Surprising",
      "shared_molecules": ["furaneol", "ethyl acetate", "diacetyl"]
    }
  ]
}
```
`shared_molecules` sourced from `ingredient_molecule.parquet` intersection at request time (up to 5 molecule names). Returns `404` if ingredient not found in embeddings.

**`GET /uncertain-pairs`**
```json
{
  "auc": 0.847,
  "pairs": [
    {
      "ingredient_a": "anchovy",
      "ingredient_b": "chocolate",
      "score": 0.501,
      "shared_molecules": ["trimethylamine", "pyrazine"]
    }
  ]
}
```
`auc` sourced by reading `training_metadata.json` directly (`json.load`) — the same way `active_learning.is_active_learning_enabled()` reads it internally. Returns `403` if the file is absent OR if AUC < 0.70 (both conditions mean active learning is not enabled). The route calls `active_learning.get_uncertain_pairs(n=5)` to retrieve pairs. `shared_molecules` same lookup as search.

**`POST /rate` — Request body**
```json
{
  "ratings": [
    { "ingredient_a": "anchovy", "ingredient_b": "chocolate", "rating": 3 },
    { "ingredient_a": "coffee",  "ingredient_b": "cardamom",  "rating": 5 }
  ]
}
```
Response:
```json
{ "auc_before": 0.847, "auc_after": 0.861, "delta": 0.014 }
```
The route reads `auc_before` from `training_metadata.json`, then loops over the ratings list calling `active_learning.submit_rating(ingredient_a, ingredient_b, rating)` for each pair. `submit_rating` is the correct public entry point — it handles appending to `feedback.csv`, loading the model, running `fine_tune_with_replay` internally, re-exporting embeddings, and re-running scoring. Do not call `fine_tune_with_replay` directly (it is an internal helper requiring pre-loaded state). After the loop completes, the route reads `auc_after` from the updated `training_metadata.json` and returns both values.

**`POST /recipe` — Request body**
```json
{
  "ingredients": ["strawberry", "miso"],
  "shared_molecules": ["furaneol", "ethyl acetate"],
  "flavor_labels": { "strawberry × miso": "Surprising" }
}
```
Response: Server-Sent Events stream. Each event is a text chunk from the Claude API stream. Frontend accumulates chunks and renders them in place. The "Flavor Science" block is part of the same streamed response — Claude is prompted to end with a `## Flavor Science` section.

**`GET /graph`**
```json
{
  "nodes": [
    { "id": "strawberry", "label": "strawberry", "size": 18, "center": true },
    { "id": "miso", "label": "miso", "size": 12 }
  ],
  "edges": [
    { "source": "strawberry", "target": "miso", "weight": 0.87, "label": "Surprising" }
  ]
}
```

---

## Frontend Pages

All pages share the root layout (`web/app/layout.tsx`) which renders the sticky dark top nav (`FLAVORNET | Search | Rate | Graph | Recipe`).

### Landing (`/`)
- Hero section: tagline, brief description, two CTAs (Try Search, Explore Graph)
- Stats bar: 935 ingredients · 436k scored pairs · 128 embedding dims · GAT
- 4-card feature grid linking to each page

### Search (`/search`)
- Text input with submit button; calls `GET /search` on submit
- Results rendered as 2-column card grid
- Each card: ingredient name, label pill (Surprising/Unexpected/Classic), pairing score bar (terracotta `#c4622a`), surprise score bar (green `#4a7c4e`), shared molecule tags (italic). Score bar colors match existing Streamlit implementation.

### Rate (`/rate`)
- Fetches uncertain pairs from `GET /uncertain-pairs` on load
- Displays current model AUC in top-right
- Each pair: ingredient names × separator, shared molecules, 5-star input (unrated = all empty stars)
- Submit button: calls `POST /rate`, shows loading state with spinner (~30s), then displays AUC before/after delta

### Graph (`/graph`)
- Left sidebar: center ingredient text input, min score slider, max nodes slider, node/edge counts, legend
- Right panel: Sigma.js graph (WebGL canvas)
- Click any node → re-fetches `GET /graph?center={clicked}` and re-renders. This replaces the Streamlit dropdown — clicking is now the primary navigation mechanism.
- Edge color: terracotta = Surprising, blue-grey = Expected/Classic

### Recipe (`/recipe`)
- Ingredient selector: selected ingredients shown as chips with remove (×) button
- "+ Add ingredient" opens a dropdown populated from the top-surprise pairs already loaded in the session (not a live search call — matches existing Streamlit behavior)
- Shared molecules panel shown when ≥2 ingredients selected (computed client-side from `/search` results already in state)
- Generate button: calls `POST /recipe` with selected ingredients + precomputed shared molecules + labels, streams response into recipe body
- Flavor Science callout box rendered when streaming completes (detected by `## Flavor Science` heading in stream)

---

## Visual Design System

Sourced directly from `app/utils/theme.py` and `.streamlit/config.toml`.

| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#fdf6ec` | Page background |
| `--color-card` | `#fff8f0` | Card backgrounds |
| `--color-dark` | `#2d1b0e` | Nav background, headings |
| `--color-accent` | `#c4622a` | Primary accent, pairing score bars |
| `--color-accent-light` | `#e8845a` | Score bar gradient end |
| `--color-muted` | `#e8d5bc` | Borders, empty bar fills |
| `--color-green` | `#4a7c4e` | Surprise score bars |
| `--color-green-light` | `#6aab6e` | Surprise score bar gradient end |
| `--color-blue` | `#8b9dc3` | Expected/Classic edge color |
| `--color-gold` | `#b8860b` | "Unexpected" label pill text/border |
| `--font-serif` | `Georgia, serif` | All body text and headings |

CSS approach: Tailwind CSS with a custom theme extension for the earthy palette. Component-level styles for editorial-specific elements (hairline bars, molecule tags, label pills).

---

## Deployment

### Data Persistence — Modal Volume

A Modal Volume named `flavornet-data` stores all runtime data files. This replaces local file mounts so files persist across container restarts and are updated after fine-tuning:

```
flavornet-data/
├── ingredient_embeddings.pkl      # Updated after training
├── scored_pairs.pkl               # Updated after scoring run
├── ingredient_molecule.parquet    # Static (from data pipeline)
├── training_metadata.json         # Updated after each fine-tune
├── feedback.csv                   # Appended after each rating submission
├── graph/hetero_data.pt           # Required by active_learning.py for fine-tuning
├── graph/val_edges.pt             # Fallback AUC source; absent = AUC silently returns 0.5
├── model/checkpoints/best_model.pt # Required by active_learning.py for fine-tuning
└── model/replay_buffer.pkl        # Required by active_learning.py for experience replay
```

All files must be present for `POST /rate` to execute fine-tuning. If `hetero_data.pt`, `best_model.pt`, or `replay_buffer.pkl` are absent, `fine_tune_with_replay()` will fail silently and return stale AUC values. Upload these on initial `modal deploy` alongside the embeddings.

On `modal deploy`, the current local versions of these files are uploaded to the Volume. After a fine-tune cycle, `active_learning.py` writes updated embeddings and metadata directly to the Volume path.

### FastAPI on Modal

`api/main.py` uses the current Modal ASGI pattern:

```python
import modal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = modal.App("flavornet-api")
volume = modal.Volume.from_name("flavornet-data")

image = modal.Image.debian_slim().pip_install(
    "fastapi", "torch", "torch-geometric", "pandas", "anthropic", ...
)

fastapi_app = FastAPI()
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.vercel.app", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.function(image=image, volumes={"/data": volume})
@modal.asgi_app()
def serve():
    return fastapi_app
```

For SSE streaming on `POST /recipe`, use FastAPI's `StreamingResponse` with `media_type="text/event-stream"`. Modal ASGI endpoints support streaming responses natively — no additional configuration needed.

Deploy: `modal deploy api/main.py`

### Next.js on Vercel

- Deploy `web/` directory (set root directory to `web/` in Vercel project settings)
- Set `NEXT_PUBLIC_API_URL` to Modal endpoint URL

### Environment Variables

| Variable | Where | Value |
|----------|-------|-------|
| `NEXT_PUBLIC_API_URL` | Vercel | Modal web endpoint URL |
| `ANTHROPIC_API_KEY` | Modal secret `flavornet-secrets` | Claude API key (recipe generation) |

---

## Error Handling

- **Cold start**: Modal container takes ~2-3s on first request. All data-fetching pages show a loading skeleton. No special handling needed beyond the skeleton.
- **Search miss**: Ingredient not found in embeddings → API returns `404`. Frontend shows "Ingredient not found, try another name."
- **Rate page AUC gate**: `GET /uncertain-pairs` returns `403` if `training_metadata.json` is absent OR AUC < 0.70. Frontend shows "Model needs more training data before active learning is available."
- **Recipe stream error**: If Claude API fails mid-stream, frontend shows partial result + "Generation interrupted" notice.
- **CORS**: Handled by `CORSMiddleware` in FastAPI. Vercel preview deploy URLs (`*.vercel.app`) are whitelisted.

---

## Out of Scope

- Authentication / user accounts
- Persisting ratings across users (feedback.csv is per-deployment on Modal Volume)
- Mobile-optimized graph view (Sigma.js works on mobile but layout not optimized)
- Dark mode
