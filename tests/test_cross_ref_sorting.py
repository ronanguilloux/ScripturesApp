import os
import json
import subprocess
import pytest

@pytest.fixture
def setup_sorting_files():
    """Create temporary reference file with mixed order references."""
    cwd = os.getcwd()
    data_dir = os.path.join(cwd, "data")
    
    file_path = os.path.join(data_dir, "references_ot_test_sorting.json")
    
    # Create refs in random/reverse biblical order
    # Revelation (REV) comes after Genesis (GEN)
    # Psalms (PSA) comes between
    # Input order: REV, GEN, PSA
    # Expected Output order: GEN, PSA, REV
    
    content = {
        "version": "1.0",
        "cross_references": [
            {
                "source": "GEN.1.1",
                "relations": [
                    {
                        "target": "REV.1.1",
                        "type": "other",
                        "note": "Revelation Ref"
                    },
                    {
                        "target": "GEN.1.2",
                        "type": "other",
                        "note": "Genesis Ref"
                    },
                    {
                        "target": "PSA.23.1",
                        "type": "other",
                        "note": "Psalms Ref"
                    }
                ]
            }
        ]
    }
    
    with open(file_path, "w") as f:
        json.dump(content, f)
        
    yield
    
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)

def test_sorting_order(setup_sorting_files):
    """Test that references are sorted by biblical book order."""
    cmd = ["bin/biblecli", "Gen 1:1", "-c", "-s", "test_sorting"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assert result.returncode == 0
    output = result.stdout
    
    # Find positions of references
    pos_gen = output.find("Genesis Ref")
    pos_psa = output.find("Psalms Ref")
    pos_rev = output.find("Revelation Ref")
    
    # Verify all present
    assert pos_gen != -1
    assert pos_psa != -1
    assert pos_rev != -1
    
    # Verify Order: GEN < PSA < REV
    assert pos_gen < pos_psa, f"Genesis ({pos_gen}) should be before Psalms ({pos_psa})"
    assert pos_psa < pos_rev, f"Psalms ({pos_psa}) should be before Revelation ({pos_rev})"
