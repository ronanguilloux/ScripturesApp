import pytest
import os
import json
import shutil
import tempfile
from references_db import ReferenceDatabase
from book_normalizer import BookNormalizer

@pytest.fixture
def temp_data_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)

@pytest.fixture
def normalizer():
    # Use real data for normalization in DB tests to be realistic
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return BookNormalizer(os.path.join(project_root, 'data'))

@pytest.fixture
def db(temp_data_dir, normalizer):
    return ReferenceDatabase(temp_data_dir, normalizer)

def test_add_relation_creates_file(db, temp_data_dir):
    # Add a relation for an NT book
    db.add_relation("personal", "John 1:1", "Gen 1:1", "parallel", "Echoes of creation")
    
    # Check if file was created with correct name
    expected_file = os.path.join(temp_data_dir, "references_nt_personal.json")
    assert os.path.exists(expected_file)
    
    with open(expected_file, "r") as f:
        data = json.load(f)
        assert data["version"] == "1.0"
        assert len(data["cross_references"]) == 1
        entry = data["cross_references"][0]
        assert entry["source"] == "JHN.1.1"
        assert entry["relations"][0]["target"] == "GEN.1.1"
        assert entry["relations"][0]["note"] == "Echoes of creation"

def test_add_relation_ot_prefix(db, temp_data_dir):
    # Add a relation for an OT book
    db.add_relation("notes", "Gen 1:1", "Ps 23:1", "allusion", "Shepherd theme")
    
    expected_file = os.path.join(temp_data_dir, "references_ot_notes.json")
    assert os.path.exists(expected_file)
    
    with open(expected_file, "r") as f:
        data = json.load(f)
        assert data["cross_references"][0]["source"] == "GEN.1.1"

def test_load_all_filters_by_scope(db, temp_data_dir):
    # Create one NT and one OT file
    db.add_relation("mine", "Jn 1:1", "Gn 1:1")
    db.add_relation("mine", "Gn 1:1", "Jn 1:1")
    
    # Load with NT scope
    db.load_all(scope='nt')
    assert "JHN.1.1" in db.in_memory_refs
    assert "GEN.1.1" not in db.in_memory_refs
    
    # Load with OT scope
    db.load_all(scope='ot')
    assert "GEN.1.1" in db.in_memory_refs
    assert "JHN.1.1" not in db.in_memory_refs
    
    # Load all
    db.load_all(scope='all')
    assert "JHN.1.1" in db.in_memory_refs
    assert "GEN.1.1" in db.in_memory_refs

def test_load_all_filters_by_source(db, temp_data_dir):
    # Create files for different sources
    db.add_relation("openbible", "Jn 1:1", "Gn 1:1")
    db.add_relation("personal", "Jn 1:1", "Mt 1:1")
    
    # Filter by 'openbible'
    db.load_all(source_filter='openbible')
    assert len(db.in_memory_refs["JHN.1.1"]["relations"]) == 1
    assert db.in_memory_refs["JHN.1.1"]["relations"][0]["target"] == "GEN.1.1"
    
    # Filter by 'personal'
    db.load_all(source_filter='personal')
    assert len(db.in_memory_refs["JHN.1.1"]["relations"]) == 1
    assert db.in_memory_refs["JHN.1.1"]["relations"][0]["target"] == "MAT.1.1"

def test_get_references_by_book(db, temp_data_dir):
    db.add_relation("test", "Jn 1:1", "Gn 1:1")
    db.add_relation("test", "Mt 1:1", "Lk 1:1")
    db.load_all()
    
    jhn_refs = db.get_references("JHN")
    assert "JHN.1.1" in jhn_refs
    assert "MAT.1.1" not in jhn_refs
    
    mat_refs = db.get_references("MAT")
    assert "MAT.1.1" in mat_refs
    assert "JHN.1.1" not in mat_refs
