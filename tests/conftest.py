import pytest
import os
import sys
from unittest.mock import MagicMock

# Ensure src is in path for all tests
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

class MockF:
    def __init__(self):
        self.otype = MagicMock()
        self.book = MagicMock()
        self.chapter = MagicMock()
        self.verse = MagicMock()
        self.text = MagicMock()
        self.text.v.return_value = "Mock Verse Text"
    
class MockL:
    def __init__(self):
        self.d = MagicMock()
        self.d.return_value = [] # Default to empty list of children

class MockT:
    def __init__(self):
        self.sectionFromNode = MagicMock()
        self.nodeFromSection = MagicMock()
        self.text = MagicMock()
        self.text.return_value = "Mock Greek Text"

class MockN:
    def __init__(self):
        self.walk = MagicMock()

class MockApi:
    def __init__(self):
        self.F = MockF()
        self.L = MockL()
        self.T = MockT()
        self.N = MockN()

class MockApp:
    def __init__(self):
        self.api = MockApi()
        self.nodeFromSectionStr = MagicMock()

@pytest.fixture
def mock_app():
    return MockApp()

@pytest.fixture
def mock_printer():
    printer = MagicMock()
    printer.print_verse = MagicMock()
    printer.get_french_text.return_value = "Mock French Text"
    printer.get_nav_text.return_value = "Mock Arabic Text"
    return printer

@pytest.fixture
def mock_nav_app():
    app = MockApp()
    app.api.T.text.return_value = "Mock Arabic Text"
    app.api.T.nodeFromSection.return_value = 500
    return app
