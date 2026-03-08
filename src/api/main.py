from fastapi import FastAPI, Depends, Query
from typing import List, Optional
import sys
import os

# Ensure src is in path for imports to work as expected by existing code structure
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from contextlib import asynccontextmanager
from src.api.dtos import VerseResponseDTO, FindResponseDTO
from src.dependencies import DependencyContainer
from src.application.use_cases.search import SearchBibleUseCase
from src.application.use_cases.find import FindWordsUseCase

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initializing services...")
    yield
    # Shutdown

app = FastAPI(
    title="ScripturesApp API",
    description="Backend for ScripturesApp Native App",
    version="1.0.0",
    lifespan=lifespan
)

# Dependency Injection for Use Cases
def get_search_use_case():
    bible_adapter = DependencyContainer.get_bible_adapter()
    return SearchBibleUseCase(
        bible_adapter,
        DependencyContainer.get_ref_db(),
        bible_adapter.normalizer
    )

def get_find_use_case():
    bible_adapter = DependencyContainer.get_bible_adapter()
    return FindWordsUseCase(
        bible_adapter,
        DependencyContainer.get_nlp_adapter(),
        bible_adapter.normalizer
    )

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/v1/search", response_model=VerseResponseDTO)
def search_verses(
    q: str = Query(..., description="Bible reference (e.g. 'Gn 1:1')"),
    tr: Optional[List[str]] = Query(None, description="Translations to show (en, fr, gr, hb, ar)"),
    v: str = Query("N1904", description="Primary version (N1904, LXX, BHSA)"),
    bible: Optional[str] = Query(None, description="French version (tob, bj)"),
    crossref: bool = Query(False, description="Show cross references"),
    crossref_full: bool = Query(False, description="Display cross-references with text"),
    crossref_source: Optional[str] = Query(None, description="Filter cross-references by source"),
    use_case: SearchBibleUseCase = Depends(get_search_use_case)
):
    return use_case.execute(
        reference=q,
        translations=tr,
        version=v,
        french_version=bible,
        show_crossrefs=crossref,
        crossref_full=crossref_full,
        crossref_source=crossref_source
    )

@app.get("/api/v1/find", response_model=FindResponseDTO)
def find_words(
    q: str = Query(..., description="Search query (Greek word or French expression)"),
    tr: Optional[List[str]] = Query(None, description="Translations to show (en, fr, gr, hb, ar)"),
    v: Optional[str] = Query(None, description="Greek Corpus (nt, lxx, all)"),
    bible: Optional[str] = Query(None, description="French version (tob, bj)"),
    limit: int = Query(20, description="Max results"),
    use_case: FindWordsUseCase = Depends(get_find_use_case)
):
    """
    Find occurrences of a word or expression.
    Detects script (Greek vs Latin) to determine search mode.
    """
    return use_case.execute(
        query=q,
        limit=limit,
        bible=bible,
        version=v,
        translations=tr
    )
