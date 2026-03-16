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
│   ├── main.py                 # FastAPI app + Modal @web_endpoint
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
                         loads ingredient_embeddings.pkl once at startup
```

FastAPI loads `ingredient_embeddings.pkl` and scored pair data once at startup (Modal container warm). Subsequent requests within the same container are fast in-memory lookups.

---

## API Endpoints

All endpoints served from FastAPI on a Modal `@web_endpoint`. Base URL stored in `NEXT_PUBLIC_API_URL` Vercel env var.

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/search?q={ingredient}&limit=10` | Top pairings ranked by surprise score |
| `GET` | `/uncertain-pairs` | 5 most uncertain pairs for active learning |
| `POST` | `/rate` | Submit star ratings, trigger Modal fine-tune |
| `GET` | `/graph?center={ingredient}&max_nodes=50&min_score=0.0` | Graph nodes + edges for Sigma.js |
| `POST` | `/recipe` | Stream Claude recipe generation (SSE) |
| `GET` | `/health` | Liveness check, returns model AUC |

### Response Shapes

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

**`POST /recipe`** — Server-Sent Events stream of Claude text chunks.

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
- Each card: ingredient name, label pill (Surprising/Unexpected/Classic), surprise score bar (terracotta), pairing score bar (blue-grey), shared molecule tags (italic)

### Rate (`/rate`)
- Fetches uncertain pairs from `GET /uncertain-pairs` on load
- Displays current model AUC in top-right
- Each pair: ingredient names × separator, shared molecules, 5-star input
- Submit button: calls `POST /rate`, shows loading state (~30s fine-tune), then displays AUC delta

### Graph (`/graph`)
- Left sidebar: center ingredient input, min score slider, max nodes slider, node/edge counts, legend
- Right panel: Sigma.js graph (WebGL canvas)
- Click any node → re-fetches `GET /graph?center={clicked}` and re-renders (replaces PyVis dropdown)
- Edge color: terracotta = Surprising, blue-grey = Expected/Classic

### Recipe (`/recipe`)
- Ingredient selector: chips with remove button, "+ Add ingredient" trigger (searches via `GET /search`)
- Shared molecules panel (shown when ≥2 ingredients selected)
- Generate button: calls `POST /recipe`, streams response token-by-token into the recipe body
- Flavor Science callout box rendered after streaming completes

---

## Visual Design System

Ported directly from existing Streamlit theme. All values from `app/utils/theme.py`.

| Token | Value |
|-------|-------|
| `--color-bg` | `#f5ede0` |
| `--color-dark` | `#2d1b0e` |
| `--color-accent` | `#c4622a` |
| `--color-muted` | `#e8d5bc` |
| `--color-blue` | `#8b9dc3` |
| `--font-serif` | `Georgia, serif` |

CSS approach: Tailwind CSS with a custom theme extension for the earthy palette. Component-level styles for editorial-specific elements (hairline bars, molecule tags, label pills).

---

## Deployment

### FastAPI on Modal

`api/main.py` exposes the FastAPI app as a Modal `@web_endpoint`:

```python
import modal
from fastapi import FastAPI

app = modal.App("flavornet-api")
fastapi_app = FastAPI()

@app.function(
    image=modal.Image.debian_slim().pip_install(...),
    mounts=[modal.Mount.from_local_dir("model/embeddings", remote_path="/embeddings"),
            modal.Mount.from_local_dir("scoring", remote_path="/scoring")],
)
@modal.asgi_app()
def serve():
    return fastapi_app
```

Deploy: `modal deploy api/main.py`

### Next.js on Vercel

- Deploy `web/` directory
- Set `NEXT_PUBLIC_API_URL` to Modal endpoint URL
- No special build config needed (standard Next.js App Router)

### Environment Variables

| Variable | Where | Value |
|----------|-------|-------|
| `NEXT_PUBLIC_API_URL` | Vercel | Modal web endpoint URL |
| `ANTHROPIC_API_KEY` | Modal secret | Claude API key (recipe generation) |

---

## Error Handling

- **Cold start**: Modal container takes ~2-3s on first request. Next.js shows a loading skeleton on all data-fetching pages. No special handling needed — the skeleton covers it.
- **Search miss**: If ingredient not found in embeddings, API returns `404`. Frontend shows "Ingredient not found, try another name."
- **Rate page AUC gate**: If model AUC < 0.70, `GET /uncertain-pairs` returns `403`. Frontend shows "Model needs more training data before active learning is available."
- **Recipe stream error**: If Claude API fails mid-stream, frontend shows partial result + error notice.

---

## Out of Scope

- Authentication / user accounts
- Persisting ratings across users (feedback.csv stays local/Modal volume)
- Mobile-optimized graph view (Sigma.js works on mobile but layout not optimized)
- Dark mode
