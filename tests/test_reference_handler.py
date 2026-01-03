import pytest
import sys
import os
from unittest.mock import call, MagicMock

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from reference_handler import ReferenceHandler
from book_normalizer import BookNormalizer

@pytest.fixture
def data_dir():
    return os.path.join(os.path.dirname(__file__), '..', 'data')

@pytest.fixture
def normalizer(data_dir):
    return BookNormalizer(data_dir)

@pytest.fixture
def handler(mock_app, normalizer, mock_printer):
    # Pass mocks for providers
    mock_n1904_provider = MagicMock(return_value=mock_app)
    mock_lxx_provider = MagicMock()
    mock_bhsa_provider = MagicMock()
    return ReferenceHandler(mock_n1904_provider, mock_lxx_provider, mock_bhsa_provider, normalizer, mock_printer)

def test_single_ref_calls_printer(handler, mock_app, mock_printer):
    # Setup mock to return a node
    mock_app.nodeFromSectionStr.return_value = 1001
    
    handler.handle_reference("John 1:1")
    
    mock_app.nodeFromSectionStr.assert_called_with("John 1:1") # Or normalized
    # ReferenceHandler standardizes inputs before calling nodeFromSectionStr?
    # Actually, ReferenceHandler attempts normalize inside?
    # handle_reference replaces ',' with ':' and checks abbreviations.
    # "John 1:1" -> "JHN 1:1" via abbreviation load? 
    # Let's see normalizer.abbreviations.
    # "John" -> "John" or "JHN"?
    # In BookNormalizer, "John" maps to "JHN"? No, ABBREVIATIONS maps to internal key (often English label or dedicated key).
    
    # Let's rely on what the mock receives.
    # If logic works, it should call printer.print_verse(node=1001, ...)
    mock_printer.print_verse.assert_called()
    assert mock_printer.print_verse.call_args[1]['node'] == 1001

def test_chapter_ref_calls_printer_loop(handler, mock_app, mock_printer):
    # "John 1"
    # Logic: 1. Try L.chapter to find chapter node
    # 2. Iterate verses
    
    # Mock finding chapter
    # Mock finding chapter node via app helper
    mock_app.nodeFromSectionStr.return_value = 500
    mock_app.api.F.otype.v.return_value = 'chapter'
    
    # We need to ensure logic matches "John" == "John"
    
    # If successful, it calls L.d(chapter_node, otype='verse')
    mock_app.api.L.d.return_value = [1001, 1002, 1003] # verse nodes
    
    handler.handle_reference("John 1")
    
    assert mock_printer.print_verse.call_count == 3
    # Check calls
    expected_calls = [
        call(node=1001, show_english=False, show_greek=True, show_french=True, show_crossref=False, cross_refs=None, show_crossref_text=False, source_app=mock_app, show_hebrew=False, french_version='tob'),
        call(node=1002, show_english=False, show_greek=True, show_french=True, show_crossref=False, cross_refs=None, show_crossref_text=False, source_app=mock_app, show_hebrew=False, french_version='tob'),
        call(node=1003, show_english=False, show_greek=True, show_french=True, show_crossref=False, cross_refs=None, show_crossref_text=False, source_app=mock_app, show_hebrew=False, french_version='tob')
    ]
    mock_printer.print_verse.assert_has_calls(expected_calls)
    mock_printer.print_verse.assert_has_calls(expected_calls)

def test_bhsa_lazy_load(handler, mock_app):
    # Setup N1904 failure
    mock_app.nodeFromSectionStr.return_value = None
    
    # Setup LXX failure (mock provider returns None App or App returns None node)
    handler.lxx_provider.return_value = None
    
    # Setup BHSA success
    mock_bhsa_app = MagicMock()
    mock_bhsa_app.nodeFromSectionStr.return_value = 5001
    handler.bhsa_provider.return_value = mock_bhsa_app
    
    node, app = handler._get_node_and_app("Genesis 1:1")
    
    # Check BHSA provider was called
    handler.bhsa_provider.assert_called_once()
    assert node == 5001
    assert app == mock_bhsa_app

def test_handle_ref_show_hebrew(handler, mock_app, mock_printer):
    # Setup success ref (N1904)
    mock_app.nodeFromSectionStr.return_value = 1001
    
    # Use OT book for Hebrew test, as NT forces it False
    handler.handle_reference("Genesis 1:1", show_hebrew=True)
    
    args = mock_printer.print_verse.call_args[1]
    assert args['show_hebrew'] is True
