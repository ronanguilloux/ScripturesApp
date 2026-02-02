import os
import json
import subprocess
import pytest

@pytest.fixture
def setup_repro_files():
    """Create temporary reference files for testing."""
    cwd = os.getcwd()
    data_dir = os.path.join(cwd, "data")
    
    file_a = os.path.join(data_dir, "references_ot_test_agg_A.json")
    file_b = os.path.join(data_dir, "references_ot_test_agg_B.json")
    
    content_a = {
        "version": "1.0",
        "cross_references": [
            {
                "source": "GEN.1.1",
                "relations": [
                    {
                        "target": "JHN.1.1",
                        "type": "allusion",
                        "note": "Source A Note"
                    }
                ]
            }
        ]
    }
    
    content_b = {
        "version": "1.0",
        "cross_references": [
            {
                "source": "GEN.1.1",
                "relations": [
                    {
                        "target": "JHN.1.1",
                        "type": "allusion",
                        "note": "Source B Note"
                    }
                ]
            }
        ]
    }
    
    with open(file_a, "w") as f:
        json.dump(content_a, f)
        
    with open(file_b, "w") as f:
        json.dump(content_b, f)
        
    yield
    
    # Cleanup
    if os.path.exists(file_a):
        os.remove(file_a)
    if os.path.exists(file_b):
        os.remove(file_b)

def test_aggregation(setup_repro_files):
    """Test that references from both sources are displayed."""
    cmd = ["bin/biblecli", "Gen 1:1", "-c"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assert result.returncode == 0
    assert "Source A Note" in result.stdout
    assert "Source B Note" in result.stdout

def test_segregation(setup_repro_files):
    """Test that -s flag filters sources."""
    # Filter for Source A (filename contains 'test_agg_A')
    cmd = ["bin/biblecli", "Gen 1:1", "-c", "-s", "test_agg_A"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assert result.returncode == 0
    assert "Source A Note" in result.stdout
    assert "Source B Note" not in result.stdout
