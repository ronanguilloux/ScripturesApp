from abc import ABC, abstractmethod
from typing import List, Optional
from domain.models import Verse, Book, VerseCrossReferences

class BibleProvider(ABC):
    """
    Port interface that any data source (Text-Fabric, SQL, Mock) must implement.
    """

    @abstractmethod
    def get_verse(self, book_code: str, chapter: int, verse: int, version: str) -> Optional[Verse]:
        """Fetch a single verse text."""
        pass

    @abstractmethod
    def get_chapter(self, book_code: str, chapter: int, version: str) -> List[Verse]:
        """Fetch all verses in a chapter."""
        pass

    @abstractmethod
    def search(self, query: str, version: str) -> List[Verse]:
        """Full text search."""
        pass
    
    @abstractmethod
    def get_cross_references(self, book_code: str, chapter: int, verse: int) -> VerseCrossReferences:
        """Fetch cross references and notes for a verse."""
        pass

class MetadataProvider(ABC):
    """
    Port for structural metadata (book names, chapter counts).
    """
    
    @abstractmethod
    def get_book_info(self, book_code: str) -> Optional[Book]:
        pass

    @abstractmethod
    def normalize_reference(self, ref_string: str) -> Optional[tuple[str, int, int]]:
        """Parses 'Gen 1:1' -> ('GEN', 1, 1)"""
        pass
