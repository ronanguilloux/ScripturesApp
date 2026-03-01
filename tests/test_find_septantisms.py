import pytest
import json
from unittest.mock import patch, MagicMock
from src.application.services import BibleService
from src.domain.models import VerseItem, Verse

class MockVerse:
    def __init__(self, text):
        self.text = text

# Sample texts
NT_TEXT = "καὶ ἐδίδασκεν καὶ ἔλεγεν αὐτοῖς Οὐ γέγραπται ὅτι Ὁ οἶκός μου οἶκος προσευχῆς κληθήσεται πᾶσιν τοῖς ἔθνεσιν; ὑμεῖς δὲ πεποιήκατε αὐτὸν σπήλαιον λῃστῶν."
OT_TEXT = "μὴ σπήλαιον λῃστῶν ὁ οἶκός μου οὗ ἐπικέκληται τὸ ὄνομά μου ἐπ’ αὐτῷ ἐκεῖ ἐνώπιον ὑμῶν καὶ ἐγὼ ἰδοὺ ἑώρακα λέγει κύριος"

@pytest.fixture
def bible_service():
    with patch('src.application.services.AdapterFactory.get') as mock_get:
        mock_adapter = MagicMock()
        mock_adapter.normalizer.code_to_n1904 = {"MRK": "Mark", "JER": "Jeremiah"}
        mock_adapter.normalizer.n1904_to_tob = {"Mark": "Mc", "Jeremiah": "Jr"}
        mock_adapter.normalizer.is_nt = lambda code: code == "MRK"
        mock_adapter.normalize_reference.side_effect = lambda ref: {
            "Mc 1:1": ("MRK", 1, 1, "MRK.1.1"),
            "Jr 7.11": ("JER", 7, 11, "JER.7.11")
        }.get(ref, ("MRK", 1, 1, "MRK.1.1") if "Mc" in ref else ("JER", 7, 11, "JER.7.11"))
        
        # Mock verse fetching
        def get_verse(b, c, v, version):
            if b == "MRK": return MockVerse(NT_TEXT)
            if b in ["JER", "MAL"]: return MockVerse(OT_TEXT)
            return None
            
        mock_adapter.get_verse.side_effect = get_verse
        mock_get.return_value = mock_adapter
        
        service = BibleService(adapter=mock_adapter)
        
        # Mock Ref DB
        service.ref_db = MagicMock()
        service.ref_db.in_memory_refs = {
            "MRK.11.17": {
                "relations": [{"target": "Jr 7.11"}]
            },
            "MRK.1.2": {
                "relations": [{"target": "Mal 3.1"}]
            }
        }
        
        # Mock the subprocess worker since we don't want to load spacy in unit test
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            # Return a fake json result
            mock_result.stdout = json.dumps([{
                "id": "MRK.11.17 -> Jr 7.11", 
                "matches": [{"lemma": "οἶκος", "target_words": ["οἶκός"]}],
                "score": 1
            }])
            mock_run.return_value = mock_result
            
            yield service, mock_run

def test_find_septantisms_success(bible_service):
    service, mock_run = bible_service
    # "Mc" will fallback to normalize_reference("Mc 1:1") -> MRK, so prefix is MRK.
    # It should include both MRK.11.17 and MRK.1.2
    
    # We need to mock normalize_reference properly for "Mc" vs "Mc 11"
    service.adapter.normalize_reference.side_effect = lambda ref: {
        "Mc": None,
        "Mc 1:1": ("MRK", 1, 1),
        "Mc 11": ("MRK", 11, 0),
        "Jr 7.11": ("JER", 7, 11),
        "Mal 3.1": ("MAL", 3, 1)
    }.get(ref, None)
    
    results = service.find_septantisms("Mc")
    
    # Assert worker was called
    mock_run.assert_called_once()
    kwargs = mock_run.call_args.kwargs
    payload = json.loads(kwargs['input'])
    
    # Since "Mc" searches the whole book, both refs should be included
    assert len(payload) == 2
    
def test_find_septantisms_chapter_filter(bible_service):
    service, mock_run = bible_service
    
    service.adapter.normalize_reference.side_effect = lambda ref: {
        "Mc 11": ("MRK", 11, 0),
        "Jr 7.11": ("JER", 7, 11),
        "Mal 3.1": ("MAL", 3, 1)
    }.get(ref, None)
    
    results = service.find_septantisms("Mc 11")
    
    # Assert worker was called
    mock_run.assert_called_once()
    kwargs = mock_run.call_args.kwargs
    payload = json.loads(kwargs['input'])
    
    # It should only include MRK.11.17 and NOT MRK.1.2
    assert len(payload) == 1
    assert payload[0]["source_ref"] == "MRK.11.17"
    assert payload[0]["source_text"] == NT_TEXT
    assert payload[0]["target_text"] == OT_TEXT
    
    assert len(results) == 1
    assert results[0]["score"] == 1
    assert results[0]["matches"][0]["lemma"] == "οἶκος"

def test_find_septantisms_invalid_book():
    service = BibleService() # real service init fails without adapter if data missing, but we can mock
    with patch.object(service.adapter, 'normalize_reference', return_value=None):
        with pytest.raises(ValueError, match="Unknown book abbreviation"):
            service.find_septantisms("InvalidBook")
