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
    rel_type: CrossReferenceType
    note: Optional[str] = None
    
    model_config = ConfigDict(frozen=True)

class VerseCrossReferences(BaseModel):
    notes: List[str] = Field(default_factory=list)
    relations: List[CrossReferenceRelation] = Field(default_factory=list)
    
    # VerseCrossReferences holds lists, so it cannot be strictly frozen without Tuple conversion.
    # Keeping it mutable for ease of construction.
