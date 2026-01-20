import pytest
from unittest.mock import MagicMock, patch
import io
import sys
import os

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import handle_list

def test_handle_list_books(mock_app):
    # Setup mock_app to return some books via N.walk
    mock_app.api.N.walk.return_value = [1, 2, 3] # 1,2 are books, 3 is not
    
    def F_otype_v_side_effect(n):
        if n in [1, 2]: return 'book'
        return 'verse'
    mock_app.api.F.otype.v.side_effect = F_otype_v_side_effect
    
    def F_book_v_side_effect(n):
        if n == 1: return "Genesis"
        if n == 2: return "Exodus"
        return ""
    mock_app.api.F.book.v.side_effect = F_book_v_side_effect
    
    # Capture stdout
    captured_output = io.StringIO()
    sys.stdout = captured_output
    
    try:
        handle_list(mock_app, ["books"])
    finally:
        sys.stdout = sys.__stdout__
        
    output = captured_output.getvalue()
    assert "Available books:" in output
    assert "Genesis" in output
    assert "Exodus" in output

def test_handle_list_no_args():
    mock_app = MagicMock()
    captured_output = io.StringIO()
    sys.stdout = captured_output
    
    try:
        handle_list(mock_app, [])
    finally:
        sys.stdout = sys.__stdout__
        
    output = captured_output.getvalue()
    assert "Error: Missing argument for 'list'" in output
