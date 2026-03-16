# Next.js Migration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate FlavorNet from Streamlit to Next.js + FastAPI on Modal/Vercel, preserving the editorial earthy design.

**Architecture:** FastAPI (Modal ASGI web endpoint) wraps existing ML code; Next.js (Vercel, App Router) consumes those endpoints. All runtime data on a Modal Volume `flavornet-data`. Next.js is deployed to Vercel with root directory `web/`.

**Tech Stack:** Next.js 14 (App Router), TypeScript, Tailwind CSS, `@react-sigma/core` + `sigma`, `react-markdown`; FastAPI, Modal, Python 3.11

**Spec:** `docs/superpowers/specs/2026-03-15-nextjs-migration-design.md`

---

## Chunk 1: Backend

### Task 0: Dev dependencies

**Files:**
- Create: `requirements-dev.txt`

- [ ] **Step 1: Create `requirements-dev.txt`**

```
pytest
httpx
fastapi[standard]
pydantic
anthropic
pandas
pyarrow
torch
scikit-learn
numpy
```

- [ ] **Step 2: Install**

```bash
pip install -r requirements-dev.txt
```

- [ ] **Step 3: Commit**

```bash
git add requirements-dev.txt
git commit -m "chore: add dev/test dependencies"
```

---

### Task 1: Volume upload script

**Files:**
- Create: `scripts/upload_volume.py`

- [ ] **Step 1: Write the script**

```python
"""
One-off script to populate the flavornet-data Modal Volume with local artifacts.
Run: modal run scripts/upload_volume.py
"""
import modal
from pathlib import Path

app = modal.App("flavornet-upload")
volume = modal.Volume.from_name("flavornet-data", create_if_missing=True)

LOCAL_FILES = [
    # (local_path, volume_path)
    ("model/embeddings/ingredient_embeddings.pkl", "ingredient_embeddings.pkl"),
    ("scoring/scored_pairs.pkl", "scored_pairs.pkl"),
    ("data/processed/ingredient_molecule.parquet", "ingredient_molecule.parquet"),
    ("logs/training_metadata.json", "training_metadata.json"),
    ("feedback.csv", "feedback.csv"),
    ("data/processed/hetero_data.pt", "graph/hetero_data.pt"),
    ("data/processed/val_edges.pt", "graph/val_edges.pt"),
    ("model/checkpoints/best_model.pt", "model/checkpoints/best_model.pt"),
    ("model/replay_buffer.pkl", "model/replay_buffer.pkl"),
]


@app.function(volumes={"/data": volume})
def upload():
    import shutil
    import os
    for local_path, volume_path in LOCAL_FILES:
        src = Path(local_path)
        if not src.exists():
            print(f"  SKIP (not found): {local_path}")
            continue
        dst = Path("/data") / volume_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  OK: {local_path} -> /data/{volume_path}")
    volume.commit()
    print("Volume committed.")


@app.local_entrypoint()
def main():
    upload.remote()
```

- [ ] **Step 2: Verify local artifacts exist**

