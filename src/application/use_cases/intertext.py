from typing import List, Dict, Any, Optional
from src.ports.bible_provider import BibleProvider
from src.ports.nlp_provider import NLPProvider
from src.references_db import ReferenceDatabase
from src.book_normalizer import BookNormalizer
import re
import unicodedata

class AnalyzeIntertextualityUseCase:
    def __init__(self, bible_provider: BibleProvider, nlp_provider: NLPProvider, ref_db: ReferenceDatabase, normalizer: BookNormalizer):
        self.bible_provider = bible_provider
        self.nlp_provider = nlp_provider
        self.ref_db = ref_db
        self.normalizer = normalizer

    def execute(self, book_abbr: str, french_version: Optional[str] = None) -> List[Dict[str, Any]]:
        range_match = re.search(r'(?:[.:]\s*)(\d+)(?:\s*-\s*(\d+))', book_abbr)
        start_verse, end_verse = 0, 0
        if range_match:
            start_verse = int(range_match.group(1))
            end_verse = int(range_match.group(2))
            
        parsed = self.bible_provider.normalize_reference(book_abbr)
        
        if parsed:
            book_code, filter_chapter, filter_verse = parsed
            if start_verse and end_verse:
                filter_verse = 0 
        else:
            parsed = self.bible_provider.normalize_reference(f"{book_abbr} 1:1")
            if not parsed:
                raise ValueError(f"Unknown book abbreviation: {book_abbr}")
            book_code, filter_chapter, filter_verse = parsed[0], 0, 0
            
        if not self.normalizer.is_nt(book_code):
            raise ValueError(f"Intertextuality analysis is primarily designed to assess how NT books quote the OT. '{book_code}' is not an NT book.")

        self.ref_db.load_all(source_filter=None, scope='nt')
        payload = []
        
        for ref_key, data in self.ref_db.in_memory_refs.items():
            if not ref_key.startswith(f"{book_code}."):
                continue
                
            parts = ref_key.split(".")
            if len(parts) != 3: continue
            b, c, v = parts[0], int(parts[1]), int(parts[2])
            
            if filter_chapter > 0 and c != filter_chapter: continue
            if start_verse > 0 and end_verse > 0:
                if not (start_verse <= v <= end_verse): continue
            elif filter_verse > 0:
                if v != filter_verse: continue
            
            try:
                source_verse = self.bible_provider.get_verse(b, c, v, version="N1904")
                if not source_verse or not source_verse.text: continue
                source_text = source_verse.text
                
                source_fr = None
                if french_version:
                    fr_v = self.bible_provider.get_verse(b, c, v, version=french_version)
                    if fr_v: source_fr = fr_v.text
            except:
                continue
            
            for rel in data.get("relations", []):
                target_ref = rel["target"]
                
                parsed_target = self.bible_provider.normalize_reference(target_ref)
                if not parsed_target: continue
                tb, tc, tv = parsed_target
                
                if self.normalizer.is_nt(tb):
                    continue 
                    
                try:
                    target_verse = self.bible_provider.get_verse(tb, tc, tv, version="LXX")
                    if not target_verse or not target_verse.text: continue
                    target_text = target_verse.text
                    
                    target_fr = None
                    if french_version:
                        fr_tgt = self.bible_provider.get_verse(tb, tc, tv, version=french_version)
                        if fr_tgt: target_fr = fr_tgt.text
                except:
                    continue
                    
                pair_id = f"{ref_key} -> {target_ref}"
                payload.append({
                    "id": pair_id,
                    "source_ref": ref_key,
                    "target_ref": target_ref,
                    "source_text": source_text,
                    "target_text": target_text,
                    "source_fr": source_fr,
                    "target_fr": target_fr
                })

        if not payload:
            return []

        # Delegate execution to explicit port
        output = self.nlp_provider.analyze_intertextuality(payload)

        final_results = []
        payload_map = {p["id"]: p for p in payload}
        
        lemma_to_gloss = {}
        # Needs direct access to N1904 TF API for glosses, or NLP provider could provide.
        # Since bible_provider has it, we just check if it has n1904
        if hasattr(self.bible_provider, 'n1904') and self.bible_provider.n1904:
            F = self.bible_provider.n1904.api.F
            target_lemmas = set()
            for item in output:
                for match in item.get("matches", []):
                    target_lemmas.add(unicodedata.normalize('NFC', match["lemma"]))
                        
            if target_lemmas:
                for w in F.otype.s('word'):
                    db_lemma = F.lemma.v(w)
                    if not db_lemma: continue
                    db_lemma_nfc = unicodedata.normalize('NFC', db_lemma)
                    if db_lemma_nfc in target_lemmas and db_lemma_nfc not in lemma_to_gloss:
                        lemma_to_gloss[db_lemma_nfc] = F.gloss.v(w)
                        if len(lemma_to_gloss) == len(target_lemmas):
                            break
            
        for item in output:
            orig = payload_map.get(item["id"], {})
            item["source_ref"] = orig.get("source_ref")
            item["target_ref"] = orig.get("target_ref")
            item["source_text"] = orig.get("source_text")
            item["target_text"] = orig.get("target_text")
            item["source_fr"] = orig.get("source_fr")
            item["target_fr"] = orig.get("target_fr")
            
            for match in item.get("matches", []):
                lemma_nfc = unicodedata.normalize('NFC', match["lemma"])
                if lemma_nfc in lemma_to_gloss:
                    match["gloss"] = lemma_to_gloss[lemma_nfc]
                            
            final_results.append(item)
                
        final_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return final_results


