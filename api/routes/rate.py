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
