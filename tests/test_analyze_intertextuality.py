import pytest
import json
from unittest.mock import MagicMock
from src.application.use_cases.intertext import AnalyzeIntertextualityUseCase
from src.domain.models import VerseItem, Verse

class MockVerse:
    def __init__(self, text):
        self.text = text

NT_TEXT = "καὶ ἐδίδασκεν καὶ ἔλεγεν αὐτοῖς Οὐ γέγραπται ὅτι Ὁ οἶκός μου οἶκος προσευχῆς κληθήσεται πᾶσιν τοῖς ἔθνεσιν; ὑμεῖς δὲ πεποιήκατε αὐτὸν σπήλαιον λῃστῶν."
OT_TEXT = "μὴ σπήλαιον λῃστῶν ὁ οἶκός μου οὗ ἐπικέκληται τὸ ὄνομά μου ἐπ’ αὐτῷ ἐκεῖ ἐνώπιον ὑμῶν καὶ ἐγὼ ἰδοὺ ἑώρακα λέγει κύριος"

@pytest.fixture
def use_case_intertext():
    mock_adapter = MagicMock()
    mock_adapter.normalizer.code_to_n1904 = {"MRK": "Mark", "JER": "Jeremiah"}
    mock_adapter.normalizer.n1904_to_tob = {"Mark": "Mc", "Jeremiah": "Jr"}
    mock_adapter.normalizer.is_nt = lambda code: code == "MRK"
    mock_adapter.normalize_reference.side_effect = lambda ref: {
        "Mc 11:17": ("MRK", 11, 17, "MRK.11.17"),
        "Jr 7.11": ("JER", 7, 11, "JER.7.11")
    }.get(ref, ("MRK", 11, 17, "MRK.11.17") if "Mc" in ref else ("JER", 7, 11, "JER.7.11"))
    
    def get_verse(b, c, v, version):
        if b == "MRK": return MockVerse(NT_TEXT)
        if b in ["JER", "MAL"]: return MockVerse(OT_TEXT)
        return None
        
    mock_adapter.get_verse.side_effect = get_verse
    
    ref_db = MagicMock()
    ref_db.in_memory_refs = {
        "MRK.11.17": {
            "relations": [{"target": "Jr 7.11"}]
        }
    }
    
    mock_nlp = MagicMock()
    mock_nlp.analyze_intertextuality.return_value = [{
        "id": "MRK.11.17 -> Jr 7.11", 
        "matches": [{"lemma": "οἶκος", "target_words": ["οἶκός"]}],
        "score": 1,
        "similarity": 0.85,
        "intertext_flags": ["E", "L"]
    }]
    
    use_case = AnalyzeIntertextualityUseCase(mock_adapter, mock_nlp, ref_db, mock_adapter.normalizer)
    yield use_case, mock_nlp

def test_analyze_intertextuality_success(use_case_intertext):
    use_case, mock_nlp = use_case_intertext
    
    use_case.bible_provider.normalize_reference.side_effect = lambda ref: {
        "Mc": None,
        "Mc 1:1": ("MRK", 1, 1),
        "Mc 11": ("MRK", 11, 0),
        "Jr 7.11": ("JER", 7, 11),
    }.get(ref, None)
    
    results = use_case.execute("Mc")
    
    mock_nlp.analyze_intertextuality.assert_called_once()
    payload = mock_nlp.analyze_intertextuality.call_args[0][0]
    
    assert len(payload) == 1
    assert payload[0]["source_ref"] == "MRK.11.17"
    
    assert len(results) == 1
    assert results[0]["similarity"] == 0.85
    assert results[0]["intertext_flags"] == ["E", "L"]

def test_analyze_intertextuality_invalid_book():
    use_case = AnalyzeIntertextualityUseCase(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    use_case.bible_provider.normalize_reference.return_value = None
    with pytest.raises(ValueError, match="Unknown book abbreviation"):
        use_case.execute("InvalidBook")