class FindSeptantismsUseCase:
    def __init__(self, bible_provider: BibleProvider, nlp_provider: NLPProvider, ref_db: ReferenceDatabase, normalizer: BookNormalizer):
        self.bible_provider = bible_provider
        self.nlp_provider = nlp_provider
        self.ref_db = ref_db
        self.normalizer = normalizer

    def execute(self, book_abbr: str, french_version: Optional[str] = None) -> List[Dict[str, Any]]:
        range_match = re.search(r'(?:[.:]\s*)(\d+)(?:\s*-\s*(\d+))', book_abbr)
        start_verse = 0
        end_verse = 0
        if range_match:
            start_verse = int(range_match.group(1))
            end_verse = int(range_match.group(2))
            
        parsed = self.bible_provider.normalize_reference(book_abbr)
        
        if parsed:
            book_code, filter_chapter, filter_verse = parsed
            if start_verse and end_verse:
                filter_verse = 0 
        else:
            parsed = self.bible_provider.normalize_reference(f"{book_abbr} 1:1")
            if not parsed:
                raise ValueError(f"Unknown book abbreviation or reference: {book_abbr}")
            book_code, filter_chapter, filter_verse = parsed[0], 0, 0
            
        is_nt = self.normalizer.is_nt(book_code)
        if not is_nt:
            raise ValueError(f"Septantism search is mainly for NT books referencing OT. '{book_code}' is not an NT book.")

        self.ref_db.load_all(source_filter=None, scope='nt')
        payload = []
        for ref_key, data in self.ref_db.in_memory_refs.items():
            if not ref_key.startswith(f"{book_code}."):
                continue
                
            parts = ref_key.split(".")
            if len(parts) != 3: continue
            b, c, v = parts[0], int(parts[1]), int(parts[2])
            
            if filter_chapter > 0 and c != filter_chapter:
                continue
                
            if start_verse > 0 and end_verse > 0:
                if not (start_verse <= v <= end_verse):
                    continue
            elif filter_verse > 0:
                if v != filter_verse:
                    continue
            
            try:
                source_verse = self.bible_provider.get_verse(b, c, v, version="N1904")
                if not source_verse or not source_verse.text: continue
                source_text = source_verse.text
                
                source_fr = None
                if french_version:
                    fr_v = self.bible_provider.get_verse(b, c, v, version=french_version)
                    if fr_v: source_fr = fr_v.text
            except:
                continue
            
            for rel in data.get("relations", []):
                target_ref = rel["target"]
                
                parsed_target = self.bible_provider.normalize_reference(target_ref)
                if not parsed_target: continue
                tb, tc, tv = parsed_target
                
                if self.normalizer.is_nt(tb):
                    continue
                    
                try:
                    target_verse = self.bible_provider.get_verse(tb, tc, tv, version="LXX")
                    if not target_verse or not target_verse.text: continue
                    target_text = target_verse.text
                    
                    target_fr = None
                    if french_version:
                        fr_tgt = self.bible_provider.get_verse(tb, tc, tv, version=french_version)
                        if fr_tgt: target_fr = fr_tgt.text
                except:
                    continue
                    
                pair_id = f"{ref_key} -> {target_ref}"
                payload.append({
                    "id": pair_id,
                    "source_ref": ref_key,
                    "target_ref": target_ref,
                    "source_text": source_text,
                    "target_text": target_text,
                    "source_fr": source_fr,
                    "target_fr": target_fr
                })

        if not payload:
            return []

        # Delegate execution to port
        output = self.nlp_provider.find_septantisms(payload)

        final_results = []
        payload_map = {p["id"]: p for p in payload}
        
        lemma_to_gloss = {}
        if hasattr(self.bible_provider, 'n1904') and self.bible_provider.n1904:
            F = self.bible_provider.n1904.api.F
            target_lemmas = set()
            for item in output:
                if item["score"] > 0:
                    for match in item.get("matches", []):
                        target_lemmas.add(unicodedata.normalize('NFC', match["lemma"]))
                        
            if target_lemmas:
                for w in F.otype.s('word'):
                    db_lemma = F.lemma.v(w)
                    if not db_lemma: continue
                    db_lemma_nfc = unicodedata.normalize('NFC', db_lemma)
                    if db_lemma_nfc in target_lemmas and db_lemma_nfc not in lemma_to_gloss:
                        lemma_to_gloss[db_lemma_nfc] = F.gloss.v(w)
                        if len(lemma_to_gloss) == len(target_lemmas):
                            break
            
        for item in output:
            if item["score"] > 0: 
                orig = payload_map.get(item["id"], {})
                item["source_ref"] = orig.get("source_ref")
                item["target_ref"] = orig.get("target_ref")
                item["source_text"] = orig.get("source_text")
                item["target_text"] = orig.get("target_text")
                item["source_fr"] = orig.get("source_fr")
                item["target_fr"] = orig.get("target_fr")
                
                for match in item.get("matches", []):
                    lemma_nfc = unicodedata.normalize('NFC', match["lemma"])
                    if lemma_nfc in lemma_to_gloss:
                        match["gloss"] = lemma_to_gloss[lemma_nfc]
                                
                final_results.append(item)
                
        final_results.sort(key=lambda x: x["score"], reverse=True)
        return final_results
