import pytest
import sys
import os
import subprocess
from unittest.mock import MagicMock

# Mark all tests in this file as integration
pytestmark = pytest.mark.integration

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_cli(cmd):
    """Run a CLI command relative to project root and return stdout string."""
    full_cmd = f"bin/{cmd}"
    result = subprocess.run(full_cmd, shell=True, cwd=PROJECT_ROOT, 
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert result.returncode == 0, f"Command failed: {cmd}\nSTDERR: {result.stderr}"
    return result.stdout

def test_tob_bj_french_differences():
    # Verify TOB output for Gen 1:1
    # TOB: "Au commencement, Dieu créa..."
    out_tob = run_cli('tob "Gen 1:1"')
    assert "Au commencement" in out_tob
    assert "Dieu créa" in out_tob
    # Verify specific TOB phrasing if distinct, or just check that it's present.
    # TOB Gen 1:2 "ténèbre" (singular) vs BJ "ténèbres" (plural)? 
    # Let's check Gen 1:2 to be sure of diff.
    
def test_greek_outputs():
    # NT Greek (N1904) - Mark 1:1
    out_nt = run_cli('biblecli "Mk 1:1" --tr gr')
    assert "Ἀρχὴ τοῦ εὐαγγελίου" in out_nt
    
    # OT Greek (LXX) - Gen 1:1
    # biblecli automatically loads LXX for OT if not disabled
    out_ot = run_cli('biblecli "Gen 1:1" --tr gr')
    assert "ἐν ἀρχῇ ἐποίησεν" in out_ot

def test_hebrew_output():
    # Hebrew should appear for OT by default or with --tr hb
    out_hb = run_cli('biblecli "Gen 1:1" --tr hb')
    assert "בְּ" in out_hb # Check for Hebrew characters
    assert "אֱלֹהִ֑ים" in out_hb # Elohim

def test_arabic_output():
    # Arabic should appear with --tr ar
    # Use "Gen 1:1"
    out_ar = run_cli('biblecli "Gen 1:1" --tr ar')
    assert "فِي الْبَدْءِ" in out_ar

def test_tob_command_defaults():
    # tob command should show French
    out = run_cli('tob "Mk 1:1"')
    assert "Commencement" in out

def test_bj_command_defaults():
    # bj command should show French (BJ text)
    out = run_cli('bj "Mk 1:1"')
    assert "Commencement" in out
    # Verify it says [BJ] ? No, current implementation doesn't prefix [BJ].
    # But we can verify it works.

def test_french_diff_gen_1_2():
    # Verify content differences between TOB and BJ in Gen 1:2
    # TOB: "La terre était déserte et vide..."
    # BJ: "Or la terre était vide et vague..."
    
    out_tob = run_cli('tob "Gen 1:2"')
    out_bj = run_cli('bj "Gen 1:2"')
    
    # Assert TOB specific phrasing
    assert "déserte" in out_tob
    assert "vague" not in out_tob
    assert "la ténèbre" in out_tob # Singular in TOB
    
    # Assert BJ specific phrasing
    assert "vague" in out_bj
    assert "déserte" not in out_bj
    assert "les ténèbres" in out_bj # Plural in BJ
