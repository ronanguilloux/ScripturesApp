import pytest
from unittest.mock import MagicMock, patch
from adapters.text_fabric_adapter import TextFabricAdapter
from domain.models import Verse, Language

class MockNode:
    pass

class MockTFApp:
    def __init__(self):
        self.api = MagicMock()
        self.api.T = MagicMock()
        self.api.F = MagicMock()
        self.api.L = MagicMock()

    def nodeFromSectionStr(self, ref):
        return 1001

@pytest.fixture
def adapter():
    a = TextFabricAdapter(data_dir="/tmp/mock_data")
    # Mock normalizer to avoid file system dependency failure
    a.normalizer.is_nt = MagicMock(return_value=True)
    a.normalizer.is_ot = MagicMock(return_value=True)
    a.normalizer.code_to_n1904 = {"JHN": "John", "GEN": "Genesis"}
    a.normalizer.n1904_to_tob = {"Genesis": "Genèse"}
    return a

def test_n1904_fetching(adapter):
    mock_app = MockTFApp()
    # Mock node lookup
    mock_app.api.T.nodeFromSection.return_value = 123
    # Mock text (T.text used now)
    mock_app.api.T.text.return_value = "In the beginning"
    mock_app.api.L.d.return_value = [1]
    # mock_app.api.F.trans.v.return_value = "In the beginning" # Legacy
    
    # Inject provider
    adapter._n1904_provider = lambda: mock_app
    
    verse = adapter.get_verse("JHN", 1, 1, version="n1904")
    assert verse is not None
    assert verse.text == "In the beginning"
    assert verse.version == "N1904"
    assert verse.chapter == 1
    assert verse.chapter == 1
    assert verse.verse == 1
    assert verse.node is not None # Check explicit field

def test_lxx_fetching(adapter):
    mock_app = MockTFApp()
    # LXX mocks
    mock_app.nodeFromSectionStr = MagicMock(return_value=200)
    mock_app.api.T.text.return_value = "En arche"
    
    adapter._lxx_provider = lambda: mock_app
    
    verse = adapter.get_verse("GEN", 1, 1, version="lxx")
    assert verse is not None
    assert verse.text == "En arche"
    assert verse.version == "LXX"
    assert verse.language == Language.GREEK

def test_bhsa_fetching(adapter):
    mock_app = MockTFApp()
    # BHSA mocks
    mock_app.nodeFromSectionStr = MagicMock(return_value=300)
    mock_app.api.L.d.return_value = [1, 2]
    
    # Mock Hebrew words
    def vocab_side_effect(w):
        return "Bereshit" if w == 1 else "Bara"
        
    mock_app.api.F.g_word_utf8.v.side_effect = vocab_side_effect
    
    adapter._bhsa_provider = lambda: mock_app
    
    verse = adapter.get_verse("GEN", 1, 1, version="bhsa")
    assert verse is not None
    assert verse.text == "Bereshit Bara"
    assert verse.version == "BHSA"
    assert verse.language == Language.HEBREW

def test_tob_fetching(adapter):
    mock_api = MagicMock()
    mock_api.F = MagicMock()
    mock_api.L = MagicMock()
    mock_api.T = MagicMock() # Mock T interface
    
    # Mock searching for book, chapter, verse nodes
    # Update: Adapter prefers nodeFromSection now.
    mock_api.T.nodeFromSection.return_value = 50
    
    # Mock normalizer needs (mocked in fixture but verify)
    adapter.normalizer.n1904_to_tob = {"Genesis": "Genèse"}
    adapter.normalizer.code_to_n1904 = {"GEN": "Genesis"}
    
    mock_api.F.book.v.return_value = "Genèse"
    mock_api.F.chapter.v.return_value = 1
    mock_api.F.verse.v.return_value = 1
    
    # Text (Adapter uses T.text)
    mock_api.T.text.return_value = "Au commencement"
    
    adapter._tob_provider = lambda: mock_api
    
    verse = adapter.get_verse("GEN", 1, 1, version="tob")
    assert verse is not None
    assert verse.text == "Au commencement"
    assert verse.version == "TOB"
    assert verse.language == Language.FRENCH

def test_bj_fetching(adapter):
    mock_api = MagicMock()
    mock_api.F = MagicMock()
    mock_api.L = MagicMock()
    mock_api.T = MagicMock()
    
    # BJ uses Codes "GEN"
    # Update: Adapter uses nodeFromSection for BJ too (O(1) optimization)
    mock_api.T.nodeFromSection.return_value = 60
    
    mock_api.F.book.v.return_value = "GEN"
    mock_api.F.chapter.v.return_value = 1
    mock_api.F.verse.v.return_value = 1
    
    # Text
    mock_api.T.text.return_value = "Au commencement BJ"
    
    adapter._bj_provider = lambda: mock_api
    
    verse = adapter.get_verse("GEN", 1, 1, version="bj")
    assert verse is not None
    assert verse.text == "Au commencement BJ"
    assert verse.version == "BJ"

def test_nav_fetching(adapter):
    mock_api = MagicMock()
    mock_api.T = MagicMock()
    
    adapter.normalizer.code_to_n1904 = {"GEN": "Genesis"}
    
    mock_api.T.nodeFromSection.return_value = 500
    mock_api.T.text.return_value = "Fi al-bad'"
    
    adapter._nav_provider = lambda: mock_api
    
    verse = adapter.get_verse("GEN", 1, 1, version="nav")
    assert verse is not None
    assert verse.text == "Fi al-bad'"
    assert verse.version == "NAV"
    assert verse.language == Language.ARABIC

def test_get_chapter_n1904(adapter):
    mock_app = MockTFApp()
    # Mock node lookup for "John 1" (Book John, Ch 1)
    
    mock_app.api.T.nodeFromSection.return_value = 500 # Chapter node
    mock_app.api.F.otype.v.return_value = 'chapter'
    
    # Mock Verse Nodes from Chapter
    # L.d(chapter_node, otype='verse')
    mock_app.api.L.d.side_effect = lambda n, otype: [601, 602] if n == 500 and otype == 'verse' else []
    
    # Text
    mock_app.api.T.text.side_effect = lambda n: "Verse 1" if n == 601 else "Verse 2"
    mock_app.api.F.verse.v.side_effect = lambda n: 1 if n == 601 else 2
    
    adapter._n1904_provider = lambda: mock_app
    
    verses = adapter.get_chapter("JHN", 1, version="n1904")
    
    assert len(verses) == 2
    assert verses[0].text == "Verse 1"
    assert verses[1].text == "Verse 2"
    
    # Assertions on construction (indirectly testing adapter's construction logic)
    assert len(verses) == 2
    assert verses[0].node is not None
    assert verses[1].node is not None
