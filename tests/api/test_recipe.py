# tests/api/test_recipe.py
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

def make_client():
    with patch("api.deps.load_all_data", return_value={
        "embeddings": {}, "scored_pairs": [], "mol_lookup": {},
    }):
        from api.main import fastapi_app
        return TestClient(fastapi_app)

def test_recipe_streams():
    client = make_client()
    payload = {
        "ingredients": ["strawberry", "miso"],
        "shared_molecules": ["furaneol"],
        "flavor_labels": {"strawberry × miso": "Surprising"},
    }
    mock_stream = MagicMock()
    mock_stream.__enter__ = lambda s: s
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.text_stream = iter(["Hello ", "world"])

    with patch("anthropic.Anthropic") as mock_anthropic, \
         patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        mock_anthropic.return_value.messages.stream.return_value = mock_stream
        resp = client.post("/recipe", json=payload)
    assert resp.status_code == 200
    assert b"Hello" in resp.content

def test_recipe_requires_two_ingredients():
    client = make_client()
    payload = {"ingredients": ["strawberry"], "shared_molecules": [], "flavor_labels": {}}
    resp = client.post("/recipe", json=payload)
    assert resp.status_code == 422
