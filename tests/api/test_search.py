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
