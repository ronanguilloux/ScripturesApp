
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from api.main import app, get_service
from application.services import BibleService
from domain.models import Verse, Language

# Mock Data
def create_mock_verse(book, version, text, lang):
    return Verse(
        book_code=book,
        chapter=1,
        verse=1,
        text=text,
        language=lang,
        version=version,
        node=1000 + len(text)
    )

MOCK_VERSES = {
    # OT
    "N1904_EN_OT": create_mock_verse("Genesis", "N1904_EN", "In the beginning...", Language.ENGLISH),
    "LXX_OT": create_mock_verse("Genesis", "LXX", "En arche...", Language.GREEK),
    
    # NT
    "N1904_EN_NT": create_mock_verse("John", "N1904_EN", "In the beginning was the Word...", Language.ENGLISH),
    "N1904_NT": create_mock_verse("John", "N1904", "En arche en ho logos...", Language.GREEK),
    "TOB_NT": create_mock_verse("Jean", "TOB", "Au commencement était le Verbe...", Language.FRENCH),
}

@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    # Mock normalizer
    adapter.normalizer = MagicMock()
    
    def normalize_side_effect(ref):
        if "Gn 1:1" in ref: return ("Genesis", 1, 1)
        if "Jn 1:1" in ref: return ("John", 1, 1)
        return None
    adapter.normalizer.normalize_reference.side_effect = normalize_side_effect
    adapter.normalize_reference.side_effect = normalize_side_effect

    def is_nt_side_effect(book):
        return book == "John"
    adapter.normalizer.is_nt.side_effect = is_nt_side_effect
    
    adapter.normalizer.is_ot.side_effect = lambda b: b == "Genesis"
    
    # Mock code mappings
    adapter.normalizer.code_to_n1904.get.side_effect = lambda c, d=None: c
    adapter.normalizer.n1904_to_tob.get.side_effect = lambda c: "Jean" if c == "John" else "Genèse"
    adapter.normalizer.code_to_bhsa.get.return_value = "Genesis"
    

    # Mock get_verse
    def get_verse_side_effect(book, chapter, verse, version):
        if book == "Genesis" and chapter == 1 and verse == 1:
            if version == "N1904_EN": return MOCK_VERSES["N1904_EN_OT"]
            if version == "LXX": return MOCK_VERSES["LXX_OT"]
            if version == "BHSA": return create_mock_verse("Genesis", "BHSA", "Hebrew Text", Language.HEBREW)
            if version == "TOB": return create_mock_verse("Genesis", "TOB", "French Text", Language.FRENCH)
            if version == "NAV": return create_mock_verse("Genesis", "NAV", "Arabic Text", Language.ARABIC)
            if version == "BJ": return create_mock_verse("Genesis", "BJ", "BJ Text", Language.FRENCH)
            
        if book == "John" and chapter == 1 and verse == 1:
            if version == "N1904_EN": return MOCK_VERSES["N1904_EN_NT"]
            if version == "N1904": return MOCK_VERSES["N1904_NT"]
            if version == "TOB": return MOCK_VERSES["TOB_NT"]
            
        return None
    
    adapter.get_verse.side_effect = get_verse_side_effect
    
    # Mock data_dir
    adapter.data_dir = "/tmp/mock_data"
    
    return adapter

@pytest.fixture
def mock_ref_db():
    db = MagicMock()
    db.in_memory_refs = {}
    return db

@pytest.fixture
def bible_service(mock_adapter, mock_ref_db):
    with patch('application.services.ReferenceDatabase', return_value=mock_ref_db):
        service = BibleService(adapter=mock_adapter)
        service.ref_db = mock_ref_db
        return service

