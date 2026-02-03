import subprocess
import pytest

def test_cli_range_output():
    """
    Regression Test: Ensure 'bin/biblecli "Mc 7:8-9"' returns only verses 8 and 9.
    """
    cmd = ["bin/biblecli", "Mc 7:8-9"]
    
    # Run command
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assert result.returncode == 0, f"Command failed with output: {result.stderr}"
    
    output = result.stdout
    
    # Check for presence of requested verses
    # Mk 7:8 "Vous laissez de côté..."
    assert "Marc 7:8" in output
    assert "Vous laissez de côté" in output
    
    # Mk 7:9 "Il leur disait: «Vous repoussez..."
    assert "Marc 7:9" in output
    assert "Vous repoussez bel et bien" in output
    
    # Check for ABSENCE of surrounding verses (to verify it's not the whole chapter)
    # Mk 7:1 "Les Pharisiens..."
    assert "Marc 7:1" not in output
    assert "Les Pharisiens" not in output
    
    # Mk 7:7 "...préceptes d'hommes."
    assert "Marc 7:7" not in output
    
    # Mk 7:10 "Car Moïse a dit..."
    assert "Marc 7:10" not in output
