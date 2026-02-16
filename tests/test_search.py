import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from typer.testing import CliRunner
import sys
import os
import json

# Add src to sys.path to import modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(project_root, "src"))
sys.path.insert(0, project_root)

from src.api.semantic_search import app
from src.cli import app as cli_app

client = TestClient(app)
runner = CliRunner()

# Mock Data
MOCK_METADATA = [
    {"book": "ISA", "chapter": 40, "verse": 1, "text": "Comfort ye...", "translation": "TOB", "ref": "ISA 40:1"},
    {"book": "JHN", "chapter": 3, "verse": 16, "text": "For God so loved...", "translation": "BJ", "ref": "JHN 3:16"}
]

MOCK_EMBEDDINGS = [[0.1, 0.2], [0.3, 0.4]] # Dummy

@pytest.fixture
def mock_models():
    with patch("src.api.semantic_search.SentenceTransformer") as MockST, \
         patch("pickle.load") as MockPickle, \
         patch("builtins.open", new_callable=MagicMock):
        
        # Mock Model
        mock_model_instance = MagicMock()
        mock_model_instance.encode.return_value = [[0.1, 0.2]] # Query embedding
        MockST.return_value = mock_model_instance
        
        # Mock Data
        MockPickle.return_value = {
            "metadata": MOCK_METADATA,
            "embeddings": MOCK_EMBEDDINGS
        }
        
        # Trigger startup manually or via TestClient with block
        with TestClient(app) as c:
            yield c, mock_model_instance

def test_search_service_endpoint(mock_models):
    client, _ = mock_models
    response = client.post("/search", json={"query": "comfort", "limit": 1})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["book"] == "ISA"

def test_search_service_filter(mock_models):
    client, _ = mock_models
    # Filter by translation
    response = client.post("/search", json={"query": "love", "limit": 10, "translation": "BJ"})
    data = response.json()
    assert all(d["translation"] == "BJ" for d in data)


def test_cli_regression_legacy_command():
    """Test that 'biblecli Lc 9:54' still works (via default read command)"""
    # We need to mock the AdapterFactory or BibleService to avoid real DB calls/TF loading
    with patch("src.application.services.BibleService.search") as mock_search:
        mock_search.return_value.verses = []
        mock_search.return_value.cross_references = None
        
        # Note: Typer's runner.invoke doesn't simulate sys.argv injection directly 
        # because we invoke `app`. 
        # But our `cli.py` has `app.command(name="read")` as `main`.
        # When we run `biblecli "Lc 9:54"`, `sys.argv` logic injects "read".
        # So we should test `runner.invoke(cli_app, ["read", "Lc 9:54"])`
        
        result = runner.invoke(cli_app, ["read", "Lc 9:54"])
        assert result.exit_code == 0
        mock_search.assert_called_once()
        args = mock_search.call_args
        assert args.kwargs['reference'] == "Lc 9:54"

def test_cli_regression_legacy_command_implicit_routing():
    """Test the sys.argv injection logic in __main__ (simulated)"""
    # This is hard to test with CliRunner as it bypasses `if __name__ == "__main__"`
    # But we can verify that `main` is registered as "read"
    from src.cli import main
    # It should be a TyperCommand
    # We can inspect the app commands
    commands = [c.name or c.callback.__name__ for c in cli_app.registered_commands]
    assert "read" in commands
    assert "add" in commands
    assert "find" in commands
    # assert "search" in commands # Removed
    # assert "index" in commands # Removed