```bash
ls model/embeddings/ingredient_embeddings.pkl \
   scoring/scored_pairs.pkl \
   data/processed/ingredient_molecule.parquet
```
Expected: all three files present (others may be missing on a fresh clone — that's fine, the script skips them).

- [ ] **Step 3: Commit**

```bash
git add scripts/upload_volume.py
git commit -m "feat: add Modal Volume upload script"
```

---

### Task 2: FastAPI app skeleton + health endpoint

**Files:**
- Create: `api/__init__.py`
- Create: `api/main.py`
- Create: `api/deps.py`
- Create: `api/routes/__init__.py`
- Create: `tests/api/test_health.py`

`api/deps.py` holds startup-loaded state (embeddings, scored_pairs, molecules) shared across routes via FastAPI `Depends`.

- [ ] **Step 1: Write the failing test**

```python
# tests/api/test_health.py
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

def make_client():
    """Import app after patching heavy deps."""
    with patch("api.deps.load_all_data"):
        from api.main import fastapi_app
        return TestClient(fastapi_app)

def test_health_returns_200():
    client = make_client()
    resp = client.get("/health")
    assert resp.status_code == 200

def test_health_returns_auc():
    client = make_client()
    with patch("builtins.open", MagicMock()), \
         patch("json.load", return_value={"best_val_auc": 0.847}):
        resp = client.get("/health")
    assert "auc" in resp.json()
```

- [ ] **Step 2: Run test — expect ImportError (module doesn't exist)**

```bash
python -m pytest tests/api/test_health.py -v 2>&1 | head -20
```

- [ ] **Step 3: Create `api/__init__.py` and `api/routes/__init__.py`** (empty files)

- [ ] **Step 4: Create `api/deps.py`**

```python
"""Shared FastAPI dependencies — loaded once at container startup."""
from __future__ import annotations
import pickle
import pandas as pd
from pathlib import Path
from functools import lru_cache

DATA_DIR = Path("/data")  # Modal Volume mount point


@lru_cache(maxsize=1)
def load_all_data() -> dict:
    """Load all runtime artifacts into memory. Called once at startup."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    with open(DATA_DIR / "ingredient_embeddings.pkl", "rb") as f:
        embeddings = pickle.load(f)

    with open(DATA_DIR / "scored_pairs.pkl", "rb") as f:
        scored_pairs = pickle.load(f)

    molecules_df = pd.read_parquet(DATA_DIR / "ingredient_molecule.parquet")
    # Build lookup: ingredient_name -> set of molecule names
    mol_lookup: dict[str, set[str]] = {}
    for _, row in molecules_df.iterrows():
        name = str(row.get("ingredient", row.get("name", ""))).lower()
        mol = str(row.get("molecule", row.get("molecule_name", "")))
        mol_lookup.setdefault(name, set()).add(mol)

    return {
        "embeddings": embeddings,
        "scored_pairs": scored_pairs,
        "mol_lookup": mol_lookup,
    }


def get_shared_molecules(a: str, b: str, mol_lookup: dict, limit: int = 5) -> list[str]:
    """Return up to `limit` molecule names shared between ingredient a and b."""
    mols_a = mol_lookup.get(a.lower(), set())
    mols_b = mol_lookup.get(b.lower(), set())
    return sorted(mols_a & mols_b)[:limit]
```

- [ ] **Step 5: Create `api/main.py`**

```python
"""FastAPI application — import this to get fastapi_app for testing or Modal deployment."""
from __future__ import annotations
import json
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent))

fastapi_app = FastAPI(title="FlavorNet API")

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.vercel.app", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@fastapi_app.get("/health")
def health():
    metadata_path = Path("/data/training_metadata.json")
    auc = 0.0
    if metadata_path.exists():
        try:
            with open(metadata_path) as f:
                auc = json.load(f).get("best_val_auc", 0.0)
        except Exception:
            pass
    return {"status": "ok", "auc": auc}


# Routes registered in subsequent tasks
```

- [ ] **Step 6: Run test — expect PASS**

```bash
python -m pytest tests/api/test_health.py -v
```
Expected: `PASSED` for both tests.

- [ ] **Step 7: Commit**

```bash
git add api/ tests/api/test_health.py
git commit -m "feat: FastAPI skeleton with /health endpoint"
```

---

### Task 3: `/search` endpoint

**Files:**
- Create: `api/routes/search.py`
- Create: `tests/api/test_search.py`
- Modify: `api/main.py` (register router)

- [ ] **Step 1: Write the failing test**

```python
# tests/api/test_search.py
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

FAKE_PAIRS = [
    {"ingredient_a": "strawberry", "ingredient_b": "miso",
     "pairing_score": 0.91, "surprise_score": 0.87, "label": "Surprising"},
    {"ingredient_a": "strawberry", "ingredient_b": "anchovy",
     "pairing_score": 0.72, "surprise_score": 0.65, "label": "Unexpected"},
]

def make_client():
    with patch("api.deps.load_all_data", return_value={
        "embeddings": {}, "scored_pairs": FAKE_PAIRS,
        "mol_lookup": {"miso": {"furaneol", "diacetyl"}, "strawberry": {"furaneol", "ethyl acetate"}},
    }):
        from api.main import fastapi_app
        return TestClient(fastapi_app)

def test_search_found():
    client = make_client()
    with patch("scoring.score.get_top_pairings", return_value=FAKE_PAIRS):
        resp = client.get("/search?q=strawberry")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ingredient"] == "strawberry"
    assert len(body["pairings"]) == 2
    assert "shared_molecules" in body["pairings"][0]

def test_search_not_found():
    client = make_client()
    with patch("scoring.score.get_top_pairings", return_value=[]):
        resp = client.get("/search?q=unknowningredient99")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test — expect 404 (route not registered)**

```bash
python -m pytest tests/api/test_search.py -v 2>&1 | head -20
```

- [ ] **Step 3: Create `api/routes/search.py`**

```python
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from api.deps import load_all_data, get_shared_molecules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

router = APIRouter()


@router.get("/search")
def search(q: str, limit: int = 10):
    from scoring.score import get_top_pairings
    data = load_all_data()
    pairs = get_top_pairings(q.strip().lower(), n=limit)
    if not pairs:
        raise HTTPException(status_code=404, detail=f"Ingredient '{q}' not found.")
    mol_lookup = data["mol_lookup"]
    pairings = []
    for p in pairs:
        b = p.get("ingredient_b", "")
        pairings.append({
            "name": b,
            "pairing_score": round(float(p.get("pairing_score", 0)), 4),
            "surprise_score": round(float(p.get("surprise_score", 0)), 4),
            "label": p.get("label", "Classic"),
            "shared_molecules": get_shared_molecules(q, b, mol_lookup),
        })
    return {"ingredient": q.strip().lower(), "pairings": pairings}
```

- [ ] **Step 4: Register router in `api/main.py`** — add after the health route:

```python
from api.routes.search import router as search_router
fastapi_app.include_router(search_router)
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/api/test_search.py -v
```
Expected: both PASS.

- [ ] **Step 6: Commit**

```bash
git add api/routes/search.py tests/api/test_search.py api/main.py
git commit -m "feat: /search endpoint"
```

---

### Task 4: `/uncertain-pairs` endpoint

**Files:**
- Create: `api/routes/rate.py` (holds both `/uncertain-pairs` and `/rate`)
- Create: `tests/api/test_rate.py`
- Modify: `api/main.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/api/test_rate.py
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import json

FAKE_PAIRS = [
    {"ingredient_a": "anchovy", "ingredient_b": "chocolate",
     "pairing_score": 0.501, "surprise_score": 0.45, "label": "Surprising"},
]

def make_client():
    with patch("api.deps.load_all_data", return_value={
        "embeddings": {}, "scored_pairs": FAKE_PAIRS,
        "mol_lookup": {"anchovy": {"trimethylamine"}, "chocolate": {"trimethylamine", "pyrazine"}},
    }):
        from api.main import fastapi_app
        return TestClient(fastapi_app)

def test_uncertain_pairs_ok(tmp_path):
    client = make_client()
    meta = tmp_path / "training_metadata.json"
    meta.write_text(json.dumps({"best_val_auc": 0.847}))
    with patch("api.routes.rate.METADATA_PATH", meta), \
         patch("model.active_learning.get_uncertain_pairs", return_value=FAKE_PAIRS):
        resp = client.get("/uncertain-pairs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["auc"] == 0.847
    assert len(body["pairs"]) == 1
    assert "shared_molecules" in body["pairs"][0]

def test_uncertain_pairs_no_metadata(tmp_path):
    client = make_client()
    missing = tmp_path / "nonexistent.json"
    with patch("api.routes.rate.METADATA_PATH", missing), \
         patch("model.active_learning.get_uncertain_pairs", return_value=FAKE_PAIRS):
        resp = client.get("/uncertain-pairs")
    assert resp.status_code == 500
```

- [ ] **Step 2: Run — expect failures**

```bash
python -m pytest tests/api/test_rate.py::test_uncertain_pairs_ok -v 2>&1 | head -10
```

- [ ] **Step 3: Create `api/routes/rate.py`** (uncertain-pairs portion only for now)

```python
from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.deps import load_all_data, get_shared_molecules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

router = APIRouter()

METADATA_PATH = Path("/data/training_metadata.json")


@router.get("/uncertain-pairs")
def uncertain_pairs():
    if not METADATA_PATH.exists():
        raise HTTPException(status_code=500, detail="Model not initialized.")
    with open(METADATA_PATH) as f:
        auc = json.load(f).get("best_val_auc", 0.0)

    from model.active_learning import get_uncertain_pairs
    raw = get_uncertain_pairs(n=5)
    data = load_all_data()
    mol_lookup = data["mol_lookup"]
    pairs = []
    for p in raw:
        a, b = p.get("ingredient_a", ""), p.get("ingredient_b", "")
        pairs.append({
            "ingredient_a": a,
            "ingredient_b": b,
            "score": round(float(p.get("pairing_score", 0.5)), 4),
            "shared_molecules": get_shared_molecules(a, b, mol_lookup),
        })
    return {"auc": round(float(auc), 4), "pairs": pairs}
```

- [ ] **Step 4: Register router in `api/main.py`**

```python
from api.routes.rate import router as rate_router
fastapi_app.include_router(rate_router)
```

- [ ] **Step 5: Run uncertain-pairs tests**

```bash
python -m pytest tests/api/test_rate.py::test_uncertain_pairs_ok tests/api/test_rate.py::test_uncertain_pairs_no_metadata -v
```
Expected: both PASS.

---

### Task 5: `/rate` endpoint

- [ ] **Step 1: Write failing test**

```python
# append to tests/api/test_rate.py

def test_rate_submit(tmp_path):
    client = make_client()
    # Write metadata file: first read returns auc_before, second (after fine-tune) returns auc_after
    meta = tmp_path / "training_metadata.json"
    meta.write_text(json.dumps({"best_val_auc": 0.847}))

    payload = {"ratings": [
        {"ingredient_a": "anchovy", "ingredient_b": "chocolate", "rating": 4}
    ]}

    def fake_submit(a, b, r):
        # Simulate fine-tune updating the file
        meta.write_text(json.dumps({"best_val_auc": 0.861}))

    with patch("api.routes.rate.METADATA_PATH", meta), \
         patch("model.active_learning.submit_rating", side_effect=fake_submit):
        resp = client.post("/rate", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["auc_before"] == 0.847
    assert body["auc_after"] == 0.861
    assert abs(body["delta"] - 0.014) < 0.001
```

- [ ] **Step 2: Run — expect failure**

```bash
python -m pytest tests/api/test_rate.py::test_rate_submit -v 2>&1 | head -10
```

- [ ] **Step 3: Add `/rate` route to `api/routes/rate.py`**

```python
class RatingItem(BaseModel):
    ingredient_a: str
    ingredient_b: str
    rating: int  # 1-5

class RateRequest(BaseModel):
    ratings: list[RatingItem]


@router.post("/rate")
def rate(body: RateRequest):
    if not METADATA_PATH.exists():
        raise HTTPException(status_code=500, detail="Model not initialized.")
    with open(METADATA_PATH) as f:
        auc_before = json.load(f).get("best_val_auc", 0.0)

    from model.active_learning import submit_rating
    for item in body.ratings:
        submit_rating(item.ingredient_a, item.ingredient_b, item.rating)

    # Re-read updated metadata
    with open(METADATA_PATH) as f:
        auc_after = json.load(f).get("best_val_auc", auc_before)

    return {
        "auc_before": round(float(auc_before), 4),
        "auc_after": round(float(auc_after), 4),
        "delta": round(float(auc_after - auc_before), 4),
    }
```

- [ ] **Step 4: Run all rate tests**

```bash
python -m pytest tests/api/test_rate.py -v
```
Expected: all 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add api/routes/rate.py tests/api/test_rate.py api/main.py
git commit -m "feat: /uncertain-pairs and /rate endpoints"
```

---

### Task 6: `/graph` endpoint

**Files:**
- Create: `api/routes/graph.py`
- Create: `tests/api/test_graph.py`
- Modify: `api/main.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/api/test_graph.py
from unittest.mock import patch
from fastapi.testclient import TestClient

FAKE_PAIRS = [
    {"ingredient_a": "strawberry", "ingredient_b": "miso",
     "surprise_score": 0.87, "label": "Surprising"},
    {"ingredient_a": "strawberry", "ingredient_b": "anchovy",
     "surprise_score": 0.45, "label": "Classic"},
]

def make_client():
    with patch("api.deps.load_all_data", return_value={
        "embeddings": {}, "scored_pairs": FAKE_PAIRS, "mol_lookup": {},
    }):
        from api.main import fastapi_app
        return TestClient(fastapi_app)

def test_graph_nodes_and_edges():
    client = make_client()
    with patch("scoring.score.get_top_pairings", return_value=FAKE_PAIRS):
        resp = client.get("/graph?center=strawberry")
    assert resp.status_code == 200
    body = resp.json()
    assert any(n["id"] == "strawberry" and n.get("center") for n in body["nodes"])
    assert len(body["edges"]) >= 1

def test_graph_not_found():
    client = make_client()
    with patch("scoring.score.get_top_pairings", return_value=[]):
        resp = client.get("/graph?center=unknownthing99")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run — expect failures**

```bash
python -m pytest tests/api/test_graph.py -v 2>&1 | head -10
```

- [ ] **Step 3: Create `api/routes/graph.py`**

```python
from __future__ import annotations
import math
from fastapi import APIRouter, HTTPException
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

router = APIRouter()

LABEL_EDGE_COLOR = {
    "Surprising": "#c4622a",
    "Unexpected": "#b8860b",
    "Classic": "#8b9dc3",
}


@router.get("/graph")
def graph(center: str, max_nodes: int = 50, min_score: float = 0.0):
    from scoring.score import get_top_pairings
    pairs = get_top_pairings(center.strip().lower(), n=max_nodes)
    if not pairs:
        raise HTTPException(status_code=404, detail=f"Ingredient '{center}' not found.")

    pairs = [p for p in pairs if float(p.get("surprise_score", 0)) >= min_score]

    # Degree map for sizing non-center nodes
    degree: dict[str, int] = {}
    for p in pairs:
        b = p.get("ingredient_b", "")
        degree[b] = degree.get(b, 0) + 1

    max_degree = max(degree.values(), default=1)

    nodes = [{"id": center, "label": center, "size": 18, "center": True}]
    seen = {center}
    for p in pairs:
        b = p.get("ingredient_b", "")
        if b and b not in seen:
            size = 8 + int(8 * degree.get(b, 1) / max_degree)
            nodes.append({"id": b, "label": b, "size": size, "center": False})
            seen.add(b)

    edges = []
    for p in pairs:
        b = p.get("ingredient_b", "")
        if b in seen:
            label = p.get("label", "Classic")
            edges.append({
                "source": center,
                "target": b,
                "weight": round(float(p.get("surprise_score", 0)), 4),
                "label": label,
                "color": LABEL_EDGE_COLOR.get(label, "#8b9dc3"),
            })

    return {"nodes": nodes, "edges": edges}
```

- [ ] **Step 4: Register in `api/main.py`**

```python
from api.routes.graph import router as graph_router
fastapi_app.include_router(graph_router)
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/api/test_graph.py -v
```
Expected: both PASS.

- [ ] **Step 6: Commit**

```bash
git add api/routes/graph.py tests/api/test_graph.py api/main.py
git commit -m "feat: /graph endpoint"
```

---

### Task 7: `/recipe` SSE endpoint + Modal deploy wrapper

**Files:**
- Create: `api/routes/recipe.py`
- Create: `tests/api/test_recipe.py`
- Create: `api/modal_app.py` (Modal wrapper — separate from `main.py` so tests can import `main.py` cleanly)
- Modify: `api/main.py`

- [ ] **Step 1: Write failing test**

```python
# tests/api/test_recipe.py
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

def make_client():
    with patch("api.deps.load_all_data", return_value={
        "embeddings": {}, "scored_pairs": [], "mol_lookup": {},
    }):
        from api.main import fastapi_app
        return TestClient(fastapi_app)

def test_recipe_streams():
    client = make_client()
    payload = {
        "ingredients": ["strawberry", "miso"],
        "shared_molecules": ["furaneol"],
        "flavor_labels": {"strawberry × miso": "Surprising"},
    }
    mock_stream = MagicMock()
    mock_stream.__enter__ = lambda s: s
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.text_stream = iter(["Hello ", "world"])

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.stream.return_value = mock_stream
        resp = client.post("/recipe", json=payload)
    assert resp.status_code == 200
    assert b"Hello" in resp.content

def test_recipe_requires_two_ingredients():
    client = make_client()
    payload = {"ingredients": ["strawberry"], "shared_molecules": [], "flavor_labels": {}}
    resp = client.post("/recipe", json=payload)
    assert resp.status_code == 422
```

- [ ] **Step 2: Run — expect failures**

```bash
python -m pytest tests/api/test_recipe.py -v 2>&1 | head -10
```

- [ ] **Step 3: Create `api/routes/recipe.py`**

```python
from __future__ import annotations
import os
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

router = APIRouter()

RECIPE_SYSTEM = (
    "You are a culinary scientist and chef. Write for curious food lovers "
    "who appreciate both great cooking and the science behind it."
)


class RecipeRequest(BaseModel):
    ingredients: list[str]
    shared_molecules: list[str]
    flavor_labels: dict[str, str]

    @field_validator("ingredients")
    @classmethod
    def at_least_two(cls, v):
        if len(v) < 2:
            raise ValueError("At least 2 ingredients required.")
        return v


def _build_prompt(req: RecipeRequest) -> str:
    ing_list = ", ".join(i.title() for i in req.ingredients)
    mol_str = ", ".join(req.shared_molecules[:5]) or "(not available)"
    label_str = "; ".join(f"{k}: {v}" for k, v in req.flavor_labels.items())
    return f"""Create a recipe using these molecularly paired ingredients: {ing_list}.

Shared flavor compounds: {mol_str}.
Pairing classifications: {label_str}.

Your recipe MUST:
1. Give the dish a creative, evocative name
2. Explain in 2-3 sentences WHY these ingredients work together — reference the specific shared compounds by name
3. List all ingredients with quantities
4. Provide clear step-by-step cooking instructions (6-10 steps)
5. End with a ## Flavor Science section explaining the molecular pairing rationale in plain English

Be specific about the flavor compounds and write with confidence."""


def _stream_recipe(prompt: str):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text


@router.post("/recipe")
def recipe(req: RecipeRequest):
    prompt = _build_prompt(req)
    return StreamingResponse(_stream_recipe(prompt), media_type="text/event-stream")
```

- [ ] **Step 4: Register in `api/main.py`**

```python
from api.routes.recipe import router as recipe_router
fastapi_app.include_router(recipe_router)
```

- [ ] **Step 5: Create `api/modal_app.py`** — Modal wrapper, never imported by tests

```python
"""Modal deployment wrapper. Deploy with: modal deploy api/modal_app.py"""
import modal
from api.main import fastapi_app  # noqa: F401  imported for side-effects (route registration)

app = modal.App("flavornet-api")
volume = modal.Volume.from_name("flavornet-data")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi[standard]",
        "torch",
        "torch-geometric",
        "pandas",
        "pyarrow",
        "anthropic",
        "scikit-learn",
        "numpy",
    )
)


@app.function(
    image=image,
    volumes={"/data": volume},
    secrets=[modal.Secret.from_name("flavornet-secrets")],
    timeout=300,
)
@modal.asgi_app()
def serve():
    return fastapi_app
```

- [ ] **Step 6: Run all API tests**

```bash
python -m pytest tests/api/ -v
```
Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add api/routes/recipe.py api/modal_app.py tests/api/test_recipe.py api/main.py
git commit -m "feat: /recipe SSE endpoint + Modal deploy wrapper"
```

---

## Chunk 2: Frontend Foundation

### Task 8: Next.js project setup

**Files:**
- Create: `web/` (Next.js 14 project, App Router)
- Create: `web/tailwind.config.ts`
- Create: `web/app/globals.css`

- [ ] **Step 1: Scaffold Next.js project**

```bash
cd web && npx create-next-app@14 . \
  --typescript --tailwind --eslint --app \
  --src-dir=false --import-alias="@/*" --no-git
```
Accept all prompts. When done, `web/app/` exists.

- [ ] **Step 2: Replace `web/tailwind.config.ts`** with the full design system config

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: '#fdf6ec',
        card: '#fff8f0',
        dark: '#2d1b0e',
        accent: { DEFAULT: '#c4622a', light: '#e8845a' },
        muted: '#e8d5bc',
        green: { DEFAULT: '#4a7c4e', light: '#6aab6e' },
        blue: '#8b9dc3',
        gold: '#b8860b',
        warm: { mid: '#7a5c42', light: '#c4a882' },
      },
      fontFamily: {
        serif: ['Georgia', 'serif'],
        sans: ['system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      boxShadow: {
        card: '0 2px 8px rgba(45, 27, 14, 0.05)',
        'card-hover': '0 6px 24px rgba(45, 27, 14, 0.12)',
      },
      transitionDuration: { DEFAULT: '150ms' },
    },
  },
  plugins: [],
}

