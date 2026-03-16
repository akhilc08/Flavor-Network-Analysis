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


from api.routes.search import router as search_router
fastapi_app.include_router(search_router)

from api.routes.rate import router as rate_router
fastapi_app.include_router(rate_router)
