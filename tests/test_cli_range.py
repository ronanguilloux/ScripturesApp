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

def test_cli_multi_passage_same_chapter():
    """'Lc 24:24-26;44' -> verses 24-26 then 44 of Luke 24, nothing else."""
    result = subprocess.run(["bin/biblecli", "Lc 24:24-26;44"], capture_output=True, text=True)

    assert result.returncode == 0, f"Command failed with output: {result.stderr}"
    output = result.stdout

    for ref in ["Luc 24:24", "Luc 24:25", "Luc 24:26", "Luc 24:44"]:
        assert ref in output, f"{ref} missing"

    for ref in ["Luc 24:23", "Luc 24:27", "Luc 24:43", "Luc 24:45"]:
        assert ref not in output, f"{ref} should not be displayed"


def test_cli_multi_passage_other_chapter():
    """'Lc 23:1-2;24:24-26' -> Luke 23:1-2 then Luke 24:24-26."""
    result = subprocess.run(["bin/biblecli", "Lc 23:1-2;24:24-26"], capture_output=True, text=True)

    assert result.returncode == 0, f"Command failed with output: {result.stderr}"
    output = result.stdout

    for ref in ["Luc 23:1", "Luc 23:2", "Luc 24:24", "Luc 24:25", "Luc 24:26"]:
        assert ref in output, f"{ref} missing"

    for ref in ["Luc 23:3", "Luc 24:23", "Luc 24:27"]:
        assert ref not in output, f"{ref} should not be displayed"


def test_cli_ambiguous_continuation_errors():
    """'Lc 23;24' is ambiguous (chapter 24 or verse 24?) -> explicit error, not a guess."""
    result = subprocess.run(["bin/biblecli", "Lc 23;24"], capture_output=True, text=True)

    assert result.returncode == 1