export default config
```

- [ ] **Step 3: Replace `web/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --color-bg: #fdf6ec;
  --color-card: #fff8f0;
  --color-dark: #2d1b0e;
  --color-accent: #c4622a;
  --color-accent-light: #e8845a;
  --color-muted: #e8d5bc;
  --color-green: #4a7c4e;
  --color-green-light: #6aab6e;
  --color-blue: #8b9dc3;
  --color-gold: #b8860b;
  --color-warm-mid: #7a5c42;
  --color-warm-light: #c4a882;
}

*, *::before, *::after { box-sizing: border-box; }

html { background-color: var(--color-bg); scroll-behavior: smooth; }

body {
  background-color: var(--color-bg);
  color: var(--color-dark);
  font-family: Georgia, serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

::selection { background: rgba(196, 98, 42, 0.2); }

/* Custom scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--color-bg); }
::-webkit-scrollbar-thumb { background: var(--color-muted); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--color-accent); }

/* Score bar animation */
.score-bar-fill {
  transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

/* Prose styles for recipe markdown */
.recipe-prose h1, .recipe-prose h2, .recipe-prose h3 {
  font-family: Georgia, serif;
  font-weight: 400;
  color: var(--color-dark);
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  line-height: 1.25;
}
.recipe-prose h1 { font-size: 1.5rem; }
.recipe-prose h2 { font-size: 1.25rem; border-top: 1px solid var(--color-muted); padding-top: 1.25em; }
.recipe-prose p { line-height: 1.7; margin-bottom: 0.875em; color: var(--color-dark); }
.recipe-prose ul, .recipe-prose ol { padding-left: 1.5em; margin-bottom: 1em; }
.recipe-prose li { margin-bottom: 0.375em; line-height: 1.65; }
.recipe-prose strong { font-weight: 600; color: var(--color-dark); }
.recipe-prose em { font-style: italic; color: var(--color-warm-mid); }
```

- [ ] **Step 4: Verify dev server starts**

```bash
cd web && npm run dev
```
Expected: `http://localhost:3000` loads with no errors. Stop with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
cd .. && git add web/tailwind.config.ts web/app/globals.css web/package.json web/tsconfig.json web/next.config.mjs web/postcss.config.mjs web/.eslintrc.json
git commit -m "feat: Next.js project scaffold with design system tokens"
```

---

### Task 9: Shared TypeScript types + API client

**Files:**
- Create: `web/lib/types.ts`
- Create: `web/lib/api.ts`

- [ ] **Step 1: Create `web/lib/types.ts`**

```typescript
export type PairingLabel = 'Surprising' | 'Unexpected' | 'Classic'

export interface Pairing {
  name: string
  pairing_score: number
  surprise_score: number
  label: PairingLabel
  shared_molecules: string[]
}

export interface SearchResponse {
  ingredient: string
  pairings: Pairing[]
}

export interface UncertainPair {
  ingredient_a: string
  ingredient_b: string
  score: number
  shared_molecules: string[]
}

export interface UncertainPairsResponse {
  auc: number
  pairs: UncertainPair[]
}

export interface RateRequest {
  ratings: { ingredient_a: string; ingredient_b: string; rating: number }[]
}

export interface RateResponse {
  auc_before: number
  auc_after: number
  delta: number
}

export interface GraphNode {
  id: string
  label: string
  size: number
  center: boolean
}

export interface GraphEdge {
  source: string
  target: string
  weight: number
  label: PairingLabel
  color: string
}

export interface GraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface RecipeRequest {
  ingredients: string[]
  shared_molecules: string[]
  flavor_labels: Record<string, string>
}
```

- [ ] **Step 2: Create `web/lib/api.ts`**

```typescript
const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: 'no-store' })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw Object.assign(new Error(detail.detail ?? res.statusText), { status: res.status })
  }
  return res.json()
}

export async function searchIngredient(q: string, limit = 10) {
  return get<import('./types').SearchResponse>(
    `/search?q=${encodeURIComponent(q)}&limit=${limit}`
  )
}

export async function getUncertainPairs() {
  return get<import('./types').UncertainPairsResponse>('/uncertain-pairs')
}

export async function submitRatings(body: import('./types').RateRequest) {
  const res = await fetch(`${BASE}/rate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Rate failed')
  return res.json() as Promise<import('./types').RateResponse>
}

export async function getGraph(center: string, maxNodes = 50, minScore = 0.0) {
  return get<import('./types').GraphResponse>(
    `/graph?center=${encodeURIComponent(center)}&max_nodes=${maxNodes}&min_score=${minScore}`
  )
}

export async function streamRecipe(
  body: import('./types').RecipeRequest,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
) {
  try {
    const res = await fetch(`${BASE}/recipe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok || !res.body) {
      throw new Error('Recipe stream failed')
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      onChunk(decoder.decode(value, { stream: true }))
    }
    onDone()
  } catch (e) {
    onError(e instanceof Error ? e : new Error(String(e)))
  }
}
```

- [ ] **Step 3: TypeScript check**

```bash
cd web && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
cd .. && git add web/lib/
git commit -m "feat: shared TypeScript types and API client"
```

---

### Task 10: Root layout + TopNav

**Files:**
- Create: `web/components/TopNav.tsx`
- Modify: `web/app/layout.tsx`

Visual spec:
- Background: `#2d1b0e` (dark brown), sticky, `z-50`
- Height: 48px, `border-b border-white/10`
- Left: "FlavorNet" in Georgia serif 16px, `#fdf6ec`, links to `/`
- Right nav links: Search, Rate, Graph, Recipe — uppercase, 10px, 700 weight, 0.12em letter-spacing
  - Default: `rgba(253,246,236,0.55)`
  - Active (current page): `#fdf6ec` + 1px bottom border `#c4622a`
  - Hover: `#fdf6ec`, transition 0.15s
- Max-width wrapper: 1280px, centered, `px-12`
- No hamburger or mobile collapse (out of scope per spec)

- [ ] **Step 1: Install `next/navigation` — already available in Next.js 14**

- [ ] **Step 2: Create `web/components/TopNav.tsx`**

