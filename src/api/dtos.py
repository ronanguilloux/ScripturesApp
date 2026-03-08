from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any
from src.domain.models import Language, CrossReferenceType

class BookDTO(BaseModel):
    code: str
    name_en: str
    name_fr: Optional[str] = None
    chapters: int
    model_config = ConfigDict(frozen=True)

class VerseDTO(BaseModel):
    book_code: str
    chapter: int
    verse: int
    text: str
    language: Language
    version: str
    book_name: Optional[str] = None
    node: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(frozen=True)

class CrossReferenceRelationDTO(BaseModel):
    target_ref: str 
    target_ref_localized: Optional[str] = None
    rel_type: CrossReferenceType
    note: Optional[str] = None
    text: Optional[str] = None
    model_config = ConfigDict(frozen=True)

class VerseCrossReferencesDTO(BaseModel):
    notes: List[str] = Field(default_factory=list)
    relations: List[CrossReferenceRelationDTO] = Field(default_factory=list)

class VerseItemDTO(BaseModel):
    ref: str
    primary: VerseDTO
    parallels: List[VerseDTO] = Field(default_factory=list)
    model_config = ConfigDict(frozen=True)

class VerseResponseDTO(BaseModel):
    reference: str
    verses: List[VerseItemDTO]
    cross_references: Optional[VerseCrossReferencesDTO] = None
    model_config = ConfigDict(frozen=True)

class FindResultItemDTO(BaseModel):
    ref: str = Field(..., description="Verse reference (e.g. 'Mt 1:1')")
    book_code: str = Field(..., description="Standard book code")
    chapter: int
    verse: int
    text: str = Field(..., description="Main text content (Greek or French)")
    translations: Dict[str, str] = Field(default_factory=dict, description="Parallel translations")
    highlights: List[str] = Field(default_factory=list, description="Words to highlight in the main text")
    model_config = ConfigDict(frozen=True)

class FindResponseDTO(BaseModel):
    lemma: str = Field(..., description="The query lemma or expression")
    original: str = Field(..., description="The original query string")
    lemma_gloss: str = Field(default="", description="Gloss/Definition of the lemma")
    total: int = Field(..., description="Total number of results found")
    results: List[FindResultItemDTO] = Field(default_factory=list)
    model_config = ConfigDict(frozen=True)
