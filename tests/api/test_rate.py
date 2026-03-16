# tests/api/test_rate.py
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import json

FAKE_PAIRS = [
    {"ingredient_a": "anchovy", "ingredient_b": "chocolate",
     "pairing_score": 0.501, "surprise_score": 0.45, "label": "Surprising"},
]

FAKE_DATA = {
    "embeddings": {}, "scored_pairs": FAKE_PAIRS,
    "mol_lookup": {"anchovy": {"trimethylamine"}, "chocolate": {"trimethylamine", "pyrazine"}},
}

def make_client():
    with patch("api.deps.load_all_data"):
        from api.main import fastapi_app
        return TestClient(fastapi_app)

def test_uncertain_pairs_ok(tmp_path):
    client = make_client()
    meta = tmp_path / "training_metadata.json"
    meta.write_text(json.dumps({"best_val_auc": 0.847}))
    with patch("api.routes.rate.METADATA_PATH", meta), \
         patch("model.active_learning.get_uncertain_pairs", return_value=FAKE_PAIRS), \
         patch("api.routes.rate.load_all_data", return_value=FAKE_DATA):
        resp = client.get("/uncertain-pairs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["auc"] == 0.847
    assert len(body["pairs"]) == 1
    assert "shared_molecules" in body["pairs"][0]

def test_uncertain_pairs_no_metadata(tmp_path):
    client = make_client()
    missing = tmp_path / "nonexistent.json"
    with patch("api.routes.rate.METADATA_PATH", missing), \
         patch("model.active_learning.get_uncertain_pairs", return_value=FAKE_PAIRS), \
         patch("api.routes.rate.load_all_data", return_value=FAKE_DATA):
        resp = client.get("/uncertain-pairs")
    assert resp.status_code == 500

def test_rate_submit(tmp_path):
    client = make_client()
    meta = tmp_path / "training_metadata.json"
    meta.write_text(json.dumps({"best_val_auc": 0.847}))

    payload = {"ratings": [
        {"ingredient_a": "anchovy", "ingredient_b": "chocolate", "rating": 4}
    ]}

    def fake_submit(a, b, r):
        meta.write_text(json.dumps({"best_val_auc": 0.861}))

    with patch("api.routes.rate.METADATA_PATH", meta), \
         patch("model.active_learning.submit_rating", side_effect=fake_submit):
        resp = client.post("/rate", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["auc_before"] == 0.847
    assert body["auc_after"] == 0.861
    assert abs(body["delta"] - 0.014) < 0.001
