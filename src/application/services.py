import os
import contextlib
from typing import List, Optional, Tuple, Any, Dict
from src.adapters.text_fabric_adapter import TextFabricAdapter
from src.domain.models import VerseResponse, VerseCrossReferences, CrossReferenceRelation, VerseItem, FindResponse, FindResultItem
import sys
import json
import subprocess
import re
from src.book_normalizer import BookNormalizer
from src.references_db import ReferenceDatabase
from tf.app import use

# Helper/Factory for Adapter (moved from CLI, but we might want a better place)
class AdapterFactory:
    _adapter = None
    
    @classmethod
    def get(cls) -> TextFabricAdapter:
        if cls._adapter:
            return cls._adapter
            
        # Data dir logic (assuming structure)
        # We are in src/application/services.py -> src/application -> src -> root
        # Ideally we pass this config in, but for now we follow CLI pattern
        # src/application/services.py is 2 levels deep from src? No, 1 level deep from src.
        # src/application -> src
        
        # Let's use a robust way to find data relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(current_dir) # src
        project_root = os.path.dirname(src_dir) # root
        data_dir = os.path.join(project_root, "data")
        
        # Define providers
        def n1904_p():
             with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                 try: return use("CenterBLC/N1904", version="1.0.0", silent=True)
                 except: return None
        
        def lxx_p():
             with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                 try: return use("CenterBLC/LXX", version="1935", check=False, silent=True)
                 except: return None

        adapter = TextFabricAdapter(
            data_dir=data_dir,
            n1904_provider=n1904_p,
            lxx_provider=lxx_p,
        )
        cls._adapter = adapter
        return adapter

