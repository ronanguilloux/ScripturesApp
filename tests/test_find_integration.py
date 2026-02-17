"""
Integration tests for the find command with OdyCy lemmatization.
"""
import subprocess
import json
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


import unicodedata

def normalize(text):
    return unicodedata.normalize('NFC', text)

def run_find(word, limit=5):
    """Run the find worker and return parsed JSON output."""
    worker_path = os.path.join(project_root, "src", "application", "workers", "find_worker.py")
    venv_python = os.path.join(project_root, ".venv-spacy", "bin", "python3")
    
    result = subprocess.run(
        [venv_python, worker_path, word, "--limit", str(limit)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Worker failed: {result.stderr}")
    
    return json.loads(result.stdout)


def test_basic_lemma_search():
    """Test basic lemma search."""
    output = run_find("λαμβάνω", limit=3)
    
    assert normalize(output["lemma"]) == normalize("λαμβάνω")
    assert output["total"] > 200  # Should find 243+ occurrences
    assert len(output["results"]) == 3  # Limit works
    assert output["results"][0]["greek"]  # Greek text exists
    assert output["results"][0]["french"]  # French translation exists


def test_monotonic_input():
    """Test that monotonic input (no accents) works."""
    output = run_find("λαμβανω", limit=3)
    
    # Should resolve to λαμβάνω
    assert normalize(output["lemma"]) == normalize("λαμβάνω")
    assert output["total"] > 200


def test_perfect_participle():
    """Test perfect participle lemmatization."""
    output = run_find("ειληφα", limit=3)
    
    # Should resolve to λαμβάνω
    assert normalize(output["lemma"]) == normalize("λαμβάνω")
    assert output["total"] > 200


def test_suppletive_future():
    """Test suppletive future stem."""
    output = run_find("λήψεται", limit=3)
    
    # OdyCy might return the future stem as lemma or map to present
    # Accepting both for robustness
    lemma = normalize(output["lemma"])
    assert lemma in [normalize("λαμβάνω"), normalize("λήψω")]
    assert output["total"] > 0


def test_compound_verb():
    """Test compound verb recognition."""
    output = run_find("ἀπολάβῃ", limit=3)
    
    # Should recognize as compound of λαμβάνω
    assert "λαμβάνω" in output["lemma"]
    assert output["total"] > 0


def test_highlighting():
    """Test that highlights are present."""
    output = run_find("λαμβάνω", limit=1)
    
    assert len(output["results"]) > 0
    assert "highlights" in output["results"][0]
    assert len(output["results"][0]["highlights"]) > 0


if __name__ == "__main__":
    print("Running find command integration tests...")
    
    tests = [
        ("Basic lemma search", test_basic_lemma_search),
        ("Monotonic input", test_monotonic_input),
        ("Perfect participle", test_perfect_participle),
        ("Suppletive future", test_suppletive_future),
        ("Compound verb", test_compound_verb),
        ("Highlighting", test_highlighting),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            print(f"✅ {name}")
            passed += 1
        except Exception as e:
            print(f"❌ {name}: {e}")
            failed += 1
    
    print(f"\n{passed}/{len(tests)} tests passed")
    sys.exit(0 if failed == 0 else 1)