```tsx
'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const NAV_LINKS = [
  { href: '/search', label: 'Search' },
  { href: '/rate', label: 'Rate' },
  { href: '/graph', label: 'Graph' },
  { href: '/recipe', label: 'Recipe' },
]

export default function TopNav() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-50 bg-dark border-b border-white/10">
      <nav className="mx-auto max-w-[1280px] px-12 h-12 flex items-center justify-between">
        {/* Logo */}
        <Link
          href="/"
          className="font-serif text-base text-bg tracking-tight hover:text-accent transition-colors duration-150"
        >
          FlavorNet
        </Link>

        {/* Nav links */}
        <ul className="flex items-center gap-8">
          {NAV_LINKS.map(({ href, label }) => {
            const active = pathname === href || pathname.startsWith(href + '/')
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={[
                    'font-sans text-[10px] font-bold tracking-[0.12em] uppercase',
                    'transition-colors duration-150 pb-px',
                    active
                      ? 'text-bg border-b-2 border-accent'
                      : 'text-bg/55 hover:text-bg',
                  ].join(' ')}
                >
                  {label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
    </header>
  )
}
```

- [ ] **Step 3: Update `web/app/layout.tsx`**

```tsx
import type { Metadata } from 'next'
import './globals.css'
import TopNav from '@/components/TopNav'

export const metadata: Metadata = {
  title: 'FlavorNet',
  description: 'Discover hidden flavor pairings using graph neural networks.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-bg min-h-screen">
        <TopNav />
        <main className="mx-auto max-w-[1280px] px-12 py-10">
          {children}
        </main>
      </body>
    </html>
  )
}
```

- [ ] **Step 4: Visual check — run dev server**

```bash
cd web && npm run dev
```
Navigate to `http://localhost:3000`. Confirm: dark nav bar, "FlavorNet" on left, nav links on right with correct color. Stop server.

- [ ] **Step 5: Commit**

```bash
cd .. && git add web/components/TopNav.tsx web/app/layout.tsx
git commit -m "feat: root layout and dark sticky TopNav"
```

---

### Task 11: Shared UI components

**Files:**
- Create: `web/components/ScoreBar.tsx`
- Create: `web/components/LabelPill.tsx`
- Create: `web/components/MoleculeTag.tsx`
- Create: `web/components/Skeleton.tsx`

- [ ] **Step 1: Create `web/components/ScoreBar.tsx`**

Visual spec:
- Track: 3px height, `bg-muted`, `rounded-full`
- Fill: gradient, animates from 0→value on mount using CSS transition
- Pairing fill: `linear-gradient(90deg, #c4622a, #e8845a)`
- Surprise fill: `linear-gradient(90deg, #4a7c4e, #6aab6e)`
- Label row: left label in `10px, 600 weight, 0.1em tracking, uppercase, warm-mid`, right value in `Georgia, 14px, dark`

```tsx
'use client'
import { useEffect, useState } from 'react'

interface ScoreBarProps {
  label: string
  value: number          // 0-1
  variant: 'pairing' | 'surprise'
}

const GRADIENTS = {
  pairing: 'linear-gradient(90deg, #c4622a, #e8845a)',
  surprise: 'linear-gradient(90deg, #4a7c4e, #6aab6e)',
}

export default function ScoreBar({ label, value, variant }: ScoreBarProps) {
  const [width, setWidth] = useState(0)

  useEffect(() => {
    // Defer to next frame so CSS transition fires
    const id = requestAnimationFrame(() => setWidth(value * 100))
    return () => cancelAnimationFrame(id)
  }, [value])

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between items-baseline">
        <span className="font-sans text-[10px] font-semibold tracking-[0.1em] uppercase text-warm-mid">
          {label}
        </span>
        <span className="font-serif text-sm text-dark">{value.toFixed(3)}</span>
      </div>
      <div className="h-[3px] bg-muted rounded-full overflow-hidden">
        <div
          className="h-full rounded-full score-bar-fill"
          style={{ width: `${width}%`, background: GRADIENTS[variant] }}
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `web/components/LabelPill.tsx`**

Visual spec:
- 11px, 600 weight, 0.08em tracking, uppercase, 4px 10px padding, border-radius 2px
- Surprising: green bg/text/border (`rgba(74,124,78,0.12)` / `#4a7c4e` / `rgba(74,124,78,0.25)`)
- Unexpected: gold bg/text/border
- Classic: terracotta bg/text/border

```tsx
import type { PairingLabel } from '@/lib/types'

const STYLES: Record<PairingLabel, string> = {
  Surprising: 'bg-green/10 text-green border-green/25',
  Unexpected: 'bg-gold/10 text-gold border-gold/25',
  Classic:    'bg-accent/10 text-accent border-accent/25',
}

export default function LabelPill({ label }: { label: PairingLabel }) {
  return (
    <span
      className={[
        'font-sans text-[11px] font-semibold tracking-[0.08em] uppercase',
        'px-[10px] py-1 rounded-sm border whitespace-nowrap',
        STYLES[label] ?? STYLES.Classic,
      ].join(' ')}
    >
      {label}
    </span>
  )
}
```

- [ ] **Step 3: Create `web/components/MoleculeTag.tsx`**

```tsx
export default function MoleculeTag({ name }: { name: string }) {
  return (
    <span className="font-sans text-[11px] italic text-warm-mid bg-bg border border-muted rounded-sm px-2 py-0.5 inline-block">
      {name}
    </span>
  )
}
```

- [ ] **Step 4: Create `web/components/Skeleton.tsx`**

```tsx
interface SkeletonProps {
  className?: string
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div className={`animate-pulse bg-muted/60 rounded ${className}`} />
  )
}

export function CardSkeleton() {
  return (
    <div className="bg-card border border-muted rounded p-6 flex flex-col gap-4 shadow-card">
      <div className="flex justify-between items-start">
        <Skeleton className="h-7 w-32" />
        <Skeleton className="h-5 w-20" />
      </div>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-2 w-full" />
        <Skeleton className="h-[3px] w-full" />
      </div>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-2 w-full" />
        <Skeleton className="h-[3px] w-3/4" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-5 w-16" />
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-5 w-14" />
      </div>
    </div>
  )
}

export function RatePairSkeleton() {
  return (
    <div className="bg-card border border-muted rounded p-6 flex flex-col gap-4 shadow-card mb-4">
      <div className="flex justify-between">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-5 w-16" />
      </div>
      <div className="flex gap-8">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-5 w-24" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-5 w-16" />
        <Skeleton className="h-5 w-20" />
      </div>
      <div className="flex gap-2 mt-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-7 w-7 rounded" />
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: TypeScript check**

```bash
cd web && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
cd .. && git add web/components/
git commit -m "feat: shared UI components — ScoreBar, LabelPill, MoleculeTag, Skeleton"
```

---

## Chunk 3: Frontend Pages

### Task 12: Landing page

**Files:**
- Modify: `web/app/page.tsx`

Visual spec (faithfully adapted from Streamlit `app.py`):
- **Hero**: 80px/72px padding, border-bottom `#e8d5bc`. Eyebrow "GRAPH NEURAL NETWORK · MOLECULAR GASTRONOMY" in terracotta uppercase tracking. Title: Georgia, `clamp(52px, 7vw, 88px)`, "Discover hidden *flavor pairings*" with italic em in `#c4622a`. Subhead 16px, `#7a5c42`, 520px max-width. CTA button: dark bg, cream text, uppercase, hover terracotta, translateY(-1px). SVG network decoration in top-right at 18% opacity.
- **Stats bar**: 4 columns separated by `#e8d5bc` borders. Each: Georgia 36px value, 10px uppercase label.
- **Feature grid**: 2×2 grid with 1px `#e8d5bc` gap. Each card: `#fff8f0` bg, 36px padding, numbered (01–04), title 22px Georgia, desc 13px, footer with tag pill + arrow. Hover: bg shifts to `#fdf6ec`, arrow translates.
- **Footer**: FlavorNet serif left, meta text right.

- [ ] **Step 1: Write `web/app/page.tsx`**

