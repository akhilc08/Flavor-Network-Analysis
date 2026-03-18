from __future__ import annotations
from fastapi import APIRouter, HTTPException
from api.deps import load_all_data, get_shared_molecules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

router = APIRouter()


@router.get("/search")
def search(q: str, limit: int = 10):
    data = load_all_data()
    q_lower = q.strip().lower()
    df = data["scored_pairs"]
    mask = (df["ingredient_a"] == q_lower) | (df["ingredient_b"] == q_lower)
    pairs = df[mask].head(limit).to_dict(orient="records")
    if not pairs:
        raise HTTPException(status_code=404, detail=f"Ingredient '{q}' not found.")
    mol_lookup = data["mol_lookup"]
    pairings = []
    for p in pairs:
        # Partner could be in either column
        a = p.get("ingredient_a", "")
        b_candidate = p.get("ingredient_b", "")
        partner = b_candidate if a.lower() == q_lower else a
        pairings.append({
            "name": partner,
            "pairing_score": round(float(p.get("pairing_score", 0)), 4),
            "surprise_score": round(float(p.get("surprise_score", 0)), 4),
            "label": p.get("label", "Classic"),
            "shared_molecules": get_shared_molecules(q_lower, partner, mol_lookup),
        })
    return {"ingredient": q_lower, "pairings": pairings}
