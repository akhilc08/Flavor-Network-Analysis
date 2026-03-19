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

    import random
    data = load_all_data()
    mol_lookup = data["mol_lookup"]
    df = data["scored_pairs"]  # already has string names from deps.py
    records = df.to_dict(orient="records")
    # Take top 100 most uncertain, then randomly sample 5 so results vary each call
    records.sort(key=lambda p: abs(float(p.get("pairing_score", 0.5)) - 0.5))
    pool = records[:100]
    sample = random.sample(pool, min(5, len(pool)))
    pairs = []
    for p in sample:
        a, b = str(p.get("ingredient_a", "")), str(p.get("ingredient_b", ""))
        score = float(p.get("pairing_score", 0.5))
        pairs.append({
            "pair_id": f"{a}___{b}",
            "ingredient_a": a,
            "ingredient_b": b,
            "score": round(score, 4),
            "uncertainty": round(abs(score - 0.5), 4),
            "shared_molecules": get_shared_molecules(a, b, mol_lookup, pubchem_to_name=data.get("pubchem_to_name")),
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