```tsx
import Link from 'next/link'

const STATS = [
  { value: '935',  label: 'Ingredients' },
  { value: '436k', label: 'Scored pairs' },
  { value: '128',  label: 'Embedding dims' },
  { value: 'GAT',  label: 'Model architecture' },
]

const FEATURES = [
  {
    num: '01', href: '/search', title: 'Ingredient Search',
    desc: 'Type any ingredient and surface its top molecular pairings, ranked by a surprise score that balances pairing quality against culinary familiarity.',
    tag: 'Search',
  },
  {
    num: '02', href: '/rate', title: 'Rate & Improve',
    desc: 'The model is uncertain about some pairs — those whose predicted co-occurrence score hovers near 0.5. Rate them to trigger active learning fine-tuning.',
    tag: 'Active Learning',
  },
  {
    num: '03', href: '/graph', title: 'Flavor Graph',
    desc: 'Navigate the ingredient network visually. Click any node to re-center. Edge width reflects surprise score — thicker means more unexpected.',
    tag: 'Network Explorer',
  },
  {
    num: '04', href: '/recipe', title: 'Recipe Generation',
    desc: 'Pick 2–3 surprising ingredients and generate a recipe with molecular rationale. Claude explains the chemical bridges and proposes a dish.',
    tag: 'AI Generation',
  },
]

export default function Home() {
  return (
    <div className="-mx-12 -mt-10">
      {/* ── HERO ── */}
      <section className="relative px-16 pt-20 pb-[72px] border-b border-muted overflow-hidden">
        {/* SVG network decoration */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <svg
            viewBox="0 0 600 400"
            className="absolute right-0 top-0 w-[55%] h-full opacity-[0.18]"
            xmlns="http://www.w3.org/2000/svg"
          >
            <g stroke="#c4622a" strokeWidth="1" fill="none">
              <line x1="300" y1="200" x2="480" y2="100"/>
              <line x1="300" y1="200" x2="520" y2="220"/>
              <line x1="300" y1="200" x2="450" y2="320"/>
              <line x1="300" y1="200" x2="180" y2="80"/>
              <line x1="300" y1="200" x2="150" y2="280"/>
              <line x1="300" y1="200" x2="420" y2="180"/>
              <line x1="300" y1="200" x2="370" y2="310"/>
              <line x1="480" y1="100" x2="520" y2="220"/>
              <line x1="480" y1="100" x2="420" y2="180"/>
              <line x1="450" y1="320" x2="520" y2="220"/>
              <line x1="450" y1="320" x2="370" y2="310"/>
              <line x1="180" y1="80"  x2="420" y2="180"/>
              <line x1="150" y1="280" x2="370" y2="310"/>
              <line x1="100" y1="160" x2="180" y2="80"/>
              <line x1="100" y1="160" x2="150" y2="280"/>
              <line x1="560" y1="340" x2="520" y2="220"/>
              <line x1="560" y1="340" x2="450" y2="320"/>
            </g>
            <g fill="#c4622a">
              <circle cx="300" cy="200" r="7"/>
              <circle cx="480" cy="100" r="5"/>
              <circle cx="520" cy="220" r="4"/>
              <circle cx="450" cy="320" r="5"/>
              <circle cx="180" cy="80"  r="4"/>
              <circle cx="150" cy="280" r="4"/>
              <circle cx="420" cy="180" r="3.5"/>
              <circle cx="370" cy="310" r="3.5"/>
              <circle cx="100" cy="160" r="3"/>
              <circle cx="560" cy="340" r="3"/>
            </g>
          </svg>
        </div>

        <p className="font-sans text-[10px] font-bold tracking-[0.18em] uppercase text-accent mb-5">
          Graph Neural Network &middot; Molecular Gastronomy
        </p>
        <h1 className="font-serif font-normal text-dark leading-none tracking-[-0.03em] mb-6"
            style={{ fontSize: 'clamp(52px, 7vw, 88px)' }}>
          Discover hidden<br />
          <em className="not-italic text-accent">flavor pairings</em>
        </h1>
        <p className="font-sans text-base text-warm-mid leading-[1.7] max-w-[520px] mb-11">
          A graph neural network trained on flavor chemistry surfaces ingredient
          combinations that are scientifically compatible but culinarily underexplored.
          Explore the molecular bridges between unexpected ingredients.
        </p>
        <div className="flex gap-4">
          <Link href="/search"
            className="inline-flex items-center gap-2.5 bg-dark text-bg font-sans text-[11px] font-bold tracking-[0.12em] uppercase px-7 py-3.5 rounded-[3px] transition-all duration-150 hover:bg-accent hover:-translate-y-px"
          >
            Start Exploring <span className="text-sm">→</span>
          </Link>
          <Link href="/graph"
            className="inline-flex items-center gap-2.5 bg-transparent text-dark border border-muted font-sans text-[11px] font-bold tracking-[0.12em] uppercase px-7 py-3.5 rounded-[3px] transition-all duration-150 hover:border-accent hover:text-accent hover:-translate-y-px"
          >
            Explore Graph
          </Link>
        </div>
      </section>

      {/* ── STATS BAR ── */}
      <div className="flex border-b border-muted">
        {STATS.map((s, i) => (
          <div key={i} className={`flex-1 px-10 py-7 ${i < STATS.length - 1 ? 'border-r border-muted' : ''}`}>
            <div className="font-serif text-[36px] font-normal text-dark leading-none mb-1.5">{s.value}</div>
            <div className="font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-warm-mid">{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── FEATURES ── */}
      <section className="px-16 pt-14 pb-16">
        <p className="font-serif text-[11px] tracking-[0.14em] uppercase text-warm-mid mb-8">What you can do</p>
        <div className="grid grid-cols-2 gap-px bg-muted border border-muted rounded overflow-hidden">
          {FEATURES.map((f) => (
            <Link
              key={f.href}
              href={f.href}
              className="group bg-card p-9 pb-8 flex flex-col gap-3 no-underline hover:bg-bg transition-colors duration-150"
            >
              <div className="font-sans text-[10px] font-bold tracking-[0.14em] uppercase text-accent">{f.num}</div>
              <div className="font-serif text-[22px] font-normal text-dark leading-snug">{f.title}</div>
              <p className="font-sans text-[13px] text-warm-mid leading-[1.65] flex-1">{f.desc}</p>
              <div className="flex items-center justify-between pt-4 mt-1 border-t border-muted">
                <span className="font-sans text-[10px] font-semibold tracking-[0.1em] uppercase text-accent bg-accent/8 border border-accent/20 px-2.5 py-0.5 rounded-sm">
                  {f.tag}
                </span>
                <span className="text-[18px] text-accent transition-transform duration-150 group-hover:translate-x-1">→</span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="px-16 py-6 border-t border-muted flex items-center justify-between">
        <span className="font-serif text-sm text-warm-mid">FlavorNet</span>
        <span className="font-sans text-[11px] text-warm-light tracking-[0.04em]">
          Graph Neural Network &middot; Flavor Chemistry &middot; Active Learning
        </span>
      </footer>
    </div>
  )
}
```

- [ ] **Step 2: Visual check**

```bash
cd web && npm run dev
```
Navigate to `http://localhost:3000`. Verify: dark nav, hero title with italic terracotta "flavor pairings", SVG network in background, stats bar, 2×2 feature grid, footer. All hover states work.

- [ ] **Step 3: Commit**

```bash
cd .. && git add web/app/page.tsx
git commit -m "feat: landing page — hero, stats, feature grid"
```

---

### Task 13: Search page

**Files:**
- Create: `web/app/search/page.tsx`
- Create: `web/components/ResultCard.tsx`

Visual spec for `ResultCard`:
- `bg-card`, `border border-muted`, `rounded`, `p-7 pb-6`, `shadow-card`
- Hover: `shadow-card-hover`, `translate-y-[-2px]`, transition 0.15s
- Header row: ingredient name in Georgia 26px dark; label pill top-right
- Two ScoreBars (pairing then surprise)
- Molecule tags in a flex-wrap row; "No shared molecules" in italic warm-mid if empty
- Bottom italic serif sentence from `format_why_it_works` equivalent (just join molecules into a prose note)

- [ ] **Step 1: Create `web/components/ResultCard.tsx`**

