from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

class Language(str, Enum):
    ENGLISH = "en"
    FRENCH = "fr"
    GREEK = "gr"
    HEBREW = "hb"
    ARABIC = "ar"

@dataclass(frozen=True)
class Book:
    code: str
    name_en: str
    chapters: int
    name_fr: Optional[str] = None

@dataclass(frozen=True)
class VerseRef:
    book_code: str
    chapter: int
    verse: int

    def __str__(self):
        return f"{self.book_code} {self.chapter}:{self.verse}"

@dataclass(frozen=True)
class Verse(VerseRef):
    text: str = ""
    language: Language = Language.ENGLISH
    version: str = ""
    book_name: Optional[str] = None
    node: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class CrossReferenceType(str, Enum):
    PARALLEL = "parallel"
    QUOTATION = "quotation"
    ALLUSION = "allusion"
    OTHER = "other"

@dataclass(frozen=True)
class CrossReferenceRelation:
    target_ref: str 
    rel_type: CrossReferenceType
    target_ref_localized: Optional[str] = None
    note: Optional[str] = None
    text: Optional[str] = None

@dataclass
class VerseCrossReferences:
    notes: List[str] = field(default_factory=list)
    relations: List[CrossReferenceRelation] = field(default_factory=list)

@dataclass(frozen=True)
class VerseItem:
    ref: str
    primary: Verse
    parallels: List[Verse] = field(default_factory=list)

@dataclass(frozen=True)
class VerseResponse:
    reference: str
    verses: List[VerseItem]
    cross_references: Optional[VerseCrossReferences] = None

@dataclass(frozen=True)
class SearchResult:
    ref: str
    text: str
    translation: str
    score: float
    book: str
    chapter: int
    verse: int

@dataclass(frozen=True)
class FindResultItem:
    ref: str
    book_code: str
    chapter: int
    verse: int
    text: str
    translations: Dict[str, str] = field(default_factory=dict)
    highlights: List[str] = field(default_factory=list)

@dataclass(frozen=True)
class FindResponse:
    lemma: str
    original: str
    total: int
    lemma_gloss: str = ""
    results: List[FindResultItem] = field(default_factory=list)
