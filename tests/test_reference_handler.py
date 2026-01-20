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
    # Since John is NT, ReferenceHandler will use T.nodeFromSection((book, ch, vs))
    mock_app.api.T.nodeFromSection.return_value = 1001
    
    handler.handle_reference("John 1:1")
    
    mock_app.api.T.nodeFromSection.assert_called_with(("John", 1, 1))
    
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
        call(node=1001, show_english=False, show_greek=True, show_french=True, show_arabic=False, show_crossref=False, cross_refs=None, show_crossref_text=False, source_app=mock_app, show_hebrew=False, french_version='tob', compact_mode=0),
        call(node=1002, show_english=False, show_greek=True, show_french=True, show_arabic=False, show_crossref=False, cross_refs=None, show_crossref_text=False, source_app=mock_app, show_hebrew=False, french_version='tob', compact_mode=0),
        call(node=1003, show_english=False, show_greek=True, show_french=True, show_arabic=False, show_crossref=False, cross_refs=None, show_crossref_text=False, source_app=mock_app, show_hebrew=False, french_version='tob', compact_mode=0)
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

def test_handle_ref_bj_version(handler, mock_app, mock_printer):
    # Setup success ref
    mock_app.nodeFromSectionStr.return_value = 1001
    
    # Setup mock_app to have dummy API components to avoid 'nodeFromSection' errors
    mock_app.api = MagicMock()
    mock_app.api.F = MagicMock()
    mock_app.api.L = MagicMock()
    mock_app.api.T = MagicMock()

    # Test defaulting to 'tob'
    handler.handle_reference("John 1:1")
    args_default = mock_printer.print_verse.call_args[1]
    assert args_default.get('french_version') == 'tob'
    
    # Test explicit 'bj'
    handler.handle_reference("John 1:1", french_version='bj')
    args_bj = mock_printer.print_verse.call_args[1]
    assert args_bj.get('french_version') == 'bj'

def test_handle_ref_show_arabic(handler, mock_app, mock_printer):
    # Setup success ref (N1904)
    mock_app.api.T.nodeFromSection.return_value = 1001
    
    handler.handle_reference("John 1:1", show_arabic=True)
    
    args = mock_printer.print_verse.call_args[1]
    assert args['show_arabic'] is True

def test_handle_ref_ot_no_forced_hebrew(handler, mock_app, mock_printer):
    # Setup success ref (LXX/N1904 fixture might need adjustment, but focus on the flag)
    # ReferenceHandler uses n1904_provider for the app in single_ref fallback if not OT?
    # No, it uses code to decide.
    
    # Genesis is OT
    mock_app.nodeFromSectionStr.return_value = 1001
    handler.normalizer.is_ot = MagicMock(return_value=True)
    handler.normalizer.is_nt = MagicMock(return_value=False)
    
    handler.handle_reference("Gn 1:1", show_hebrew=False)
    
    args = mock_printer.print_verse.call_args[1]
    # Verify it stayed False (or at least was passed as False if that's what we want)
    assert args['show_hebrew'] is False

def test_handle_ref_compact_mode(handler, mock_app, mock_printer):
    # Setup success ref (N1904)
    mock_app.api.T.nodeFromSection.return_value = 1001
    
    handler.handle_reference("John 1:1", compact_mode=1)
    
    args = mock_printer.print_verse.call_args[1]
    assert args['compact_mode'] == 1

def test_handle_ref_very_compact_mode(handler, mock_app, mock_printer):
    # Setup success ref (N1904)
    mock_app.api.T.nodeFromSection.return_value = 1001
    
    handler.handle_reference("John 1:1", compact_mode=2)
    
    args = mock_printer.print_verse.call_args[1]
    assert args['compact_mode'] == 2

def test_handle_ref_cross_refs(handler, mock_app, mock_printer):
    mock_app.api.T.nodeFromSection.return_value = 1001
    mock_refs = {"JHN.1.1": {"relations": [{"target": "GEN.1.1"}]}}
    
    handler.handle_reference("John 1:1", show_crossref=True, cross_refs=mock_refs, show_crossref_text=True)
    
    args = mock_printer.print_verse.call_args[1]
    assert args['show_crossref'] is True
    assert args['cross_refs'] == mock_refs
    assert args['show_crossref_text'] is True
