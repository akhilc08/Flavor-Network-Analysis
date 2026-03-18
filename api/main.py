"""FastAPI application — import this to get fastapi_app for testing or Modal deployment."""
from __future__ import annotations
import json
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent))

fastapi_app = FastAPI(title="FlavorNet API")


class ForceCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            response = JSONResponse({}, status_code=200)
        else:
            try:
                response = await call_next(request)
            except Exception as exc:
                response = JSONResponse({"detail": str(exc)}, status_code=500)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response


fastapi_app.add_middleware(ForceCORSMiddleware)


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

from api.routes.graph import router as graph_router
fastapi_app.include_router(graph_router)

from api.routes.recipe import router as recipe_router
fastapi_app.include_router(recipe_router)
