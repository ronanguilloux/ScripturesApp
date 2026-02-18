from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class Language(str, Enum):
    ENGLISH = "en"
    FRENCH = "fr"
    GREEK = "gr"
    HEBREW = "hb"
    ARABIC = "ar"

class Book(BaseModel):
    code: str  # Standard 3-letter code (e.g., "GEN")
    name_en: str
    name_fr: Optional[str] = None
    chapters: int
    
    model_config = ConfigDict(frozen=True)

class VerseRef(BaseModel):
    book_code: str
    chapter: int
    verse: int

    def __str__(self):
        return f"{self.book_code} {self.chapter}:{self.verse}"
    
    model_config = ConfigDict(frozen=True)

class Verse(VerseRef):
    text: str
    language: Language
    version: str # e.g. "N1904", "TOB", "LXX"
    book_name: Optional[str] = None
    node: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(frozen=True)


class CrossReferenceType(str, Enum):
    PARALLEL = "parallel"
    QUOTATION = "quotation"
    ALLUSION = "allusion"
    OTHER = "other"

class CrossReferenceRelation(BaseModel):
    target_ref: str 
    target_ref_localized: Optional[str] = None
    rel_type: CrossReferenceType
    note: Optional[str] = None
    text: Optional[str] = None
    
    model_config = ConfigDict(frozen=True)

class VerseCrossReferences(BaseModel):
    notes: List[str] = Field(default_factory=list)
    relations: List[CrossReferenceRelation] = Field(default_factory=list)
    
    # VerseCrossReferences holds lists, so it cannot be strictly frozen without Tuple conversion.
    # Keeping it mutable for ease of construction.

class VerseItem(BaseModel):
    ref: str
    primary: Verse
    parallels: List[Verse] = Field(default_factory=list)
    
    model_config = ConfigDict(frozen=True)

class VerseResponse(BaseModel):
    reference: str
    verses: List[VerseItem] # Structured verse data
    cross_references: Optional[VerseCrossReferences] = None
    
    model_config = ConfigDict(frozen=True)

class SearchResult(BaseModel):
    ref: str
    text: str
    translation: str
    score: float
    book: str
    chapter: int
    verse: int

    model_config = ConfigDict(frozen=True)

class FindResultItem(BaseModel):
    ref: str = Field(..., description="Verse reference (e.g. 'Mt 1:1')")
    book_code: str = Field(..., description="Standard book code")
    chapter: int
    verse: int
    text: str = Field(..., description="Main text content (Greek or French)")
    translations: Dict[str, str] = Field(default_factory=dict, description="Parallel translations")
    highlights: List[str] = Field(default_factory=list, description="Words to highlight in the main text")
    
    model_config = ConfigDict(frozen=True)

class FindResponse(BaseModel):
    lemma: str = Field(..., description="The query lemma or expression")
    original: str = Field(..., description="The original query string")
    lemma_gloss: str = Field(default="", description="Gloss/Definition of the lemma")
    total: int = Field(..., description="Total number of results found")
    results: List[FindResultItem] = Field(default_factory=list)
    
    model_config = ConfigDict(frozen=True)


