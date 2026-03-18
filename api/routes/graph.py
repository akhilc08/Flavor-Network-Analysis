from __future__ import annotations
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from api.deps import load_all_data

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

router = APIRouter()

LABEL_EDGE_COLOR = {
    "Surprising": "#c4622a",
    "Unexpected": "#b8860b",
    "Classic": "#8b9dc3",
}


@router.get("/graph")
def graph(center: str, max_nodes: int = 50, min_score: float = 0.0):
    data = load_all_data()
    center_lower = center.strip().lower()
    df = data["scored_pairs"]
    mask = (df["ingredient_a"] == center_lower) | (df["ingredient_b"] == center_lower)
    pairs = df[mask].head(max_nodes).to_dict(orient="records")
    if not pairs:
        raise HTTPException(status_code=404, detail=f"Ingredient '{center}' not found.")

    pairs = [p for p in pairs if float(p.get("surprise_score", 0)) >= min_score]

    def partner(p):
        a = p.get("ingredient_a", "")
        b = p.get("ingredient_b", "")
        return b if a == center_lower else a

    degree: dict[str, int] = {}
    for p in pairs:
        nb = partner(p)
        degree[nb] = degree.get(nb, 0) + 1

    max_degree = max(degree.values(), default=1)

    nodes = [{"id": center_lower, "label": center_lower, "size": 18, "center": True}]
    seen = {center_lower}
    for p in pairs:
        nb = partner(p)
        if nb and nb not in seen:
            size = 8 + int(8 * degree.get(nb, 1) / max_degree)
            nodes.append({"id": nb, "label": nb, "size": size, "center": False})
            seen.add(nb)

    edges = []
    for p in pairs:
        nb = partner(p)
        if nb in seen:
            label = p.get("label", "Classic")
            edges.append({
                "source": center_lower,
                "target": nb,
                "weight": round(float(p.get("surprise_score", 0)), 4),
                "label": label,
                "color": LABEL_EDGE_COLOR.get(label, "#8b9dc3"),
            })

    return {"nodes": nodes, "edges": edges}
