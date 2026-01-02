import pytest
import sys
import os
from unittest.mock import MagicMock

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from verse_printer import VersePrinter
from book_normalizer import BookNormalizer

@pytest.fixture
def data_dir():
    return os.path.join(os.path.dirname(__file__), '..', 'data')

@pytest.fixture
def normalizer(data_dir):
    return BookNormalizer(data_dir)

@pytest.fixture
def mock_tob_api():
    mock = MagicMock()
    # Mock Feature and Locality objects
    mock.F = MagicMock()
    mock.L = MagicMock()
    
    # Setup some basic book/chapter/verse data for TOB
    # We need to simulate finding "Genèse"
    mock.F.otype.s.return_value = [100] # book node
    mock.F.book.v.return_value = "Genèse"
    
    # Chapter 1
    mock.L.d.side_effect = lambda n, otype: [200] if otype == 'chapter' else [300] if otype == 'verse' else []
    
    mock.F.chapter.v.return_value = 1
    mock.F.verse.v.return_value = 1
    mock.F.text.v.return_value = "Au commencement..."
    
    return mock

@pytest.fixture
def mock_n1904_app():
    return MagicMock()

@pytest.fixture
def mock_lxx_app():
    return MagicMock()

@pytest.fixture
def mock_ref_db():
    mock = MagicMock()
    mock.in_memory_refs = {}
    return mock

@pytest.fixture
def printer(mock_tob_api, mock_n1904_app, normalizer, mock_ref_db):
    return VersePrinter(mock_tob_api, mock_n1904_app, normalizer, mock_ref_db)

def test_lxx_book_name_resolution(printer, mock_tob_api):
    # Test that passing "Gen" (LXX name) correctly looks up "Genèse" in TOB
    
    # "Gen" should normalize -> "Genesis" (code 01) -> "Genèse"
    
    # We need to ensure the printer calls TOB API looking for "Genèse"
    # The printer logic iterates F.otype.s('book') and checks F.book.v(n) == book_fr
    
    # Setup the mock iterating over books to only have Genèse
    def book_v_side_effect(n):
        if n == 100: return "Genèse"
        return "Autre"
    mock_tob_api.F.book.v.side_effect = book_v_side_effect
    mock_tob_api.F.otype.s.return_value = [100]
    
    # Call print_verse with LXX-style book name
    # We don't care about the Greek node for this text, just the French lookup side effect
    printer.print_verse(node=None, book_en="Gen", chapter=1, verse=1, show_french=True, show_greek=False)
    
    # If the logic is correct, it found the book node for "Genèse" and proceeded to chapters
    # Use asserts or capture stdout? 
    # The current printer just prints to stdout. We can verify mock calls.
    
    # Verify that it iterated verses
    # L.d(200, otype='verse') should have been called if chapter was found
    # And L.d(100, otype='chapter') if book was found.
    
    assert mock_tob_api.L.d.call_count >= 1
    # Check that we got the text
    mock_tob_api.F.text.v.assert_called()

def test_standard_book_name_resolution(printer, mock_tob_api):
    # Test "Genesis" -> "Genèse"
    
    mock_tob_api.F.book.v.return_value = "Genèse"
    mock_tob_api.F.otype.s.return_value = [100]
    
    printer.print_verse(node=None, book_en="Genesis", chapter=1, verse=1, show_french=True, show_greek=False)
    
    mock_tob_api.F.text.v.assert_called()

def test_lxx_greek_text_fetching(printer, mock_lxx_app):
    # Test that print_verse fetches Greek from source_app if provided
    
    mock_lxx_app.api.T.text.return_value = "LXX Text"
    mock_lxx_app.api.T.sectionFromNode.return_value = ("Gen", 1, 1)
    
    printer.print_verse(node=1001, source_app=mock_lxx_app, show_greek=True, show_french=False)
    
    mock_lxx_app.api.T.text.assert_called_with(1001)
