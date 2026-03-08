from abc import ABC, abstractmethod
from typing import List, Dict, Any

class NLPProvider(ABC):
    """
    Port interface for interacting with NLP models and workers.
    """
    @abstractmethod
    def find_words(self, query: str, limit: int, search_corpus: str, mode: str) -> Dict[str, Any]:
        """Searches for words in the specified corpus."""
        pass

    @abstractmethod
    def find_septantisms(self, payload: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyzes intertextual pairs to find septantisms."""
        pass

    @abstractmethod
    def analyze_intertextuality(self, payload: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyzes intertextual links for E/NE and L/NL categorization."""
        pass

    @abstractmethod
    def analyze_greek_word(self, word: str) -> List[Dict[str, Any]]:
        """Performs full morphological and syntactic analysis on a Greek word."""
        pass
