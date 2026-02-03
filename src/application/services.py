import os
import contextlib
from typing import List, Optional, Tuple, Any, Dict
from adapters.text_fabric_adapter import TextFabricAdapter
from domain.models import VerseResponse, VerseCrossReferences, CrossReferenceRelation, VerseItem
from book_normalizer import BookNormalizer
from references_db import ReferenceDatabase
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
                 
                 # Import locally to avoid circular dep if any (though models is leaf)
                 # Actually better to import at top.
                 
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
             if not s_filter and french_version and french_version.lower() == 'tob':
                 s_filter = 'tob'
                 
             scope = 'nt' if is_nt else 'ot'
             
             # Load DB
             self.ref_db.load_all(source_filter=s_filter, scope=scope)
             
             key = f"{book_code}.{chapter}.{verse}"
             refs_dict = self.ref_db.in_memory_refs.get(key)
             
             if refs_dict:
                 relations = []
                 for r in refs_dict.get("relations", []):
                     relations.append(CrossReferenceRelation(
                       target_ref=r["target"],
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
                             
                             # Strategy: For range, we want [Verse 3 Text] [Verse 4 Text] joined?
                             # Or [Version 1 Text for 3-4] [Version 2 Text for 3-4]?
                             # Legacy: "Text v3... Text v4..." usually?
                             # Actually legacy usually fetched just one verse for cross ref?
                             # Wait, user said "Mc 7:3-4 cross reference is mentioned but its text is not cited".
                             # Means it was missing entirely.
                             # If I fetch multiple verses, I should probably join them with space?
                             
                             # Let's fetch all text for the range in the PRIMARY preferred version?
                             # Or ALL versions?
                             # Legacy behavior for cross refs: usually just one version (the main one or defaults).
                             # "versions_to_try" list suggests multiple versions.
                             # If multiple versions AND multiple verses:
                             # Output: (Version1 v3 v4) \n (Version2 v3 v4) ?
                             # Simplify: Concatenate verses for each version, then join versions.
                             
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
