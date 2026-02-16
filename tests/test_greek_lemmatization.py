import pytest
from unittest.mock import MagicMock
from utils.greek_normalizer import GreekNormalizer
from adapters.text_fabric_adapter import TextFabricAdapter

# --- GreekNormalizer Tests ---

def test_greek_normalizer_strip_accents():
    # Test cases from report
    assert GreekNormalizer.strip_accents("λαμβάνω") == "λαμβανω"
    assert GreekNormalizer.strip_accents("ἔλαβον") == "ελαβον"
    assert GreekNormalizer.strip_accents("εἴληφα") == "ειληφα"
    
    # Test mixed case and other diacritics
    assert GreekNormalizer.strip_accents("Αὐτός") == "αυτος"
    assert GreekNormalizer.strip_accents("Ιησούς") == "ιησους"
    assert GreekNormalizer.strip_accents("ϋ") == "υ" # Dialytika
    assert GreekNormalizer.strip_accents("ΐ") == "ι" # Dialytika + Tonos

# --- TextFabricAdapter Integration Tests (Mocked) ---

@pytest.fixture
def mock_tf_app():
    app = MagicMock()
    app.api = MagicMock()
    app.api.F = MagicMock()
    app.api.T = MagicMock()
    return app

@pytest.fixture
def adapter(mock_tf_app):
    # Setup Adapter with mocked provider
    a = TextFabricAdapter(data_dir="/tmp/mock_data")
    a._n1904_provider = lambda: mock_tf_app
    return a

def test_build_stripped_index(adapter, mock_tf_app):
    # Mock Corpus Data
    # Word 1: "ἔλαβον" (lemma: "λαμβάνω")
    # Word 2: "αὐτός" (lemma: "αὐτός")
    
    mock_tf_app.api.F.otype.s.return_value = [1, 2] # Two words
    
    # Lemma lookup
    mock_tf_app.api.F.lemma.v.side_effect = lambda w: "λαμβάνω" if w == 1 else "αὐτός"
    
    # Text lookup
    mock_tf_app.api.T.text.side_effect = lambda w: "ἔλαβον " if w == 1 else "αὐτός."

    # Trigger index build
    adapter.build_stripped_index()
    
    # Verify Index Content
    # Should index both LEMMA and SURFACE forms
    
    # 1. Check "λαμβάνω" (lemma itself) -> "λαμβανω"
    assert "λαμβανω" in adapter._stripped_index
    assert "λαμβάνω" in adapter._stripped_index["λαμβανω"]
    
    # 2. Check "ἔλαβον" (surface) -> "ελαβον"
    assert "ελαβον" in adapter._stripped_index
    assert "λαμβάνω" in adapter._stripped_index["ελαβον"]
    
    # 3. Check "αὐτός"
    assert "αυτος" in adapter._stripped_index
    assert "αὐτός" in adapter._stripped_index["αυτος"]

def test_find_lemmas_by_stripped_surface(adapter, mock_tf_app):
    # Reuse setup logic or mock build_stripped_index directly
    # Let's mock the index directly to test query logic
    adapter._stripped_index = {
        "ειληφα": {"λαμβάνω", "άλλος"}, # Hypothetical collision
        "ελαβον": {"λαμβάνω"}
    }
    
    # Test valid lookup
    assert adapter.find_lemmas_by_stripped_surface("ειληφα") == {"λαμβάνω", "άλλος"}
    assert adapter.find_lemmas_by_stripped_surface("ελαβον") == {"λαμβάνω"}
    
    # Test miss
    assert adapter.find_lemmas_by_stripped_surface("unknown") == set()
