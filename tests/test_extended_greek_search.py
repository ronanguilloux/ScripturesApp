
import pytest
import os
import sys

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.application.workers.find_worker import find_in_index, load_index

def test_load_indices():
    """Verify indices can be loaded."""
    nt_index = load_index("NT")
    assert nt_index is not None
    assert "lemmas" in nt_index
    assert "verses" in nt_index
    
    lxx_index = load_index("LXX")
    assert lxx_index is not None
    assert "lemmas" in lxx_index

def test_search_nt_only():
    """Verify search in NT."""
    # Search for "λόγος" (logos)
    # Using 'logoj' or stripped form? Index uses NFC normalized lemma.
    # OdyCy would give "λόγος".
    lemma = "λόγος" 
    results = find_in_index(lemma, lemma, "nt", 10)
    
    assert results["total"] > 0
    # Check that all results are from NT books
    # We might need a helper to know which are NT.
    # But usually MAT, JHN etc.
    # Random check first result
    first = results["results"][0]
    assert first["corpus"] == "NT"
    # assert first["book_code"] in ... (can import normalizer)

def test_search_lxx_only():
    """Verify search in LXX."""
    # "En arche" -> "ἀρχή" matches Gen 1:1
    lemma = "ἀρχή"
    results = find_in_index(lemma, lemma, "lxx", 10)
    
    assert results["total"] > 0
    found_gen_1_1 = False
    for r in results["results"]:
        if r["book_code"] in ["GEN", "Gen", "Genesis"] and r["chapter"] == 1 and r["verse"] == 1:
            found_gen_1_1 = True
            break
            
    assert found_gen_1_1, "Should find Gen 1:1 for arche in LXX"
    
    # Ensure no NT books
    for r in results["results"]:
        assert r["corpus"] == "LXX"

def test_search_all():
    """Verify combined search."""
    lemma = "θεός" # God, common in both
    results = find_in_index(lemma, lemma, "all", 100)
    
    has_nt = False
    has_lxx = False
    
    for r in results["results"]:
        if r["corpus"] == "NT": has_nt = True
        if r["corpus"] == "LXX": has_lxx = True
        
    assert has_nt
    assert has_lxx

def test_search_at_alias_logic():
    # Only verify logic via arg passing?
    # Logic is in CLI/worker dispatcher.
    # find_in_index handles "lxx", "nt", "all".
    pass
