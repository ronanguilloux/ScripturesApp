
import pytest
from src.application.workers.french_worker import normalize_text, perform_search

def test_normalize_text():
    assert normalize_text("Élie") == "elie"
    assert normalize_text("Hélène") == "helene"
    assert normalize_text("Cœur") == "coeur"
    assert normalize_text("À bientôt") == "a bientot"
    assert normalize_text("Noël") == "noel"
    assert normalize_text("Cœur") == "coeur"
    assert normalize_text("Lætitia") == "laetitia"

def test_perform_search_exact_word():
    verses = [
        {"r": "Gen 1:1", "b": "Genèse", "c": 1, "v": 1, "t": "Au commencement", "n": "au commencement"},
        {"r": "Gen 1:2", "b": "Genèse", "c": 1, "v": 2, "t": "Dieu dit", "n": "dieu dit"},
        {"r": "Gen 1:3", "b": "Genèse", "c": 1, "v": 3, "t": "Adieu", "n": "adieu"},
    ]
    
    # Search for "Dieu"
    result = perform_search(verses, "Dieu")
    assert result["total"] == 1
    assert result["results"][0]["ref"] == "Gen 1:2"
    
    # Search for "dieu" (lowercase input)
    result = perform_search(verses, "dieu")
    assert result["total"] == 1
    assert result["results"][0]["ref"] == "Gen 1:2"

def test_perform_search_expression():
    verses = [
        {"r": "Mt 8:20", "b": "Matthieu", "c": 8, "v": 20, "t": "Le Fils de l'homme", "n": "le fils de l'homme"},
        {"r": "Mt 9:6", "b": "Matthieu", "c": 9, "v": 6, "t": "Fils de Dieu", "n": "fils de dieu"},
    ]
    
    # "Fils de l'homme"
    result = perform_search(verses, "Fils de l'homme")
    assert result["total"] == 1
    assert result["results"][0]["ref"] == "Mt 8:20"

def test_perform_search_punctuation_handling():
    # "l'homme" should match "l'homme" but not "homme" alone if checking boundaries?
    # Wait, \bl'homme\b
    # \b matches between space and l.
    # ' is not \w. So \b matches between l and ' ?
    # Let's check regex for "l'homme".
    # \bl'homme\b -> \b l ' homme \b
    # "le fils de l'homme" -> "le fils de l ' homme"
    # match l: yes.
    # match ': yes.
    # match homme: yes.
    
    verses = [
        {"r": "A", "t": "L'homme", "n": "l'homme"},
        {"r": "B", "t": "Un homme", "n": "un homme"},
    ]
    
    # Search for "l'homme"
    result = perform_search(verses, "l'homme")
    assert result["total"] == 1
    assert result["results"][0]["ref"] == "A"
    
    # Search for "homme"
    result = perform_search(verses, "homme")
    assert result["total"] == 2 # "L'homme" contains "homme" surrounded by boundary?
    # "l'homme" -> l (boundary) ' (boundary) homme (boundary)
    # So "homme" matches "l'homme" because ' is non-word char?
    # If so, that's acceptable behavior or stricter?
    # User asked: "exact words or exact expressions"
    # If I search "homme", finding it in "l'homme" is probably correct in French context?
    # Or should it be " un homme " ?
    # "l'homme" is "the man".
    # Searching for "man" should find "the man".
    # So yes, 2 results is correct.

def test_perform_search_accents():
    verses = [
        {"r": "A", "t": "Élie est là", "n": "elie est la"},
    ]
    
    assert perform_search(verses, "Élie")["total"] == 1
    assert perform_search(verses, "elie")["total"] == 1
    assert perform_search(verses, "Elie")["total"] == 1

from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from src.cli import app
from src.domain.models import FindResponse, FindResultItem
import json
import sys

runner = CliRunner()

def test_cli_find_french_tob():
    # Mock BibleService
    mock_response = FindResponse(
        lemma="élie",
        original="élie", 
        lemma_gloss="",
        total=1,
        results=[
            FindResultItem(
                ref="1 Rois 17:1", 
                book_code="1 Rois", 
                chapter=17, 
                verse=1, 
                text="Elie, le Tishbite...", 
                highlights=["élie"]
            )
        ]
    )
    
    with patch("src.cli.DependencyContainer") as MockDep, patch("src.cli.FindWordsUseCase") as MockUseCase:
        mock_instance = MockUseCase.return_value
        mock_instance.execute.return_value = mock_response
        
        mock_norm = MagicMock()
        mock_norm.n1904_to_tob.get.return_value = "1 Rois"
        MockDep.get_bible_adapter.return_value.normalizer = mock_norm

        result = runner.invoke(app, ["find", "élie", "-b", "tob"])
        
        assert result.exit_code == 0
        # "Searching for..." message is removed in new CLI
        assert "1 Rois 17:1" in result.stdout
        assert "Elie, le Tishbite..." in result.stdout
        
        # Verify calls
        mock_instance.execute.assert_called_once_with(
            query="élie",
            limit=20, # default
            bible="tob",
            version=None,
            translations=None
        )

def test_cli_find_french_bj_upper():
    # Test case insensitivity of CLI arg
    mock_response = FindResponse(
        lemma="test",
        original="test", 
        lemma_gloss="",
        total=0,
        results=[]
    )
    
    with patch("src.cli.DependencyContainer"), patch("src.cli.FindWordsUseCase") as MockUseCase:
        mock_instance = MockUseCase.return_value
        mock_instance.execute.return_value = mock_response
        
        result = runner.invoke(app, ["find", "test", "-b", "BJ"])
        
        assert result.exit_code == 0
        assert "No occurrences found for 'test'." in result.stdout
        
        # Verify calls
        mock_instance.execute.assert_called_once()
        call_args = mock_instance.execute.call_args[1]
        assert call_args["bible"] == "BJ"

def test_cli_find_invalid_bible():
    # BibleService.find raises ValueError for invalid inputs if logic is there.
    # But checking CLI arg validation logic.
    # In new CLI, we pass args to service. Service raises ValueError.
    
    with patch("src.cli.DependencyContainer"), patch("src.cli.FindWordsUseCase") as MockUseCase:
        mock_instance = MockUseCase.return_value
        mock_instance.execute.side_effect = ValueError("Invalid french version: invalid. Use 'tob' or 'bj'.")
        
        result = runner.invoke(app, ["find", "test", "-b", "invalid"])
        assert result.exit_code == 1
        assert "Invalid french version: invalid. Use 'tob' or 'bj'." in result.stdout
