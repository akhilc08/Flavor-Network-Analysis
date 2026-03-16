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
