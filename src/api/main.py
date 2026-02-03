from fastapi import FastAPI, Depends, Query
from typing import List, Optional
import sys
import os

# Ensure src is in path for imports to work as expected by existing code structure
# This allows 'import application...' to work if running from root as 'uvicorn src.api.main:app'
# provided we add 'src' to path.
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from application.services import BibleService
from domain.models import VerseResponse

app = FastAPI(
    title="BibleCLI API",
    description="Backend for BibleCLI Native App",
    version="1.0.0"
)

# Dependency Injection for Service
def get_service():
    return BibleService()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/v1/search", response_model=VerseResponse)
def search_verses(
    q: str = Query(..., description="Bible reference (e.g. 'Gn 1:1')"),
    tr: Optional[List[str]] = Query(None, description="Translations to show (en, fr, gr, hb, ar)"),
    v: str = Query("N1904", description="Primary version (N1904, LXX, BHSA)"),
    bible: Optional[str] = Query(None, description="French version (tob, bj)"),
    crossref: bool = Query(False, description="Show cross references"),
    crossref_full: bool = Query(False, description="Display cross-references with text"),
    crossref_source: Optional[str] = Query(None, description="Filter cross-references by source"),
    service: BibleService = Depends(get_service)
):
    return service.search(
        reference=q,
        translations=tr,
        version=v,
        french_version=bible,
        show_crossrefs=crossref,
        crossref_full=crossref_full,
        crossref_source=crossref_source
    )
