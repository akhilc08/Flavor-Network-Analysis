from __future__ import annotations
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

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
