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
    
    # Mock slotType to 'word' (default behavior for old datasets)
    mock.F.otype.slotType = 'word'
    
    # Setup some basic book/chapter/verse data for TOB
    # We need to simulate finding "Genèse"
    mock.F.otype.s.return_value = [100] # book node
    mock.F.book.v.return_value = "Genèse"
    
    # Chapter 1
    mock.L.d.side_effect = lambda n, otype: [200] if otype == 'chapter' else [300] if otype == 'verse' else [400] if otype == 'word' else []
    
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
def mock_bj_api():
    mock = MagicMock()
    mock.F = MagicMock()
    mock.L = MagicMock()
    mock.F.otype.s.return_value = [100]
    mock.F.book.v.return_value = "GEN" # Use code as feature value for BJ
    mock.L.d.side_effect = lambda n, otype: [200] if otype == 'chapter' else [300] if otype == 'verse' else [400] if otype == 'word' else []
    mock.F.chapter.v.return_value = 1
    mock.F.verse.v.return_value = 1
    mock.F.text.v.return_value = "Au commencement (BJ)..."
    return mock

@pytest.fixture
def printer(mock_tob_api, mock_n1904_app, normalizer, mock_ref_db, mock_bj_api):
    mock_tob_provider = MagicMock(return_value=mock_tob_api)
    mock_n1904_provider = MagicMock(return_value=mock_n1904_app)
    mock_bhsa_provider = MagicMock()
    mock_bj_provider = MagicMock(return_value=mock_bj_api)
    return VersePrinter(mock_tob_provider, mock_n1904_provider, normalizer, mock_ref_db, mock_bhsa_provider, bj_provider=mock_bj_provider)

def test_lxx_book_name_resolution(printer, mock_tob_api):
    # Test that passing "Gen" (LXX name) correctly looks up "Genèse" in TOB
    
    # "Gen" should normalize -> "Genesis" (code 01) -> "Genèse"
    
    # We need to ensure the printer calls TOB API looking for "Genèse"
    # The printer logic iterates F.otype.s('book') and checks F.book.v(n) == book_fr
    
    # Setup the mock iterating over books to only have GEN
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
    # Test "Genesis" -> "Genèse" resolution (via normalizer)
    
    mock_tob_api.F.book.v.return_value = "Genèse"
    mock_tob_api.F.otype.s.return_value = [100]
    
    printer.print_verse(node=None, book_en="Genesis", chapter=1, verse=1, show_french=True, show_greek=False)
    
    mock_tob_api.F.text.v.assert_called()

def test_get_nav_text_arabic(printer, mock_nav_app):
    # Setup NAV provider to return mock_nav_app.api (that's what main.py does)
    printer.nav_provider = MagicMock(return_value=mock_nav_app.api)
    
    # Test lookup
    text = printer.get_nav_text("GEN", 1, 1)
    
    assert text == "Mock Arabic Text"
    # Verify it used T.nodeFromSection with the normalized name
    mock_nav_app.api.T.nodeFromSection.assert_called()
    # It should have mapped "GEN" to "Genesis"
    call_args = mock_nav_app.api.T.nodeFromSection.call_args[0][0]
    assert "Genesis" in call_args

def test_get_french_text_tob_word_join(printer, mock_tob_api):
    # Setup mock_tob_api to return multiple words for a verse
    # Ensure slotType is 'word'
    mock_tob_api.F.otype.slotType = 'word'
    
    # Node 300 is our verse node
    mock_tob_api.F.otype.s.return_value = [100]
    mock_tob_api.F.book.v.return_value = "Genèse"
    mock_tob_api.L.d.side_effect = lambda n, otype: [200] if otype == 'chapter' else [300] if otype == 'verse' else [10, 11] if (n==300 and otype=='word') else []
    
    def F_text_v_side_effect(n):
        if n == 10: return "Mot1"
        if n == 11: return "Mot2"
        return ""
    mock_tob_api.F.text.v.side_effect = F_text_v_side_effect
    
    text = printer.get_french_text("GEN", 1, 1)
    assert text == "Mot1 Mot2"

