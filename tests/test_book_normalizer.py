import pytest
import sys
import os

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from book_normalizer import BookNormalizer

@pytest.fixture
def data_dir():
    # Use the real data directory for now to verify integration with the real JSON
    # In a pure unit test, we would mock the file read.
    return os.path.join(os.path.dirname(__file__), '..', 'data')

@pytest.fixture
def normalizer(data_dir):
    return BookNormalizer(data_dir)

def test_normalization_valid(normalizer):
    # Test French input
    res = normalizer.normalize_reference("Mc 1:1")
    assert res is not None
    assert res[3] == "MRK.1.1"

    # Test English input
    res = normalizer.normalize_reference("Mark 1:1")
    assert res is not None
    assert res[3] == "MRK.1.1"

    res = normalizer.normalize_reference("John 1:1")
    assert res is not None
    assert res[3] == "JHN.1.1"

def test_normalization_with_full_name(normalizer):
    res = normalizer.normalize_reference("Jean 3:16")
    assert res is not None
    assert res[3] == "JHN.3.16"

def test_normalization_invalid(normalizer):
    res = normalizer.normalize_reference("InvalidBook 1:1")
    assert res is None

def test_abbreviations_loaded(normalizer):
    assert "Mc" in normalizer.abbreviations
    assert "Jn" in normalizer.abbreviations
    assert "Gn" in normalizer.abbreviations
    assert "Mt" in normalizer.abbreviations

def test_lxx_abbreviations_lookup(normalizer):
    # Verify that LXX-specific abbreviations are resolved
    lxx_cases = {
        "2Kgs": "2KI",
        "1Kgs": "1KI",
        "Exod": "EXO",
        "Qoh": "ECC",
        "Cant": "SNG"
    }
    
    for abbr, expected_code in lxx_cases.items():
        res = normalizer.normalize_reference(f"{abbr} 1:1")
        assert res is not None, f"Failed to normalize {abbr}"
        assert res[0] == expected_code, f"Expected {expected_code} for {abbr}, got {res[0]}"

def test_comprehensive_aliases(normalizer):
    cases = [
        ("Gn 1:1", "GEN"),
        ("Gen 1:1", "GEN"),
        ("Genèse 1:1", "GEN"),
        ("Genesis 1:1", "GEN"),
        ("Ex 1:1", "EXO"),
        ("Exode 1:1", "EXO"),
        ("Exodus 1:1", "EXO"),
        ("Mc 1:1", "MRK"),
        ("Marc 1:1", "MRK"),
        ("Mark 1:1", "MRK"),
        ("1 S 1:1", "1SA"),
        ("1 Samuel 1:1", "1SA"),
        ("2 R 1:1", "2KI"),
        ("2 Kings 1:1", "2KI"),
    ]
    for ref, expected_code in cases:
        res = normalizer.normalize_reference(ref)
        assert res is not None, f"Failed to normalize {ref}"
        assert res[0] == expected_code, f"Expected {expected_code} for {ref}, got {res[0]}"
