import pytest
from unittest.mock import MagicMock
from domain.models import Verse, Language
from presenter import VersePresenter

@pytest.fixture
def presenter():
    return VersePresenter()

def test_present_verse_classic_header(presenter, capsys):
    v = Verse(book_code="GEN", chapter=1, verse=1, text="In the beginning", language=Language.ENGLISH, version="N1904", node=100)
    presenter.present_verse(v)
    captured = capsys.readouterr()
    assert "GEN 1:1" in captured.out
    assert "In the beginning" in captured.out

def test_present_verse_localized_header(presenter, capsys):
    v = Verse(book_code="GEN", chapter=1, verse=1, text="In the beginning", language=Language.ENGLISH, version="N1904", node=100)
    # Simulate CLI passing localized name
    presenter.present_verse(v, book_name_override="Genèse")
    captured = capsys.readouterr()
    assert "Genèse 1:1" in captured.out
    assert "GEN 1:1" not in captured.out

def test_present_verse_compact_mode_1(presenter, capsys):
    v = Verse(book_code="GEN", chapter=1, verse=1, text="Text", language=Language.ENGLISH, version="N1904", node=100)
    presenter.present_verse(v, compact_mode=1)
    captured = capsys.readouterr()
    assert "v1. Text" in captured.out
    assert "GEN 1:1" not in captured.out

def test_present_verse_compact_mode_2(presenter, capsys):
    v = Verse(book_code="GEN", chapter=1, verse=1, text="Text", language=Language.ENGLISH, version="N1904", node=100)
    presenter.present_verse(v, compact_mode=2)
    captured = capsys.readouterr()
    assert "Text" in captured.out
    assert "v1." not in captured.out

def test_present_verse_parallels_prefixes(presenter, capsys):
    main_v = Verse(book_code="GEN", chapter=1, verse=1, text="Main", language=Language.GREEK, version="LXX", node=100)
    
    # Parallels
    v_tob = Verse(book_code="GEN", chapter=1, verse=1, text="French", language=Language.FRENCH, version="TOB", node=101)
    v_bj = Verse(book_code="GEN", chapter=1, verse=1, text="OtherFrench", language=Language.FRENCH, version="BJ", node=102)
    v_nav = Verse(book_code="GEN", chapter=1, verse=1, text="Arabic", language=Language.ARABIC, version="NAV", node=103)
    v_bhsa = Verse(book_code="GEN", chapter=1, verse=1, text="Hebrew", language=Language.HEBREW, version="BHSA", node=104)
    
    presenter.present_verse(main_v, additional_versions=[v_tob, v_bj, v_nav, v_bhsa])
    
    captured = capsys.readouterr()
    # Parity with Legacy: No prefixes, just text on new lines.
    assert "French" in captured.out
    assert "OtherFrench" in captured.out
    assert "Arabic" in captured.out
    
    assert "[TOB]" not in captured.out
    assert "[BJ]" not in captured.out
    
    assert "Hebrew" in captured.out