def test_get_bj_text(printer, mock_tob_api):
    # We can reuse mock_tob_api structure for BJ if we set it to return from provider
    printer.bj_provider = MagicMock(return_value=mock_tob_api)
    
    mock_tob_api.F.otype.s.return_value = [100]
    mock_tob_api.F.book.v.return_value = "GEN"
    mock_tob_api.F.chapter.v.return_value = 1
    mock_tob_api.F.verse.v.return_value = 1
    mock_tob_api.L.d.side_effect = lambda n, otype: [200] if otype == 'chapter' else [300] if otype == 'verse' else [10, 11] if (n==300 and otype=='word') else []
    
    def F_text_v_side_effect(n):
        if n == 10: return "BJ1"
        if n == 11: return "BJ2"
        return ""
    mock_tob_api.F.text.v.side_effect = F_text_v_side_effect
    
    text = printer.get_bj_text("Genesis", 1, 1)
    assert text == "BJ1 BJ2"

def test_lxx_greek_text_fetching(printer, mock_lxx_app):
    pass # Existing placeholder/todo?

def test_get_hebrew_text(printer):
    # Setup BHSA mock
    mock_bhsa_app = MagicMock()
    printer.bhsa_provider.return_value = mock_bhsa_app
    
    # Setup node lookup
    mock_bhsa_app.nodeFromSectionStr.return_value = 999
    
    # Setup text features (L.d for words, F.g_word_utf8 for text)
    mock_bhsa_app.api.L.d.return_value = [10, 11] # word nodes
    mock_bhsa_app.api.F.g_word_utf8.v.side_effect = lambda w: "Word1" if w==10 else "Word2"
    
    text = printer.get_hebrew_text("Genesis", 1, 1)
    
    assert text == "Word1 Word2"
    mock_bhsa_app.nodeFromSectionStr.assert_called_with("Genesis 1:1")

def test_print_verse_calls_hebrew(printer, mock_tob_api, mock_lxx_app):
    # Verify that passing show_hebrew=True calls get_hebrew_text logic OR prints if node is driving
    
    # Test 1: Driving node is NOT BHSA (e.g. N1904 or None)
    # So it should call get_hebrew_text -> bhsa_provider
    mock_bhsa_app = MagicMock()
    printer.bhsa_provider.return_value = mock_bhsa_app
    mock_bhsa_app.nodeFromSectionStr.return_value = 999
    mock_bhsa_app.api.L.d.return_value = [10]
    mock_bhsa_app.api.F.g_word_utf8.v.return_value = "HebrewText"
    
    # Call print_verse with show_hebrew=True
    # We are mocking print (or just ensuring logic runs without error and calls provider)
    # Since print_verse prints to stdout, we can check side effects on dependencies.
    
    printer.print_verse(node=None, book_en="Genesis", chapter=1, verse=1, show_hebrew=True, show_english=False, show_french=False, show_greek=False)
    
    printer.bhsa_provider.assert_called()
    mock_bhsa_app.nodeFromSectionStr.assert_called()
    # Test that print_verse fetches Greek from source_app if provided
    
    mock_lxx_app.api.T.text.return_value = "LXX Text"
    mock_lxx_app.api.T.sectionFromNode.return_value = ("Gen", 1, 1)
    
    printer.print_verse(node=1001, source_app=mock_lxx_app, show_greek=True, show_french=False)
    
    mock_lxx_app.api.T.text.assert_called_with(1001)

def test_print_verse_calls_bj(printer, mock_bj_api, mock_tob_api):
    # Test that setting french_version='bj' uses the BJ API
    
    # Reset mocks to clear any previous interactions
    mock_tob_api.reset_mock()
    mock_bj_api.reset_mock()
    
    # Call print_verse requesting BJ
    printer.print_verse(node=None, book_en="Genesis", chapter=1, verse=1, show_french=True, french_version='bj')
    
    # Verify BJ API was used (e.g. text fetched)
    mock_bj_api.F.text.v.assert_called()
    
    # Verify TOB API was NOT used for text fetching (though it might be checked for existence/loading)
    # Actually, printer logic: if show_french: if french_version == 'bj': ... else: ...
    mock_tob_api.F.text.v.assert_not_called()
