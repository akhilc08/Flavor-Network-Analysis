# tests/api/test_health.py
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

def make_client():
    """Import app after patching heavy deps."""
    with patch("api.deps.load_all_data"):
        from api.main import fastapi_app
        return TestClient(fastapi_app)

def test_health_returns_200():
    client = make_client()
    resp = client.get("/health")
    assert resp.status_code == 200

def test_health_returns_auc():
    client = make_client()
    with patch("builtins.open", MagicMock()), \
         patch("json.load", return_value={"best_val_auc": 0.847}):
        resp = client.get("/health")
    assert "auc" in resp.json()
