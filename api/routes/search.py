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