```tsx
import type { Pairing } from '@/lib/types'
import ScoreBar from './ScoreBar'
import LabelPill from './LabelPill'
import MoleculeTag from './MoleculeTag'

function whyItWorks(molecules: string[]): string {
  if (!molecules.length) return ''
  if (molecules.length === 1) return `Both share the compound ${molecules[0]}.`
  const last = molecules[molecules.length - 1]
  const rest = molecules.slice(0, -1).join(', ')
  return `Both contain ${rest} and ${last}, bridging their flavor profiles.`
}

export default function ResultCard({ pairing }: { pairing: Pairing }) {
  return (
    <div className="group bg-card border border-muted rounded p-7 pb-6 flex flex-col gap-4 shadow-card transition-all duration-150 hover:shadow-card-hover hover:-translate-y-0.5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-serif text-[26px] font-normal text-dark leading-[1.15]">
          {pairing.name.charAt(0).toUpperCase() + pairing.name.slice(1)}
        </h3>
        <div className="mt-1 flex-shrink-0">
          <LabelPill label={pairing.label} />
        </div>
      </div>

      {/* Score bars */}
      <ScoreBar label="Pairing Score" value={pairing.pairing_score} variant="pairing" />
      <ScoreBar label="Surprise Score" value={pairing.surprise_score} variant="surprise" />

      {/* Molecules */}
      <div className="flex flex-wrap gap-1.5">
        {pairing.shared_molecules.length > 0
          ? pairing.shared_molecules.map((m) => <MoleculeTag key={m} name={m} />)
          : <span className="font-sans text-[11px] italic text-warm-light">No shared molecules</span>
        }
      </div>

      {/* Why it works */}
      {pairing.shared_molecules.length > 0 && (
        <p className="font-serif text-[13px] italic text-warm-mid leading-relaxed pt-3 border-t border-muted">
          {whyItWorks(pairing.shared_molecules)}
        </p>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create `web/app/search/page.tsx`**

```tsx
'use client'
import { useState, useRef } from 'react'
import ResultCard from '@/components/ResultCard'
import { CardSkeleton } from '@/components/Skeleton'
import { searchIngredient } from '@/lib/api'
import type { SearchResponse } from '@/lib/types'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleSearch(q: string) {
    const trimmed = q.trim()
    if (!trimmed) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await searchIngredient(trimmed)
      setResult(data)
    } catch (e: any) {
      setError(e.status === 404
        ? `Ingredient "${trimmed}" not found. Try another name.`
        : 'Something went wrong. Please try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="font-serif text-[32px] font-normal text-dark mb-1">Ingredient Search</h1>
        <p className="font-sans text-[13px] text-warm-mid tracking-[0.02em]">
          Molecular gastronomy &middot; Top 10 pairings ranked by surprise
        </p>
      </div>

      {/* Search input */}
      <form
        onSubmit={(e) => { e.preventDefault(); handleSearch(query) }}
        className="flex gap-3 mb-10"
      >
        <div className="flex-1 relative">
          <label className="block font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-warm-mid mb-1.5">
            Find pairings for any ingredient
          </label>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. strawberry, miso, cardamom"
            className="w-full font-serif text-base text-dark bg-card border-[1.5px] border-muted rounded px-3.5 py-2.5 outline-none transition-all duration-150 focus:border-accent focus:shadow-[0_0_0_2px_rgba(196,98,42,0.12)] placeholder:text-warm-light"
          />
        </div>
        <button
          type="submit"
          disabled={!query.trim() || loading}
          className="self-end font-sans text-[11px] font-bold tracking-[0.08em] uppercase text-bg bg-accent px-6 py-2.5 rounded border-none cursor-pointer transition-colors duration-150 hover:bg-accent/80 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Search
        </button>
      </form>

      {/* Loading state */}
      {loading && (
        <div>
          <div className="h-10 w-64 bg-muted/60 animate-pulse rounded mb-6" />
          <div className="grid grid-cols-2 gap-6">
            {Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="font-serif text-[15px] italic text-warm-mid py-6">{error}</p>
      )}

      {/* Results */}
      {result && (
        <div>
          <div className="flex items-baseline justify-between pb-4 mb-6 border-b border-muted">
            <h2 className="font-serif text-[28px] font-normal text-dark">
              Pairings for{' '}
              <em className="not-italic text-accent">{result.ingredient.charAt(0).toUpperCase() + result.ingredient.slice(1)}</em>
            </h2>
            <span className="font-sans text-[13px] text-warm-mid">{result.pairings.length} results</span>
          </div>
          <div className="grid grid-cols-2 gap-6">
            {result.pairings.map((p) => (
              <ResultCard key={p.name} pairing={p} />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && !result && (
        <p className="font-serif text-[15px] italic text-warm-mid py-6">
          Enter an ingredient above to explore its flavor pairings.
        </p>
      )}
    </>
  )
}
```

- [ ] **Step 3: Visual check — run dev server**

```bash
cd web && npm run dev
```
Search "strawberry" (against a running backend or mock). Verify: 2-column card grid, hairline score bars animate in, label pills correct colors, molecule tags italic. Card hover lifts with shadow.

- [ ] **Step 4: Commit**

```bash
cd .. && git add web/components/ResultCard.tsx web/app/search/
git commit -m "feat: search page with animated result cards"
```

---

### Task 14: Rate page + StarRating component

**Files:**
- Create: `web/components/StarRating.tsx`
- Create: `web/components/PairCard.tsx`
- Create: `web/app/rate/page.tsx`

Visual spec for `StarRating`:
- 5 stars, each 28px, gap 6px
- Empty: `#e8d5bc`, Filled: `#c4622a`, Hover-fill (previewing): `#e8845a`
- Uses `★` (U+2605) as filled, `☆` (U+2606) as empty — but we render using SVG stars for crisp rendering OR use the unicode chars in Georgia serif at 28px
- Click sets rating. Hover previews fill from 1 to hovered index.
- `rating=0` means unrated (all empty, slightly faded)

- [ ] **Step 1: Create `web/components/StarRating.tsx`**

```tsx
'use client'
import { useState } from 'react'

interface StarRatingProps {
  value: number          // 0–5, 0 = unrated
  onChange: (v: number) => void
}

export default function StarRating({ value, onChange }: StarRatingProps) {
  const [hover, setHover] = useState(0)

  return (
    <div className="flex gap-1.5" onMouseLeave={() => setHover(0)}>
      {Array.from({ length: 5 }, (_, i) => {
        const star = i + 1
        const filled = hover > 0 ? star <= hover : star <= value
        const isHoverFill = hover > 0 && star <= hover

        return (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            onMouseEnter={() => setHover(star)}
            className="text-[28px] leading-none cursor-pointer bg-transparent border-none p-0 transition-transform duration-75 hover:scale-110"
            style={{
              color: isHoverFill ? '#e8845a' : filled ? '#c4622a' : '#e8d5bc',
              fontFamily: 'Georgia, serif',
            }}
            aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
          >
            {filled ? '★' : '☆'}
          </button>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: Create `web/components/PairCard.tsx`**

```tsx
import type { UncertainPair } from '@/lib/types'
import StarRating from './StarRating'
import MoleculeTag from './MoleculeTag'

interface PairCardProps {
  pair: UncertainPair
  rating: number
  onRate: (v: number) => void
}

export default function PairCard({ pair, rating, onRate }: PairCardProps) {
  const name_a = pair.ingredient_a.charAt(0).toUpperCase() + pair.ingredient_a.slice(1)
  const name_b = pair.ingredient_b.charAt(0).toUpperCase() + pair.ingredient_b.slice(1)

  return (
    <div className="bg-card border border-muted rounded p-6 flex flex-col gap-4 shadow-card mb-4">
      {/* Pair name */}
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-serif text-[22px] font-normal text-dark leading-snug">
          {name_a} <span className="text-warm-mid text-base">×</span> {name_b}
        </h3>
        <div className="font-sans text-[10px] font-semibold tracking-[0.1em] uppercase text-warm-mid pt-1.5">
          Score: <span className="font-serif text-dark text-sm">{pair.score.toFixed(3)}</span>
        </div>
      </div>

      {/* Molecules */}
      {pair.shared_molecules.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {pair.shared_molecules.map((m) => <MoleculeTag key={m} name={m} />)}
        </div>
      )}

      {/* Star rating */}
      <div className="flex flex-col gap-2">
        <p className="font-sans text-[10px] font-semibold tracking-[0.1em] uppercase text-warm-mid">
          Your rating
        </p>
        <StarRating value={rating} onChange={onRate} />
        {rating === 0 && (
          <p className="font-sans text-[11px] italic text-warm-light">Not yet rated</p>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create `web/app/rate/page.tsx`**

```tsx
'use client'
import { useEffect, useState } from 'react'
import PairCard from '@/components/PairCard'
import { RatePairSkeleton } from '@/components/Skeleton'
import { getUncertainPairs, submitRatings } from '@/lib/api'
import type { UncertainPairsResponse, RateResponse } from '@/lib/types'

export default function RatePage() {
  const [data, setData] = useState<UncertainPairsResponse | null>(null)
  const [ratings, setRatings] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<RateResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getUncertainPairs()
      .then(setData)
      .catch(() => setError('Rating unavailable — model not initialized.'))
      .finally(() => setLoading(false))
  }, [])

  function pairKey(a: string, b: string) { return `${a}|${b}` }

  async function handleSubmit() {
    if (!data) return
    const ratingItems = data.pairs.map((p) => ({
      ingredient_a: p.ingredient_a,
      ingredient_b: p.ingredient_b,
      rating: ratings[pairKey(p.ingredient_a, p.ingredient_b)] ?? 0,
    })).filter((r) => r.rating > 0)
    if (!ratingItems.length) return

    setSubmitting(true)
    setResult(null)
    try {
      const res = await submitRatings({ ratings: ratingItems })
      setResult(res)
      setRatings({})
    } catch {
      setError('Submission failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const ratedCount = Object.values(ratings).filter((v) => v > 0).length

  return (
    <>
      {/* Page header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="font-serif text-[32px] font-normal text-dark mb-1">Rate Uncertain Pairs</h1>
          <p className="font-sans text-[13px] text-warm-mid tracking-[0.02em]">
            Active learning &middot; Help the model improve
          </p>
        </div>
        {data && (
          <div className="text-right">
            <div className="font-sans text-[10px] font-semibold tracking-[0.1em] uppercase text-warm-mid mb-1">Model AUC</div>
            <div className="font-serif text-[28px] text-dark leading-none">{data.auc.toFixed(3)}</div>
          </div>
        )}
      </div>

      {/* Intro */}
      {data && (
        <p className="font-sans text-[13px] text-warm-mid leading-relaxed mb-6 max-w-[640px]">
          These {data.pairs.length} pairs sit closest to the model&apos;s decision boundary (score ≈ 0.5).
          Your ratings give it signal to improve.
        </p>
      )}

      {/* Loading */}
      {loading && Array.from({ length: 5 }).map((_, i) => <RatePairSkeleton key={i} />)}

      {/* Error */}
      {error && (
        <div className="bg-accent/8 border border-accent/25 rounded p-5">
          <p className="font-sans text-[12px] font-semibold tracking-[0.08em] uppercase text-accent mb-1">Unavailable</p>
          <p className="font-sans text-[13px] text-warm-mid">{error}</p>
        </div>
      )}

      {/* Pairs */}
      {data && !error && (
        <>
          {data.pairs.map((pair) => (
            <PairCard
              key={pairKey(pair.ingredient_a, pair.ingredient_b)}
              pair={pair}
              rating={ratings[pairKey(pair.ingredient_a, pair.ingredient_b)] ?? 0}
              onRate={(v) => setRatings((r) => ({ ...r, [pairKey(pair.ingredient_a, pair.ingredient_b)]: v }))}
            />
          ))}

          <hr className="border-muted my-6" />

          <button
            onClick={handleSubmit}
            disabled={ratedCount === 0 || submitting}
            className="font-sans text-[11px] font-bold tracking-[0.08em] uppercase text-bg bg-accent px-8 py-3 rounded border-none cursor-pointer transition-colors duration-150 hover:bg-accent/80 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-3"
          >
            {submitting ? (
              <>
                <span className="w-4 h-4 border-2 border-bg/30 border-t-bg rounded-full animate-spin" />
                Fine-tuning… ~30s
              </>
            ) : (
              `Submit Ratings${ratedCount > 0 ? ` (${ratedCount})` : ''}`
            )}
          </button>
        </>
      )}

      {/* Result */}
      {result && (
        <div className="mt-8 bg-card border border-muted rounded p-6 flex gap-12">
          <div>
            <div className="font-sans text-[10px] font-semibold tracking-[0.1em] uppercase text-warm-mid mb-1">AUC Before</div>
            <div className="font-serif text-[32px] text-dark leading-none">{result.auc_before.toFixed(4)}</div>
          </div>
          <div>
            <div className="font-sans text-[10px] font-semibold tracking-[0.1em] uppercase text-warm-mid mb-1">AUC After</div>
            <div className="font-serif text-[32px] text-dark leading-none">{result.auc_after.toFixed(4)}</div>
          </div>
          <div>
            <div className="font-sans text-[10px] font-semibold tracking-[0.1em] uppercase text-warm-mid mb-1">Delta</div>
            <div className={`font-serif text-[32px] leading-none ${result.delta >= 0 ? 'text-green' : 'text-accent'}`}>
              {result.delta >= 0 ? '+' : ''}{result.delta.toFixed(4)}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
```

- [ ] **Step 4: Visual check — star hover states**

Run dev server. Navigate to `/rate`. Verify skeleton loaders appear, then (with backend) pairs load with star rating inputs. Hover over stars shows amber preview fill. Clicking selects. Submit button shows spinner when submitting.

- [ ] **Step 5: Commit**

```bash
cd .. && git add web/components/StarRating.tsx web/components/PairCard.tsx web/app/rate/
git commit -m "feat: rate page with star rating inputs and AUC delta display"
```

---

### Task 15: Graph page + Sigma.js

**Files:**
- Create: `web/components/FlavorGraph.tsx`
- Create: `web/app/graph/page.tsx`

Visual spec:
- Install: `npm install sigma graphology @react-sigma/core`
- Layout: two-panel. Left sidebar 280px: controls (center input, sliders, stats, legend). Right panel: full remaining width, full viewport height minus nav (calc(100vh - 48px)).
- Center node: terracotta `#c4622a`, larger (node size × 3)
- Other nodes: dark `#2d1b0e`, text label in Georgia 11px
- Surprising edges: `#c4622a`, other edges: `#8b9dc3`
- Edge size: `weight * 3` (capped at 5)
- Sigma background: `#fdf6ec` (matches page)
- Click node → API re-fetch with that node as center
- Sidebar legend: colored dot + label for each edge type

- [ ] **Step 1: Install Sigma**

```bash
cd web && npm install sigma graphology @react-sigma/core
```

- [ ] **Step 2: Create `web/components/FlavorGraph.tsx`**

```tsx
'use client'
import { useEffect, useRef } from 'react'
import Sigma from 'sigma'
import Graph from 'graphology'
import type { GraphResponse } from '@/lib/types'

interface Props {
  data: GraphResponse
  onNodeClick: (nodeId: string) => void
}

export default function FlavorGraph({ data, onNodeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sigmaRef = useRef<Sigma | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    // Build graphology graph
    const graph = new Graph()
    data.nodes.forEach((n) => {
      graph.addNode(n.id, {
        label: n.label,
        size: n.center ? n.size * 2.5 : Math.max(6, n.size),
        color: n.center ? '#c4622a' : '#2d1b0e',
        x: Math.random(),
        y: Math.random(),
      })
    })
    data.edges.forEach((e) => {
      if (graph.hasNode(e.source) && graph.hasNode(e.target)) {
        graph.addEdge(e.source, e.target, {
          color: e.color,
          size: Math.min(5, e.weight * 4),
          label: e.label,
        })
      }
    })

    // Apply simple circular layout
    const nodes = graph.nodes()
    const total = nodes.length
    if (total === 0) return
    nodes.forEach((id, i) => {
      const node = graph.getNodeAttributes(id)
      if (node.color === '#c4622a') {
        // center node at origin
        graph.setNodeAttribute(id, 'x', 0)
        graph.setNodeAttribute(id, 'y', 0)
      } else {
        const angle = (2 * Math.PI * i) / Math.max(1, total - 1)
        const radius = 1 + Math.random() * 0.4
        graph.setNodeAttribute(id, 'x', Math.cos(angle) * radius)
        graph.setNodeAttribute(id, 'y', Math.sin(angle) * radius)
      }
    })

    sigmaRef.current = new Sigma(graph, containerRef.current, {
      defaultNodeColor: '#2d1b0e',
      defaultEdgeColor: '#e8d5bc',
      labelFont: 'Georgia, serif',
      labelSize: 11,
      labelWeight: '400',
      labelColor: { color: '#2d1b0e' },
      renderEdgeLabels: false,
      nodeReducer: (node, data) => ({ ...data }),
      edgeReducer: (edge, data) => ({ ...data }),
    })

    sigmaRef.current.on('clickNode', ({ node }) => {
      onNodeClick(node)
    })

    return () => {
      sigmaRef.current?.kill()
      sigmaRef.current = null
    }
  }, [data])  // eslint-disable-line react-hooks/exhaustive-deps

  return <div ref={containerRef} className="w-full h-full" style={{ background: '#fdf6ec' }} />
}
```

- [ ] **Step 3: Create `web/app/graph/page.tsx`**

```tsx
'use client'
import { useState, useEffect, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { getGraph } from '@/lib/api'
import type { GraphResponse } from '@/lib/types'

const FlavorGraph = dynamic(() => import('@/components/FlavorGraph'), { ssr: false })

const LEGEND = [
  { color: '#c4622a', label: 'Surprising' },
  { color: '#b8860b', label: 'Unexpected' },
  { color: '#8b9dc3', label: 'Classic' },
]

export default function GraphPage() {
  const [center, setCenter] = useState('strawberry')
  const [input, setInput] = useState('strawberry')
  const [maxNodes, setMaxNodes] = useState(50)
  const [minScore, setMinScore] = useState(0)
  const [graphData, setGraphData] = useState<GraphResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchGraph = useCallback(async (c: string) => {
    setLoading(true)
    setError(null)
    try {
      const data = await getGraph(c, maxNodes, minScore / 100)
      setGraphData(data)
    } catch (e: any) {
      setError(e.status === 404 ? `"${c}" not found.` : 'Failed to load graph.')
    } finally {
      setLoading(false)
    }
  }, [maxNodes, minScore])

  useEffect(() => { fetchGraph(center) }, [center, maxNodes, minScore])  // eslint-disable-line

  function handleNodeClick(nodeId: string) {
    setCenter(nodeId)
    setInput(nodeId)
  }

  return (
    <div className="flex -mx-12 -mt-10" style={{ height: 'calc(100vh - 48px)' }}>
      {/* ── LEFT SIDEBAR ── */}
      <aside className="w-[280px] flex-shrink-0 border-r border-muted bg-card flex flex-col gap-6 p-6 overflow-y-auto">
        <div>
          <h1 className="font-serif text-[22px] font-normal text-dark mb-0.5">Flavor Graph</h1>
          <p className="font-sans text-[11px] text-warm-mid tracking-[0.02em]">Click any node to re-center</p>
        </div>

        {/* Center input */}
        <div>
          <label className="block font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-warm-mid mb-1.5">
            Center Ingredient
          </label>
          <form onSubmit={(e) => { e.preventDefault(); setCenter(input) }} className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="flex-1 font-serif text-sm text-dark bg-bg border border-muted rounded px-3 py-1.5 outline-none focus:border-accent transition-colors duration-150"
            />
            <button
              type="submit"
              className="font-sans text-[10px] font-bold tracking-[0.08em] uppercase text-bg bg-accent px-3 py-1.5 rounded border-none cursor-pointer hover:bg-accent/80 transition-colors duration-150"
            >
              Go
            </button>
          </form>
        </div>

        {/* Min score */}
        <div>
          <label className="block font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-warm-mid mb-1.5">
            Min Surprise Score: <span className="font-serif text-dark">{(minScore / 100).toFixed(2)}</span>
          </label>
          <input type="range" min={0} max={80} value={minScore}
            onChange={(e) => setMinScore(+e.target.value)}
            className="w-full accent-accent"
          />
        </div>

        {/* Max nodes */}
        <div>
          <label className="block font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-warm-mid mb-1.5">
            Max Nodes: <span className="font-serif text-dark">{maxNodes}</span>
          </label>
          <input type="range" min={10} max={100} value={maxNodes}
            onChange={(e) => setMaxNodes(+e.target.value)}
            className="w-full accent-accent"
          />
        </div>

        {/* Stats */}
        {graphData && (
          <div className="flex gap-6 pt-2 border-t border-muted">
            <div>
              <div className="font-sans text-[10px] font-semibold tracking-[0.1em] uppercase text-warm-mid mb-0.5">Nodes</div>
              <div className="font-serif text-[20px] text-dark leading-none">{graphData.nodes.length}</div>
            </div>
            <div>
              <div className="font-sans text-[10px] font-semibold tracking-[0.1em] uppercase text-warm-mid mb-0.5">Edges</div>
              <div className="font-serif text-[20px] text-dark leading-none">{graphData.edges.length}</div>
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="pt-2 border-t border-muted">
          <p className="font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-warm-mid mb-3">Legend</p>
          <div className="flex flex-col gap-2">
            {LEGEND.map((l) => (
              <div key={l.label} className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: l.color }} />
                <span className="font-sans text-[12px] text-warm-mid">{l.label}</span>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* ── GRAPH CANVAS ── */}
      <div className="flex-1 relative">
        {loading && (
          <div className="absolute inset-0 bg-bg/80 flex items-center justify-center z-10">
            <div className="flex flex-col items-center gap-3">
              <div className="w-6 h-6 border-2 border-muted border-t-accent rounded-full animate-spin" />
              <span className="font-sans text-[12px] text-warm-mid">Building graph…</span>
            </div>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="font-serif text-[15px] italic text-warm-mid">{error}</p>
          </div>
        )}
        {graphData && !error && (
          <FlavorGraph data={graphData} onNodeClick={handleNodeClick} />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Visual check**

Run dev server. Navigate to `/graph`. Verify: sidebar on left, graph canvas fills remaining space, loading spinner appears, nodes render with correct colors, clicking a node re-fetches.

- [ ] **Step 5: Commit**

```bash
cd .. && git add web/components/FlavorGraph.tsx web/app/graph/
git commit -m "feat: graph page with Sigma.js WebGL renderer and click-to-pivot"
```

---

### Task 16: Recipe page

**Files:**
- Create: `web/app/recipe/page.tsx`

Visual spec:
- Ingredient selector: search input → live `GET /search` call → dropdown results; selected ingredients shown as chips with `×` remove button
- Chips: `bg-card border border-muted rounded-full px-4 py-1.5 font-serif text-sm text-dark` + label pill
- Shared molecules panel: shown when ≥2 ingredients selected; molecules from intersecting `/search` results already in state
- Generate button: full-width terracotta, disabled if <2 ingredients selected or streaming
- Stream output: rendered in `.recipe-prose` div (uses globals.css prose styles); text accumulates in real-time
- Flavor Science callout: detected when `## Flavor Science` appears in accumulated text; last section rendered in a special green-tinted box with left border

- [ ] **Step 1: Install react-markdown**

```bash
cd web && npm install react-markdown
```

- [ ] **Step 2: Create `web/app/recipe/page.tsx`**

```tsx
'use client'
import { useState, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import LabelPill from '@/components/LabelPill'
import MoleculeTag from '@/components/MoleculeTag'
import { searchIngredient, streamRecipe } from '@/lib/api'
import type { Pairing, PairingLabel } from '@/lib/types'

interface SelectedIngredient {
  name: string
  label: PairingLabel
  pairings: Pairing[]  // full /search results, for shared mol computation
}

export default function RecipePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Pairing[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [selected, setSelected] = useState<SelectedIngredient[]>([])
  const [streaming, setStreaming] = useState(false)
  const [recipeText, setRecipeText] = useState('')
  const [streamDone, setStreamDone] = useState(false)
  const [genError, setGenError] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Debounced live search for ingredient selector
  const handleSearchInput = useCallback((q: string) => {
    setSearchQuery(q)
    setDropdownOpen(true)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!q.trim()) { setSearchResults([]); return }
    debounceRef.current = setTimeout(async () => {
      setSearchLoading(true)
      try {
        const res = await searchIngredient(q.trim())
        setSearchResults(res.pairings.slice(0, 8))
      } catch { setSearchResults([]) }
      finally { setSearchLoading(false) }
    }, 300)
  }, [])

  function addIngredient(pairing: Pairing) {
    const name = pairing.name
    if (selected.find((s) => s.name === name)) return
    setSelected((prev) => [...prev, {
      name,
      label: pairing.label,
      pairings: searchResults,
    }])
    setSearchQuery('')
    setSearchResults([])
    setDropdownOpen(false)
  }

  function removeIngredient(name: string) {
    setSelected((prev) => prev.filter((s) => s.name !== name))
  }

  // Compute shared molecules client-side
  function getSharedMolecules(a: SelectedIngredient, b: SelectedIngredient): string[] {
    const pairingAB = a.pairings.find((p) => p.name === b.name)
    const pairingBA = b.pairings.find((p) => p.name === a.name)
    const mols = pairingAB?.shared_molecules ?? pairingBA?.shared_molecules ?? []
    return mols.slice(0, 5)
  }

  // Build all pairs for display
  const moleculePairs: { key: string; a: string; b: string; mols: string[] }[] = []
  for (let i = 0; i < selected.length; i++) {
    for (let j = i + 1; j < selected.length; j++) {
      const mols = getSharedMolecules(selected[i], selected[j])
      moleculePairs.push({
        key: `${selected[i].name}+${selected[j].name}`,
        a: selected[i].name, b: selected[j].name, mols,
      })
    }
  }

  const allSharedMols = Array.from(new Set(moleculePairs.flatMap((p) => p.mols)))

  async function handleGenerate() {
    setRecipeText('')
    setStreamDone(false)
    setGenError(null)
    setStreaming(true)
    const flavorLabels: Record<string, string> = {}
    moleculePairs.forEach((p) => {
      // Use the actual pairing label if available from search results
      const ingA = selected.find((s) => s.name === p.a)
      const labelFromSearch = ingA?.pairings.find((pair) => pair.name === p.b)?.label
      flavorLabels[`${p.a} × ${p.b}`] = labelFromSearch ?? 'Surprising'
    })
    await streamRecipe(
      {
        ingredients: selected.map((s) => s.name),
        shared_molecules: allSharedMols,
        flavor_labels: flavorLabels,
      },
      (chunk) => setRecipeText((t) => t + chunk),
      () => { setStreamDone(true); setStreaming(false) },
      (err) => { setGenError('Generation interrupted.'); setStreaming(false) },
    )
  }

  // Split recipe at ## Flavor Science
  const scienceIdx = recipeText.indexOf('## Flavor Science')
  const mainText = scienceIdx >= 0 ? recipeText.slice(0, scienceIdx) : recipeText
  const scienceText = scienceIdx >= 0 ? recipeText.slice(scienceIdx) : null

  return (
    <>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="font-serif text-[32px] font-normal text-dark mb-1">AI Recipe Generation</h1>
        <p className="font-sans text-[13px] text-warm-mid tracking-[0.02em]">
          Molecular rationale &middot; Written by Claude
        </p>
      </div>

      <div className="max-w-[780px]">
        {/* ── INGREDIENT SELECTOR ── */}
        <div className="mb-6">
          <label className="block font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-warm-mid mb-1.5">
            Add Ingredients
          </label>

          {/* Selected chips */}
          {selected.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {selected.map((s) => (
                <div key={s.name}
                  className="flex items-center gap-2 bg-card border border-muted rounded-full px-4 py-1.5"
                >
                  <LabelPill label={s.label} />
                  <span className="font-serif text-sm text-dark capitalize">{s.name}</span>
                  <button
                    onClick={() => removeIngredient(s.name)}
                    className="text-warm-mid hover:text-accent transition-colors duration-150 text-base leading-none bg-transparent border-none cursor-pointer p-0 ml-0.5"
                    aria-label={`Remove ${s.name}`}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Search input + dropdown */}
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearchInput(e.target.value)}
              onFocus={() => searchQuery && setDropdownOpen(true)}
              onBlur={() => setTimeout(() => setDropdownOpen(false), 150)}
              placeholder="Search for an ingredient…"
              className="w-full font-serif text-sm text-dark bg-card border border-muted rounded px-3.5 py-2.5 outline-none transition-all duration-150 focus:border-accent focus:shadow-[0_0_0_2px_rgba(196,98,42,0.12)] placeholder:text-warm-light"
            />
            {searchLoading && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <div className="w-3.5 h-3.5 border border-muted border-t-accent rounded-full animate-spin" />
              </div>
            )}

            {dropdownOpen && searchResults.length > 0 && (
              <ul className="absolute z-20 top-full mt-1 w-full bg-card border border-muted rounded shadow-card-hover max-h-56 overflow-y-auto">
                {searchResults.map((p) => (
                  <li key={p.name}>
                    <button
                      type="button"
                      onMouseDown={() => addIngredient(p)}
                      className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-bg transition-colors duration-100 cursor-pointer border-none bg-transparent text-left"
                    >
                      <span className="font-serif text-sm text-dark capitalize">{p.name}</span>
                      <LabelPill label={p.label} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {selected.length < 2 && (
            <p className="font-serif text-[14px] italic text-warm-mid mt-3">
              Select at least 2 ingredients to continue.
            </p>
          )}
        </div>

        {/* ── SHARED MOLECULES ── */}
        {selected.length >= 2 && moleculePairs.some((p) => p.mols.length > 0) && (
          <div className="mb-6 p-5 bg-card border border-muted rounded">
            {moleculePairs.map((pair) => pair.mols.length > 0 && (
              <div key={pair.key} className="mb-3 last:mb-0">
                <p className="font-sans text-[10px] font-semibold tracking-[0.1em] uppercase text-warm-mid mb-2 capitalize">
                  {pair.a} × {pair.b} shared molecules
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {pair.mols.map((m) => <MoleculeTag key={m} name={m} />)}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── GENERATE BUTTON ── */}
        {selected.length >= 2 && (
          <button
            onClick={handleGenerate}
            disabled={streaming || selected.length < 2}
            className="w-full font-sans text-[11px] font-bold tracking-[0.1em] uppercase text-bg bg-accent py-4 rounded border-none cursor-pointer transition-colors duration-150 hover:bg-accent/80 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-3 mb-8"
          >
            {streaming ? (
              <>
                <span className="w-4 h-4 border-2 border-bg/30 border-t-bg rounded-full animate-spin" />
                Generating…
              </>
            ) : (
              'Generate Recipe'
            )}
          </button>
        )}

        {/* ── STREAM ERROR ── */}
        {genError && (
          <p className="font-sans text-[13px] text-accent italic mb-4">{genError}</p>
        )}

        {/* ── RECIPE OUTPUT ── */}
        {recipeText && (
          <div>
            <div className="pb-4 mb-4 border-b border-muted">
              <h2 className="font-serif text-[24px] font-normal text-dark mb-1">Your Molecular Pairing Recipe</h2>
              <p className="font-sans text-[12px] text-warm-mid tracking-[0.04em]">Generated by Claude Sonnet</p>
            </div>

            {/* Main recipe body */}
            <div className="recipe-prose">
              <ReactMarkdown>{mainText}</ReactMarkdown>
            </div>

            {/* Flavor Science callout */}
            {scienceText && (
              <div className="mt-6 p-6 rounded border border-green/25 bg-green/8 border-l-4 border-l-green">
                <div className="recipe-prose">
                  <ReactMarkdown>{scienceText}</ReactMarkdown>
                </div>
              </div>
            )}

            {streaming && (
              <span className="inline-block w-0.5 h-4 bg-accent animate-pulse ml-0.5" />
            )}
          </div>
        )}
      </div>
    </>
  )
}
```

- [ ] **Step 3: Visual check**

Run dev server. Navigate to `/recipe`. Verify: search input, results dropdown with label pills, chips with × remove, shared molecules panel, generate button enabled at ≥2 selected, streaming text renders incrementally, Flavor Science section gets green callout.

- [ ] **Step 4: TypeScript check**

```bash
cd web && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
cd .. && git add web/app/recipe/ web/package.json web/package-lock.json
git commit -m "feat: recipe page with live ingredient search, chips, and SSE streaming"
```

---

## Chunk 4: Deployment

### Task 17: Vercel configuration

**Files:**
- Create: `web/vercel.json`
- Create: `.env.local.example`

- [ ] **Step 1: Create `web/vercel.json`**

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "installCommand": "npm install"
}
```

- [ ] **Step 2: Create `web/.env.local.example`**

```bash
# Copy to web/.env.local and fill in values
NEXT_PUBLIC_API_URL=https://your-modal-endpoint.modal.run
```

- [ ] **Step 3: Build check**

```bash
cd web && npm run build
```
Expected: build succeeds with no TypeScript or ESLint errors. Review any warnings.

- [ ] **Step 4: Commit**

```bash
cd .. && git add web/vercel.json web/.env.local.example
git commit -m "feat: Vercel config and env var template"
```

---

### Task 18: Deploy + smoke test

- [ ] **Step 1: Create Modal secret (if not already exists)**

```bash
modal secret create flavornet-secrets ANTHROPIC_API_KEY=sk-ant-...
```
If the secret already exists, update it: `modal secret create flavornet-secrets --force ANTHROPIC_API_KEY=sk-ant-...`

- [ ] **Step 2: Upload volume artifacts**

```bash
modal run scripts/upload_volume.py
```
Expected: prints "OK:" for each found file and "Volume committed."

- [ ] **Step 3: Deploy FastAPI to Modal**

```bash
modal deploy api/modal_app.py
```
Expected: outputs a `https://*.modal.run` URL. Copy it.

- [ ] **Step 4: Smoke test API endpoints**

```bash
export API=<modal-url>
curl "$API/health"
# Expected: {"status":"ok","auc":0.xxx}

curl "$API/search?q=strawberry"
# Expected: {"ingredient":"strawberry","pairings":[...]}

curl "$API/uncertain-pairs"
# Expected: {"auc":0.xxx,"pairs":[...]}

curl "$API/graph?center=strawberry"
# Expected: {"nodes":[...],"edges":[...]}
```

- [ ] **Step 5: Set `NEXT_PUBLIC_API_URL` in `web/.env.local`**

```bash
echo "NEXT_PUBLIC_API_URL=<modal-url>" > web/.env.local
```

- [ ] **Step 6: Run frontend against live API**

```bash
cd web && npm run dev
```
Open `http://localhost:3000`. Test each page end-to-end: search, rate, graph, recipe generate.

- [ ] **Step 7: Deploy to Vercel**

```bash
cd web && npx vercel --prod
```
In Vercel dashboard: set root directory to `web/`, add env var `NEXT_PUBLIC_API_URL=<modal-url>`.

- [ ] **Step 8: Final smoke test on production URL**

Open the Vercel production URL. Verify:
- [ ] Landing page renders with correct colors and SVG decoration
- [ ] Search returns results with animated score bars
- [ ] Rate page loads uncertain pairs with star inputs
- [ ] Graph renders Sigma.js canvas, clicking node re-centers
- [ ] Recipe page: add 2 ingredients, generate, stream renders, Flavor Science callout appears

- [ ] **Step 9: Final commit**

```bash
cd .. && git add web/.env.local.example
git commit -m "deploy: Modal API + Vercel frontend live"
```

---

## Post-migration cleanup (after validation)

Once the Next.js version is confirmed working in production:

```bash
git rm -r app/
git commit -m "chore: remove Streamlit app after Next.js migration"
```

Do NOT do this until the new version has been validated for at least one full session.
