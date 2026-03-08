from typing import List, Optional
from src.domain.models import FindResponse, FindResultItem
from src.ports.bible_provider import BibleProvider
from src.ports.nlp_provider import NLPProvider
from src.book_normalizer import BookNormalizer

class FindWordsUseCase:
    def __init__(self, bible_provider: BibleProvider, nlp_provider: NLPProvider, normalizer: BookNormalizer):
        self.bible_provider = bible_provider
        self.nlp_provider = nlp_provider
        self.normalizer = normalizer

    def execute(
        self,
        query: str,
        limit: int = 20,
        bible: Optional[str] = None,
        version: Optional[str] = None,
        translations: Optional[List[str]] = None
    ) -> FindResponse:
        
        def is_greek_script(text: str) -> bool:
            for char in text:
                if '\u0370' <= char <= '\u03ff' or '\u1f00' <= char <= '\u1fff':
                    return True
            return False

        is_greek = is_greek_script(query)
        
        mode = "greek"
        search_corpus = "nt"
        french_version = "tob"
        
        if bible:
            french_version = bible.lower()
            if french_version not in ["tob", "bj"]:
                 raise ValueError(f"Invalid french version: {bible}. Use 'tob' or 'bj'.")

        if is_greek:
            mode = "greek"
            if version:
                if version.lower() not in ["nt", "lxx", "all", "at"]:
                     raise ValueError(f"Invalid greek version: {version}. Use 'nt', 'lxx', 'all'.")
                search_corpus = version.lower()
                if search_corpus == "at": search_corpus = "lxx"
        else:
            if bible:
                mode = "french"
                search_corpus = french_version
            elif version:
                mode = "greek"
                search_corpus = version.lower()
                if search_corpus == "at": search_corpus = "lxx"
            else:
                raise ValueError(f"Ambiguous search for latin query '{query}'. Specify french_version (tob/bj) or greek version (nt/lxx).")

        # Invoke NLP Provider instead of subprocess
        output = self.nlp_provider.find_words(query, limit, search_corpus, mode)

        lemma = output.get("lemma", query)
        count = output.get("total", 0)
        lemma_gloss = output.get("lemma_gloss", "")
        raw_results = output.get("results", [])
        
        final_results = []

        for item in raw_results:
            b = item.get("book_code")
            c = item.get("chapter")
            v = item.get("verse")
            
            main_text = item.get("greek") or item.get("french") or ""
            
            translations_map = {}
            if translations:
                is_nt = self.normalizer.is_nt(b)
                
                for t in translations:
                     t_code = t.lower()
                     v_code = None
                     if t_code == 'en': v_code = 'N1904_EN'
                     elif t_code == 'fr': v_code = (french_version or 'tob').upper()
                     elif t_code == 'gr': v_code = 'N1904' if is_nt else 'LXX'
                     elif t_code == 'hb': v_code = 'BHSA' 
                     elif t_code in ['tob', 'bj', 'nav', 'lxx', 'bhsa', 'n1904']: v_code = t_code.upper()
                     
                     if v_code:
                         try:
                             p_v = self.bible_provider.get_verse(b, c, v, version=v_code)
                             if p_v:
                                 translations_map[v_code] = p_v.text
                         except: pass

            final_results.append(FindResultItem(
                ref=item.get("ref"),
                book_code=b,
                chapter=c,
                verse=v,
                text=main_text,
                translations=translations_map,
                highlights=item.get("highlights", [])
            ))

        return FindResponse(
            lemma=lemma,
            original=query,
            lemma_gloss=lemma_gloss,
            total=count,
            results=final_results
        )
