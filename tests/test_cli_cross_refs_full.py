import subprocess
import pytest

def test_cli_cross_ref_full_range_text():
    """
    Regression Test: Ensure 'bin/biblecli "Mc 7:8" -f -t fr' 
    1. Returns Mc 7:8 in French.
    2. Lists Mc 7:3-4 as a cross reference.
    3. Prints the full text of Mc 7:3-4 (multiverse cross ref).
    """
    cmd = ["bin/biblecli", "Mc 7:8", "-f", "-t", "fr"]
    
    # Run command
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assert result.returncode == 0, f"Command failed with output: {result.stderr}"
    
    output = result.stdout
    
    # 1. Main Verse (Mc 7:8)
    assert "Marc 7:8" in output
    assert "Vous laissez de côté" in output # French text start
    
    # 2. Cross Ref Citation
    assert "Marc 7:3-4" in output
    
    # 3. Cross Ref Full Text (Verse 3 and Verse 4)
    # Verse 3 part
    assert "En effet, les Pharisiens" in output 
    # Verse 4 part
    assert "en revenant du marché" in output
