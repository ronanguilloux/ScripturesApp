import pytest
from typer.testing import CliRunner
from src.cli import app
import json
from unittest.mock import MagicMock, patch

runner = CliRunner()

@patch("src.application.services.BibleService")
def test_find_greek_script_detection(MockService):
    """Test that Greek script automatically triggers Greek search."""
    # Configure Mock Result
    mock_result = MagicMock()
    mock_result.ref = "MAT 1:1"
    mock_result.book_code = "MAT"
    mock_result.chapter = 1
    mock_result.verse = 1
    mock_result.text = "Biblos geneseos..."
    mock_result.translations = {"fr": "Livre de la genese"}
    mock_result.highlights = []

    mock_response = MagicMock()
    mock_response.lemma = "logos"
    mock_response.original = "logos"
    mock_response.lemma_gloss = ""
    mock_response.total = 1
    mock_response.results = [mock_result]
    
    mock_instance = MockService.return_value
    mock_instance.find.return_value = mock_response
    
    # Mock normalizer behavior used in CLI for localization
    mock_instance.normalizer.code_to_n1904.get.side_effect = lambda x, y: "MAT" # Simplification
    mock_instance.normalizer.n1904_to_tob.get.return_value = "Matthieu"

    result = runner.invoke(app, ["find", "λόγος", "-tr", "fr"])
    
    assert result.exit_code == 0
    # Localization mock maps n1904_to_tob.get -> "Matthieu"
    assert "Matthieu 1:1" in result.stdout
    assert "Biblos geneseos" in result.stdout
    assert "(fr) Livre de la genese" in result.stdout 
    
    # Verify service call
    mock_instance.find.assert_called_once()
    args = mock_instance.find.call_args[1]
    assert args['query'] == "λόγος"
    # version defaults to None in CLI, service handles default?
    # CLI passes None to service. Service defaults to NT.
    assert args['version'] is None 

@patch("src.application.services.BibleService")
def test_find_greek_explicit_corpus(MockService):
    """Test finding with explicit Greek corpus (-v lxx)."""
    mock_instance = MockService.return_value
    mock_instance.find.return_value = MagicMock(total=0, results=[])

    result = runner.invoke(app, ["find", "ἀρχή", "-v", "lxx"])
    
    assert result.exit_code == 0
    
    # Verify service call
    mock_instance.find.assert_called_once()
    args = mock_instance.find.call_args[1]
    assert args['version'] == "lxx"

@patch("src.application.services.BibleService")
def test_find_french_latin_script(MockService):
    """Test that Latin script with -b triggers French search."""
    mock_instance = MockService.return_value
    mock_instance.find.return_value = MagicMock(total=0, results=[])

    result = runner.invoke(app, ["find", "Dieu", "-b", "tob"])
    
    assert result.exit_code == 0
    
    # Verify service call
    mock_instance.find.assert_called_once()
    args = mock_instance.find.call_args[1]
    assert args['bible'] == "tob"

def test_find_ambiguous_latin():
    """Test that Latin script without -b raises error."""
    # This logic is likely in Service now? 
    # CLI calls Service. Service detects Latin + No Bible -> Raises ValueError?
    # Or CLI has check? CLI logic was moved to Service.
    # So we need to mock Service to raise ValueError.
    
    with patch("src.application.services.BibleService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.find.side_effect = ValueError("Ambiguous search: 'God' is Latin script")
        
        result = runner.invoke(app, ["find", "God"])
        
        assert result.exit_code == 1
        assert "Ambiguous search" in result.stdout

