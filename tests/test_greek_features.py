import pytest
from unittest.mock import MagicMock, PropertyMock
from src.adapters.text_fabric_adapter import TextFabricAdapter
from src.domain.models import Verse, Language

class MockWord:
    def __init__(self, node_id):
        self.node_id = node_id

@pytest.fixture
def mock_tf_app():
    app = MagicMock()
    app.api = MagicMock()
    return app

@pytest.fixture
def adapter(mock_tf_app):
    # Mock normalizer to avoiding loading data
    mock_normalizer = MagicMock()
    mock_normalizer.n1904_to_code.get.return_value = "MAT"
    
    adapter = TextFabricAdapter("/tmp")
    adapter.normalizer = mock_normalizer
    
    # Inject mock app
    t_n1904 = PropertyMock(return_value=mock_tf_app)
    type(adapter).n1904 = t_n1904
    
    return adapter

def test_find_lemma_exact_match(adapter, mock_tf_app):
    """Test finding a lemma by exact match."""
    api = mock_tf_app.api
    F, L, T = api.F, api.L, api.T
    
    # Setup Data
    # Word 1: ἀγαπάω -> Verse 100
    w1 = 1
    v1 = 100
    
    # Mock Iteration
    F.otype.s.return_value = [w1]
    
    # Mock Features
    F.lemma.v.side_effect = lambda n: "ἀγαπάω" if n == w1 else None
    
    # Mock Verse Lookup
    L.u.side_effect = lambda n, otype: [v1] if n == w1 and otype == 'verse' else []
    
    # Mock Section/Text
    T.sectionFromNode.return_value = ("Matthew", 5, 44)
    T.text.return_value = "ἀγαπᾶτε"
    
    # Run
    results = adapter.find_lemma("ἀγαπάω")
    
    assert len(results) == 1
    assert results[0].book_code == "MAT"
    assert results[0].chapter == 5
    assert results[0].verse == 44
    assert results[0].text == "ἀγαπᾶτε"

def test_find_lemma_normalization(adapter, mock_tf_app):
    """Test finding a lemma with different accent normalization (Oxia vs Tonos)."""
    api = mock_tf_app.api
    F, L, T = api.F, api.L, api.T
    
    w1 = 1
    v1 = 100
    F.otype.s.return_value = [w1]
    
    # Dataset has Oxia (ἀγαπάω)
    # Input will be Tonos (ἀγαπάω)
    dataset_lemma = "ἀγαπ\u1F71ω" # Oxia
    input_lemma = "ἀγαπάω"     # Tonos
    
    F.lemma.v.return_value = dataset_lemma
    L.u.return_value = [v1]
    T.sectionFromNode.return_value = ("Matthew", 1, 1)
    T.text.return_value = "ἀγαπάω"
    
    results = adapter.find_lemma(input_lemma)
    
    assert len(results) == 1 # Should match due to normalization

def test_find_surface_form(adapter, mock_tf_app):
    """Test finding a word by its surface form (e.g. Teknia)."""
    api = mock_tf_app.api
    F, L, T = api.F, api.L, api.T
    
    w1 = 1
    v1 = 100
    F.otype.s.return_value = [w1]
    
    # Lemma doesn't match
    F.lemma.v.return_value = "τεκνίον" 
    
    # Surface text matches (with punctuation)
    T.text.return_value = "Τεκνία, "
    L.u.return_value = [v1]
    T.sectionFromNode.return_value = ("1 John", 3, 18)
    
    # Search for surface form
    results = adapter.find_lemma("Τεκνία")
    
    assert len(results) == 1
    assert results[0].text == "Τεκνία, "

def test_highlighting(adapter, mock_tf_app):
    """Test that matching words are collected for highlighting."""
    api = mock_tf_app.api
    F, L, T = api.F, api.L, api.T
    
    w1 = 1
    v1 = 100
    F.otype.s.return_value = [w1]
    
    # Text matches surface form
    F.lemma.v.return_value = "other_lemma"
    T.text.return_value = "TargetWord" 
    
    # Mock finding
    L.u.return_value = [v1]
    T.sectionFromNode.return_value = ("Mark", 1, 1)
    
    # Important: L.d(v_node, otype='word') is called inside to find words in verse for highlighting
    # We need to mock this to return [w1]
    L.d.return_value = [w1]
    
    results = adapter.find_lemma("TargetWord")
    
    assert len(results) == 1
    assert "highlight_words" in results[0].metadata
    assert "TargetWord" in results[0].metadata["highlight_words"]