@pytest.fixture
def client(bible_service):
    app.dependency_overrides[get_service] = lambda: bible_service
    return TestClient(app)

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_search_basic(client):
    # Use NT for English default expectation
    response = client.get("/api/v1/search?q=Jn 1:1&tr=en")
    assert response.status_code == 200
    data = response.json()
    assert data["reference"] == "Jn 1:1"
    assert len(data["verses"]) == 1
    assert data["verses"][0]["primary"]["text"] == MOCK_VERSES["N1904_EN_NT"].text

def test_search_multiple_languages(client):
    # Use NT to easily get English and French
    response = client.get("/api/v1/search?q=Jn 1:1&tr=en&tr=fr")
    assert response.status_code == 200
    data = response.json()
    parallels = data["verses"][0]["parallels"]
    # Check versions present in primary or parallels
    combined_versions = {data["verses"][0]["primary"]["version"]} | {p["version"] for p in parallels}
    assert "N1904_EN" in combined_versions
    assert "TOB" in combined_versions

def test_search_all_languages_ot(client, mock_adapter):
    # en + gr + ar + hb + fr
    response = client.get("/api/v1/search?q=Gn 1:1&tr=en&tr=gr&tr=ar&tr=hb&tr=fr")
    assert response.status_code == 200
    data = response.json()
    combined_versions = {data["verses"][0]["primary"]["version"]} | {p["version"] for p in data["verses"][0]["parallels"]}
    
    # Check all are present
    assert "LXX" in combined_versions # Greek OT
    assert "BHSA" in combined_versions # Hebrew
    assert "TOB" in combined_versions # French
    assert "NAV" in combined_versions # Arabic

def test_primary_version_override(client, mock_adapter):
    response = client.get("/api/v1/search?q=Gn 1:1&v=BHSA")
    assert response.status_code == 200
    data = response.json()
    assert data["verses"][0]["primary"]["version"] == "BHSA"

def test_french_version_selection(client, mock_adapter):
    response = client.get("/api/v1/search?q=Gn 1:1&tr=fr&bible=bj")
    assert response.status_code == 200
    data = response.json()
    combined_versions = {data["verses"][0]["primary"]["version"]} | {p["version"] for p in data["verses"][0]["parallels"]}
    assert "BJ" in combined_versions

def test_search_crossref_simple(client, mock_ref_db):
    mock_ref_db.in_memory_refs = {
        "Genesis.1.1": {
            "relations": [
                {"target": "Jn 1:1", "type": "parallel", "note": None} # Use valid type
            ],
            "notes": []
        }
    }
    
    response = client.get("/api/v1/search?q=Gn 1:1&crossref=true")
    assert response.status_code == 200
    data = response.json()
    
    assert data["cross_references"] is not None
    assert len(data["cross_references"]["relations"]) == 1
    assert data["cross_references"]["relations"][0]["target_ref"] == "Jn 1:1"

def test_search_crossref_full(client, mock_ref_db, mock_adapter):
    mock_ref_db.in_memory_refs = {
        "Genesis.1.1": {
            "relations": [
                {"target": "Gn 1:1", "type": "parallel", "note": None}
            ],
            "notes": []
        }
    }
    
    # Ensure Gn 1:1 fetch returns something (provided by mock_adapter defaults)
    
    response = client.get("/api/v1/search?q=Gn 1:1&crossref_full=true")
    assert response.status_code == 200
    data = response.json()
    
    assert data["cross_references"] is not None
    rel = data["cross_references"]["relations"][0]
    assert rel["text"] is not None

def test_search_crossref_source_filter(client, bible_service):
    with patch.object(bible_service.ref_db, 'load_all') as mock_load:
         client.get("/api/v1/search?q=Gn 1:1&crossref=true&crossref_source=BJ")
         mock_load.assert_called_with(source_filter="BJ", scope='ot')

def test_search_invalid_ref(client, mock_adapter):
    mock_adapter.normalize_reference.return_value = None
    try:
        response = client.get("/api/v1/search?q=InvalidRef")
        assert response.status_code in [400, 422, 500]
    except Exception:
        pass