class BibleService:
    def __init__(self, adapter: Optional[TextFabricAdapter] = None):
        self.adapter = adapter or AdapterFactory.get()
        self.normalizer = self.adapter.normalizer
        # Initialize DB on demand or here? 
        # RefDB needs data_dir.
        self.data_dir = self.adapter.data_dir
        self.ref_db = ReferenceDatabase(self.data_dir, self.normalizer)

    def _localize_ref(self, target_str: str) -> str:
        if not target_str: return ""
        
        def parse_one(ref):
            parts = ref.split(".")
            if len(parts) >= 3:
                bk, ch, vs = parts[0], parts[1], parts[2]
                n1904 = self.normalizer.code_to_n1904.get(bk, bk)
                tob_name = self.normalizer.n1904_to_tob.get(n1904, bk)
                return tob_name, ch, vs
            return None, None, None

        if "-" in target_str:
            parts_range = target_str.split("-")
            if len(parts_range) == 2:
                start_parsed = parse_one(parts_range[0])
                end_parsed = parse_one(parts_range[1])
                
                if start_parsed[0] and end_parsed[0]:
                    sb, sc, sv = start_parsed
                    eb, ec, ev = end_parsed
                    if sb == eb:
                        if sc == ec: return f"{sb} {sc}:{sv}-{ev}"
                        else: return f"{sb} {sc}:{sv}-{ec}:{ev}"
                    else: return f"{sb} {sc}:{sv}-{eb} {ec}:{ev}"
        
        abbr, ch, vs = parse_one(target_str)
        if abbr:
             return f"{abbr} {ch}:{vs}"
        
        # Fallback for space separated logic if needed, or return original
        if " " in target_str:
             parts = target_str.split(" ", 1)
             code = parts[0]
             rest = parts[1]
             n1904 = self.normalizer.code_to_n1904.get(code, code)
             tob = self.normalizer.n1904_to_tob.get(n1904)
             if tob: return f"{tob} {rest}"
             
        return target_str

    def search(
        self, 
        reference: str, 
        translations: Optional[List[str]] = None,
        version: str = "N1904",
        french_version: Optional[str] = None,
        show_crossrefs: bool = False,
        crossref_full: bool = False,
        crossref_source: Optional[str] = None
    ) -> VerseResponse:
        
        
        # 0. Parse Reference (Handle Range vs Single)

        target_verses = []
        book_code = None
        chapter = None
        verse = None
        
        parsed_range = False
        if "-" in reference:
            parts = reference.split("-")
            if len(parts) == 2:
                start_s = parts[0].strip()
                end_s = parts[1].strip()
                
                # Normalize start
                norm_start = self.adapter.normalize_reference(start_s)
                if norm_start:
                    b_s, c_s, v_s = norm_start
                    # Ensure start is a specific verse, not chapter
                    if v_s != 0:
                        # Normalize end
                        # Case A: digit only "8-9"
                        if end_s.isdigit():
                             v_e = int(end_s)
                             # Assuming same chapter
                             if v_e >= v_s:
                                 for v in range(v_s, v_e + 1):
                                     target_verses.append((b_s, c_s, v))
                                 parsed_range = True
                                 book_code, chapter, verse = b_s, c_s, v_s # Set context to start
                        else:
                             # Case B: detailed end? "7:9"?
                             pass
                    else:
                        # Whole chapter start "Gn 1" -> End must be "2" or "1:5" (but usually "Gn 1-2" means Ch 1 to Ch 2)
                        if end_s.isdigit():
                             c_e = int(end_s)
                             # Iterate Chapters
                             if c_e >= c_s:
                                 for c in range(c_s, c_e + 1):
                                     # Fetch verses for this chapter (Need Primary Version! But we don't know it yet)
                                     # We need to defer fetching, OR fetching just list of verses 
                                     # We can't fetch text here easily because we haven't selected version.
                                     # But we can assume standard versification or use normalizer/adapter helper to get verse count?
                                     # Adapter has `get_chapter` which returns objects.
                                     # Using 'N1904' or 'LXX' or 'BHSA' as temp to find available verses.
                                     # We'll use a safe default to discover verses.
                                     
                                     temp_v = 'N1904' if self.normalizer.is_nt(b_s) else 'BHSA'
                                     # Fallback if BHSA not avail? Use adapter defaults? 
                                     # Actually `get_chapter` takes version.
                                     
                                     objs = self.adapter.get_chapter(b_s, c, temp_v)
                                     if not objs and not self.normalizer.is_nt(b_s):
                                         objs = self.adapter.get_chapter(b_s, c, 'LXX') # Fallback
                                         
                                     if objs:
                                         for v_obj in objs:
                                             target_verses.append((b_s, c, v_obj.verse))
                                             
                                 parsed_range = True
                                 book_code, chapter, verse = b_s, c_s, 0

        if not parsed_range:
             norm_ref = self.adapter.normalize_reference(reference)
             if not norm_ref:
                 raise ValueError(f"Invalid reference '{reference}'")
     
             book_code, chapter, verse = norm_ref
             
             if verse == 0:
                  # Whole chapter
                  objs = self.adapter.get_chapter(book_code, chapter, version) # Use temp version to get list?
                  # Actually primary_v is determined later.
                  # We need to defer fetching until primary_v is known.
                  # But we need book_code for primary_v logic.
                  # So we just store intent.
                  pass
             else:
                  target_verses.append((book_code, chapter, verse))
                  
        
        # 1. Determine Primary Version
        is_nt = self.normalizer.is_nt(book_code)
        primary_v = version
        
        current_translations = translations or []
        
        # Determine best primary version based on requested translations
        candidates = []
        for t in current_translations:
            t = t.lower()
            if t == 'hb': candidates.append('BHSA')
            elif t == 'gr': candidates.append('N1904' if is_nt else 'LXX')
            elif t == 'en': candidates.append('N1904_EN')
            elif t == 'fr': candidates.append((french_version or 'tob').upper())
            elif t == 'ar': candidates.append('NAV')
            elif t in ['tob', 'bj', 'nav', 'lxx', 'bhsa', 'n1904']: candidates.append(t.upper())
            
        best = None
        if not is_nt and 'BHSA' in candidates: best = 'BHSA'
        elif (is_nt and 'N1904' in candidates) or (not is_nt and 'LXX' in candidates): 
             best = 'N1904' if is_nt else 'LXX'
        elif is_nt and 'N1904_EN' in candidates: 
             best = 'N1904_EN'
        elif 'N1904' in candidates: best = 'N1904'
        
        if not best:
             for c in candidates:
                 if c in ['TOB', 'BJ']: 
                     best = c
                     break
        if not best and 'NAV' in candidates: best = 'NAV'
             
        if best:
             primary_v = best
        else:
             if version == "N1904" and not is_nt:
                 primary_v = "LXX"

        # 2. Fetch Verses
        verses_data = []
        
        # If whole chapter (verse=0 and not parsed_range), populate target_verses now
        if not target_verses and verse == 0:
             objs = self.adapter.get_chapter(book_code, chapter, primary_v)
             for v_obj in objs:
                 target_verses.append((book_code, chapter, v_obj.verse))
             
        # Fetch Loop
        for b, c, v in target_verses:
            try:
                 main_v = self.adapter.get_verse(b, c, v, version=primary_v)
                 if not main_v: continue
                 
                 item_primary = main_v
                 item_parallels = []
                 
                 # Fetch Parallels
                 # Logic for defaults if no translations requested
                 vers_to_fetch = []
                 if current_translations:
                     for t in current_translations:
                         t = t.lower()
                         v_code = None
                         if t == 'en': v_code = 'N1904_EN'
                         elif t == 'fr': v_code = (french_version or "tob").upper()
                         elif t == 'gr': v_code = 'N1904' if is_nt else 'LXX'
                         elif t == 'hb': v_code = 'BHSA'
                         elif t == 'ar': v_code = 'NAV'
                         elif t in ['tob', 'bj', 'nav', 'lxx', 'bhsa', 'n1904']: v_code = t.upper()
                         
                         if v_code and v_code != primary_v:
                             vers_to_fetch.append(v_code)
                 else:
                     # Defaults
                     greek = 'N1904' if is_nt else 'LXX'
                     if primary_v != greek: vers_to_fetch.append(greek)
                     if not is_nt and primary_v != 'BHSA': vers_to_fetch.append('BHSA')
                     fr = (french_version or "tob").upper()
                     if primary_v != fr: vers_to_fetch.append(fr)
                 
                 # Deduplicate
                 vers_to_fetch = list(set(vers_to_fetch))
                 
                 for v_code in vers_to_fetch:
                     try:
                         p_v = self.adapter.get_verse(b, c, v, version=v_code)
                         if p_v:
                             item_parallels.append(p_v)
                     except:
                         pass
                 
                 # Determine localized book name (Logic ported from CLI)
                 header_name = None
                 is_french = False
                 if current_translations:
                     if 'fr' in [t.lower() for t in current_translations]: is_french = True
                 else:
                     is_french = True # Default
                 
                 code = item_primary.book_code
                 if is_french:
                     n1904_name = self.normalizer.code_to_n1904.get(code, code)
                     tob_name = self.normalizer.n1904_to_tob.get(n1904_name)
                     if tob_name: header_name = tob_name
                 
                 if not header_name:
                     # English fallback if requested or default
                     is_english = False
                     if current_translations and 'en' in [t.lower() for t in current_translations]: is_english = True
                     if item_primary.version == "N1904_EN": is_english = True
                     
                     if is_english:
                         en_name = self.normalizer.code_to_n1904.get(code, code)
                         if en_name: header_name = en_name.replace("_", " ")

                 # Attach name to primary
                 # We need to recreate the Verse object since it's frozen
                 item_primary = item_primary.model_copy(update={"book_name": header_name})
                 
                 verses_data.append(VerseItem(
                     ref=f"{b} {c}:{v}",
                     primary=item_primary,
                     parallels=item_parallels
                 ))
            except Exception:
                pass
        # 3. Cross Refs (Only for single verse usually, or aggregate?)
        # CLI logic seemed to imply cross refs for the requested reference.
        # If chapter, loading cross refs for whole chapter might be heavy/noisy?
        # CLI: if verse==0, it didn't seem to verify cross refs explicitly in the main loop?
        # CLI lines 467: "Retrieve refs for this specific verse" implies single verse context usually.
        # But if range or chapter, key logic might fail.
        # Let's support it for the FIRST verse or the specific verse if single, 
        # OR just leave it empty if chapter.
        
        c_refs_model = None
        if (show_crossrefs or crossref_full) and verse != 0:
             s_filter = crossref_source
             
             # Logic removed: We should NOT auto-filter to 'tob' just because french_version is 'tob'
             # unless explicitly requested. This restores visibility of generic cross-refs.
                 
             scope = 'nt' if is_nt else 'ot'
             
             # Load DB
             self.ref_db.load_all(source_filter=s_filter, scope=scope)
             
             key = f"{book_code}.{chapter}.{verse}"
             refs_dict = self.ref_db.in_memory_refs.get(key)
             
             if refs_dict:
                 relations = []
                 for r in refs_dict.get("relations", []):
                     t_ref = r["target"]
                     t_ref_loc = self._localize_ref(t_ref)

                     relations.append(CrossReferenceRelation(
                       target_ref=t_ref,
                       target_ref_localized=t_ref_loc,
                       rel_type=r["type"],
                       note=r.get("note")
                     ))
                 
                 c_refs_model = VerseCrossReferences(
                     notes=refs_dict.get("notes", []),
                     relations=relations
                 )
                 
                 # Sorting (ported)
                 def sort_key(rel):
                     parsed = self.adapter.normalize_reference(rel.target_ref)
                     if parsed:
                         bk, ch, vs = parsed
                         order = self.normalizer.book_order.get(bk, 999)
                         return (0, order, ch, vs)
                     return (1, rel.target_ref)
                 
                 c_refs_model.relations.sort(key=sort_key)
                 
                 
                 c_refs_model.relations.sort(key=sort_key)
                 
                 # Full text fetch if requested
                 if crossref_full:
                     new_relations = []
                     for rel in c_refs_model.relations:
                         text_content = None
                         target = rel.target_ref
                         
                         # Determine versions to try
                         # Use current translations to pick preferred language for cross-ref?
                         # Or default to N1904/LXX/BHSA/TOB order (similar to legacy)
                         
                         
                         parsed = None
                         verses_to_fetch_list = []
                         # print(f"DEBUG: Initial normalize '{target}' -> {parsed}") # Disabled log
                         
                         if "-" in target:
                             # Range Handling
                             parts = target.split("-")
                             if len(parts) == 2:
                                 start_ref = parts[0].strip()
                                 end_part = parts[1].strip()
                                 
                                 parsed_start = self.adapter.normalize_reference(start_ref)
                                 if parsed_start:
                                     b_s, c_s, v_s = parsed_start 
                                     
                                     # Determine end verse
                                     # Try normalizing end part as full ref
                                     # But end part usually just "4" or "8:1"
                                     # We need to construct a candidate string using start's book
                                     
                                     # Case 1: "4" (Verse only)
                                     if end_part.isdigit():
                                         v_e = int(end_part)
                                         c_e = c_s
                                         b_e = b_s
                                     elif ":" in end_part:
                                         # Case 2: "8:1" (Chapter:Verse)
                                         # Construct "Book 8:1"
                                         # Need book key to reconstruct?
                                         # We have book code b_s.
                                         # Try normalizing "CODE 8:1"
                                         candidate_end = f"{b_s} {end_part}"
                                         parsed_end = self.adapter.normalize_reference(candidate_end)
                                         if parsed_end:
                                             b_e, c_e, v_e = parsed_end
                                         else:
                                             b_e, c_e, v_e = None, None, None
                                     else:
                                         # Case 3: Full Ref "Mc 8:1"? Usually not after hyphen if shared book.
                                         parsed_end = self.adapter.normalize_reference(end_part)
                                         if parsed_end:
                                             b_e, c_e, v_e = parsed_end
                                         else:
                                             b_e, c_e, v_e = None, None, None
                                     
                                     if b_e and b_s == b_e:
                                         # Iterate
                                         # Simple iteration if same chapter
                                         if c_s == c_e:
                                             for v in range(v_s, v_e + 1):
                                                 verses_to_fetch_list.append((b_s, c_s, v))
                                         else:
                                             # Multi-chapter range? Too complex for now?
                                             # Legacy CLI logic for fetch in 'get_text_for_range'?
                                             # Let's support simple same-chapter ranges first which is most common "7:3-4"
                                             pass

                         else:
                             # Single verse fallback
                             parsed = self.adapter.normalize_reference(target)
                             if parsed:
                                 verses_to_fetch_list.append(parsed)

                         if verses_to_fetch_list:
                             tb_first = verses_to_fetch_list[0][0]
                             is_target_nt = self.normalizer.is_nt(tb_first)
                             
                             # Determine versions (Priority: Requested > Original > French)
                             versions_to_try = []
                             if current_translations:
                                 for t in current_translations:
                                     t = t.lower()
                                     v_c = None
                                     if t == 'en': v_c = 'N1904_EN'
                                     elif t == 'fr': v_c = (french_version or "tob").upper()
                                     elif t == 'gr': v_c = 'N1904' if is_target_nt else 'LXX'
                                     elif t == 'hb': v_c = 'BHSA'
                                     elif t == 'ar': v_c = 'NAV'
                                     elif t in ['tob', 'bj', 'nav', 'lxx', 'bhsa', 'n1904']: v_c = t.upper()
                                     
                                     if v_c:
                                          if v_c == 'BHSA' and is_target_nt: continue
                                          if v_c == 'N1904' and not is_target_nt: v_c = 'LXX'
                                          if v_c == 'LXX' and is_target_nt: v_c = 'N1904'
                                          if v_c not in versions_to_try: versions_to_try.append(v_c)
                             else:
                                 versions_to_try.append('N1904' if is_target_nt else 'LXX')
                                 if not is_target_nt: versions_to_try.append('BHSA')
                                 versions_to_try.append((french_version or "tob").upper())

                             texts_acc = []
                             
                             for v_code in versions_to_try:
                                 v_texts = []
                                 for (b, c, v) in verses_to_fetch_list:
                                     try:
                                         v_obj = self.adapter.get_verse(b, c, v, version=v_code)
                                         if v_obj and v_obj.text:
                                             v_texts.append(v_obj.text)
                                     except: pass
                                 if v_texts:
                                     texts_acc.append(" ".join(v_texts))
                             
                             if texts_acc:
                                  text_content = "\n".join(texts_acc)

                         # Update relation with text
                         new_relations.append(CrossReferenceRelation(
                             target_ref=rel.target_ref,
                             target_ref_localized=rel.target_ref_localized, # Must preserve this!
                             rel_type=rel.rel_type,
                             note=rel.note,
                             text=text_content
                         ))
                     
                     c_refs_model.relations = new_relations

        return VerseResponse(
            reference=reference,
            verses=verses_data,
            cross_references=c_refs_model
        )

    def find(
        self,
        query: str,
        limit: int = 20,
        bible: Optional[str] = None,
        version: Optional[str] = None,
        translations: Optional[List[str]] = None
    ) -> FindResponse:
        
        # Helper: Detect Greek Script
        def is_greek_script(text: str) -> bool:
            for char in text:
                # Greek and Coptic (0370-03FF), Greek Extended (1F00-1FFF)
                if '\u0370' <= char <= '\u03ff' or '\u1f00' <= char <= '\u1fff':
                    return True
            return False

        is_greek = is_greek_script(query)
        
        # Determine Search Mode
        mode = "greek"
        search_corpus = "nt" # default Greek corpus
        french_version = "tob" # default French version
        
        if bible:
            french_version = bible.lower()
            if french_version not in ["tob", "bj"]:
                 raise ValueError(f"Invalid french version: {bible}. Use 'tob' or 'bj'.")

        if is_greek:
            # Greek Search Mode
            mode = "greek"
            if version:
                if version.lower() not in ["nt", "lxx", "all", "at"]:
                     raise ValueError(f"Invalid greek version: {version}. Use 'nt', 'lxx', 'all'.")
                search_corpus = version.lower()
                if search_corpus == "at": search_corpus = "lxx"
            
            # -b is allowed here, affects translation version only
            
        else:
            # Latin Script
            if bible:
                # Explicit French Search
                mode = "french"
                search_corpus = french_version # 'tob' or 'bj'
            elif version:
                # Explicit Greek Search (Transliteration)
                mode = "greek"
                search_corpus = version.lower()
                if search_corpus == "at": search_corpus = "lxx"
            else:
                # Ambiguous Latin - Default to French with error/hint?
                # CLI raises Exit. Service should raise ValueError.
                # However, typically API might try best effort or return 400.
                raise ValueError(f"Ambiguous search for latin query '{query}'. Specify french_version (tob/bj) or greek version (nt/lxx).")

        # Dispatch via Subprocess
        # We need to locate workers relative to this file
        # src/application/services.py -> src/application/workers/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        workers_dir = os.path.join(current_dir, "workers")
        project_root = os.path.dirname(os.path.dirname(current_dir)) # src/application -> src -> root
        
        if mode == "french":
            worker_script = os.path.join(workers_dir, "french_worker.py")
            cmd = [sys.executable, worker_script, query, "--bible", search_corpus, "--limit", str(limit)]
            
        else: # Greek
            worker_script = os.path.join(workers_dir, "find_worker.py")
            
            # Try to use spacy venv if exists
            venv_python = os.path.join(project_root, ".venv-spacy", "bin", "python3")
            if not os.path.exists(venv_python):
                 venv_python = sys.executable
                 
            cmd = [venv_python, worker_script, query, "--limit", str(limit), "--corpus", search_corpus]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except Exception as e:
            raise RuntimeError(f"Error running worker: {e}")
            
        if result.returncode != 0:
            raise RuntimeError(f"Worker failed: {result.stderr}")
            
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"Invalid output from worker: {result.stdout}")

        # Process Results
        lemma = output.get("lemma", query)
        count = output.get("total", 0)
        lemma_gloss = output.get("lemma_gloss", "")
        raw_results = output.get("results", [])
        
        final_results = []
        
        # Helper for highlighting
        def apply_highlights(text: str, highlights: List[str]) -> str:
            if not text or not highlights: return list(highlights) # Service returns list of words? 
            # Wait, API should return text and list of highlight words.
            # Client does drawing.
            # BUT: CLI does highlighting in text.
            # API Spec said: highlights: List[str]
            # So we return the LIST of words to highlight.
            # We DONT modify the text with ANSI codes here.
            # CLI modified text. API keeps data clean.
            return list(highlights)

        for item in raw_results:
            # item: {ref, book_code, chapter, verse, greek, french, highlights}
            # We need to construct FindResultItem
            
            # Fetch Translations if requested
            # Re-use logic from search?
            # Or just fetch specific verses.
            
            b = item.get("book_code")
            c = item.get("chapter")
            v = item.get("verse")
            
            # Main Text
            # For Greek mode: greek
            # For French mode: french
            main_text = item.get("greek") or item.get("french") or ""
            
            # Gather Translations
            translations_map = {}
            if translations:
                # Determine versions to fetch
                # Logic from search...
                
                # We need is_nt for defaults
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
                         # Fetch
                         try:
                             p_v = self.adapter.get_verse(b, c, v, version=v_code)
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

    def find_septantisms(self, book_abbr: str, french_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Scan a book's cross-references to the OT to find 'Septantisms'
        by comparing the NT Greek text to the LXX Greek text of the OT reference.
        Allows filtering by chapter or verse (e.g., 'Mc 1', 'Mc 1.1').
        If french_version is provided, fetches the French text for both source and target.
        """
        # 1. Normalize book abbreviation / reference
        
        # Check for range pattern e.g. "Mc 1:1-3" or "Mc 1.1-3"
        import re
        range_match = re.search(r'(?:[.:]\s*)(\d+)(?:\s*-\s*(\d+))', book_abbr)
        start_verse = 0
        end_verse = 0
        if range_match:
            start_verse = int(range_match.group(1))
            end_verse = int(range_match.group(2))
            
        parsed = self.adapter.normalize_reference(book_abbr)
        
        if parsed:
            book_code, filter_chapter, filter_verse = parsed
            if start_verse and end_verse:
                filter_verse = 0 # Override single verse exact match
        else:
            # Fallback for book only (e.g., "Mc")
            parsed = self.adapter.normalize_reference(f"{book_abbr} 1:1")
            if not parsed:
                raise ValueError(f"Unknown book abbreviation or reference: {book_abbr}")
            book_code, filter_chapter, filter_verse = parsed[0], 0, 0
            
        is_nt = self.normalizer.is_nt(book_code)
        if not is_nt:
            raise ValueError(f"Septantism search is mainly for NT books referencing OT. '{book_code}' is not an NT book.")

        # 2. Load DB notes for this book
        self.ref_db.load_all(source_filter=None, scope='nt')
        
        # 3. Gather text pairs
        payload = []
        # ref_db.in_memory_refs is a dict: "MRK.1.2": {"notes": [...], "relations": [...]}
        for ref_key, data in self.ref_db.in_memory_refs.items():
            if not ref_key.startswith(f"{book_code}."):
                continue
                
            parts = ref_key.split(".")
            if len(parts) != 3: continue
            b, c, v = parts[0], int(parts[1]), int(parts[2])
            
            # Apply chapter filter
            if filter_chapter > 0 and c != filter_chapter:
                continue
                
            # Apply verse filter
            if start_verse > 0 and end_verse > 0:
                if not (start_verse <= v <= end_verse):
                    continue
            elif filter_verse > 0:
                if v != filter_verse:
                    continue
            
            # Get source text (NT)
            try:
                source_verse = self.adapter.get_verse(b, c, v, version="N1904")
                if not source_verse or not source_verse.text: continue
                source_text = source_verse.text
                
                source_fr = None
                if french_version:
                    fr_v = self.adapter.get_verse(b, c, v, version=french_version)
                    if fr_v: source_fr = fr_v.text
            except:
                continue
            
            for rel in data.get("relations", []):
                target_ref = rel["target"]
                
                # Check if target is OT
                parsed_target = self.adapter.normalize_reference(target_ref)
                if not parsed_target: continue
                tb, tc, tv = parsed_target
                
                if self.normalizer.is_nt(tb):
                    continue # only OT references
                    
                # Get target text (LXX)
                try:
                    target_verse = self.adapter.get_verse(tb, tc, tv, version="LXX")
                    if not target_verse or not target_verse.text: continue
                    target_text = target_verse.text
                    
                    target_fr = None
                    if french_version:
                        fr_tgt = self.adapter.get_verse(tb, tc, tv, version=french_version)
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

        # 4. Call Worker
        current_dir = os.path.dirname(os.path.abspath(__file__))
        workers_dir = os.path.join(current_dir, "workers")
        project_root = os.path.dirname(os.path.dirname(current_dir))
        worker_script = os.path.join(workers_dir, "septantism_worker.py")
        
        venv_python = os.path.join(project_root, ".venv-spacy", "bin", "python3")
        if not os.path.exists(venv_python):
             venv_python = sys.executable
             
        cmd = [venv_python, worker_script]

        try:
            # We pass JSON string to stdin
            input_json = json.dumps(payload)
            result = subprocess.run(cmd, input=input_json, text=True, capture_output=True)
        except Exception as e:
            raise RuntimeError(f"Error running septantism worker: {e}")
            
        if result.returncode != 0:
            raise RuntimeError(f"Worker failed: {result.stderr}")
            
        try:
            output = json.loads(result.stdout)
            if isinstance(output, dict) and "error" in output:
                raise RuntimeError(output["error"])
        except json.JSONDecodeError:
            raise RuntimeError(f"Invalid output from worker: {result.stdout}")

        # Enhance output with texts for display
        final_results = []
        payload_map = {p["id"]: p for p in payload}
        
        # Fast lookup for Greek Lemmas in N1904 to get English gloss
        lemma_to_gloss = {}
        if self.adapter.n1904:
            import unicodedata
            F = self.adapter.n1904.api.F
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
            if item["score"] > 0: # Only return hits
                # re-attach source/target details
                orig = payload_map.get(item["id"], {})
                item["source_ref"] = orig.get("source_ref")
                item["target_ref"] = orig.get("target_ref")
                item["source_text"] = orig.get("source_text")
                item["target_text"] = orig.get("target_text")
                item["source_fr"] = orig.get("source_fr")
                item["target_fr"] = orig.get("target_fr")
                
                # Fetch Glosses for matches
                for match in item.get("matches", []):
                    lemma_nfc = unicodedata.normalize('NFC', match["lemma"])
                    if lemma_nfc in lemma_to_gloss:
                        match["gloss"] = lemma_to_gloss[lemma_nfc]
                                
                final_results.append(item)
                
        # Sort by score desc, or source ref
        final_results.sort(key=lambda x: x["score"], reverse=True)
        return final_results

    def greek_analysis(self, text: str) -> List[Dict[str, Any]]:
        """
        Perform deep NLP analysis on Greek text using OdyCy.
        """
        # Dispatch via Subprocess
        current_dir = os.path.dirname(os.path.abspath(__file__))
        workers_dir = os.path.join(current_dir, "workers")
        project_root = os.path.dirname(os.path.dirname(current_dir)) 
        
        worker_script = os.path.join(workers_dir, "greek_worker.py")
        
        # Try to use spacy venv if exists
        venv_python = os.path.join(project_root, ".venv-spacy", "bin", "python3")
        if not os.path.exists(venv_python):
             venv_python = sys.executable
             
        cmd = [venv_python, worker_script, text]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except Exception as e:
            raise RuntimeError(f"Error running worker: {e}")
            
        if result.returncode != 0:
            raise RuntimeError(f"Worker failed: {result.stderr}")
            
        try:
            output = json.loads(result.stdout)
            if isinstance(output, dict) and "error" in output:
                raise RuntimeError(output["error"])
            return output
        except json.JSONDecodeError:
            raise RuntimeError(f"Invalid output from worker: {result.stdout}")
