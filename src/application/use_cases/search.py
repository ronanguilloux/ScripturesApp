from typing import List, Optional
from src.domain.models import VerseResponse, VerseItem, VerseCrossReferences, CrossReferenceRelation, CrossReferenceType
from src.ports.bible_provider import BibleProvider
from src.references_db import ReferenceDatabase
from src.book_normalizer import BookNormalizer

class SearchBibleUseCase:
    def __init__(self, bible_provider: BibleProvider, ref_db: ReferenceDatabase, normalizer: BookNormalizer):
        self.bible_provider = bible_provider
        self.ref_db = ref_db
        self.normalizer = normalizer

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
        
        if " " in target_str:
             parts = target_str.split(" ", 1)
             code = parts[0]
             rest = parts[1]
             n1904 = self.normalizer.code_to_n1904.get(code, code)
             tob = self.normalizer.n1904_to_tob.get(n1904)
             if tob: return f"{tob} {rest}"
             
        return target_str

    def execute(
        self, 
        reference: str, 
        translations: Optional[List[str]] = None,
        version: str = "N1904",
        french_version: Optional[str] = None,
        show_crossrefs: bool = False,
        crossref_full: bool = False,
        crossref_source: Optional[str] = None
    ) -> VerseResponse:
        
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
                
                norm_start = self.bible_provider.normalize_reference(start_s)
                if norm_start:
                    b_s, c_s, v_s = norm_start
                    if v_s != 0:
                        if end_s.isdigit():
                             v_e = int(end_s)
                             if v_e >= v_s:
                                 for v in range(v_s, v_e + 1):
                                     target_verses.append((b_s, c_s, v))
                                 parsed_range = True
                                 book_code, chapter, verse = b_s, c_s, v_s
                    else:
                        if end_s.isdigit():
                             c_e = int(end_s)
                             if c_e >= c_s:
                                 for c in range(c_s, c_e + 1):
                                     temp_v = 'N1904' if self.normalizer.is_nt(b_s) else 'BHSA'
                                     objs = self.bible_provider.get_chapter(b_s, c, temp_v)
                                     if not objs and not self.normalizer.is_nt(b_s):
                                         objs = self.bible_provider.get_chapter(b_s, c, 'LXX')
                                         
                                     if objs:
                                         for v_obj in objs:
                                             target_verses.append((b_s, c, v_obj.verse))
                                             
                                 parsed_range = True
                                 book_code, chapter, verse = b_s, c_s, 0

        if not parsed_range:
             norm_ref = self.bible_provider.normalize_reference(reference)
             if not norm_ref:
                 raise ValueError(f"Invalid reference '{reference}'")
     
             book_code, chapter, verse = norm_ref
             
             if verse != 0:
                  target_verses.append((book_code, chapter, verse))
        
        is_nt = self.normalizer.is_nt(book_code)
        primary_v = version
        current_translations = translations or []
        
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

        verses_data = []
        
        if not target_verses and verse == 0:
             objs = self.bible_provider.get_chapter(book_code, chapter, primary_v)
             for v_obj in objs:
                 target_verses.append((book_code, chapter, v_obj.verse))
             
        for b, c, v in target_verses:
            try:
                 main_v = self.bible_provider.get_verse(b, c, v, version=primary_v)
                 if not main_v: continue
                 
                 item_primary = main_v
                 item_parallels = []
                 
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
                     greek = 'N1904' if is_nt else 'LXX'
                     if primary_v != greek: vers_to_fetch.append(greek)
                     if not is_nt and primary_v != 'BHSA': vers_to_fetch.append('BHSA')
                     fr = (french_version or "tob").upper()
                     if primary_v != fr: vers_to_fetch.append(fr)
                 
                 vers_to_fetch = list(set(vers_to_fetch))
                 
                 for v_code in vers_to_fetch:
                     try:
                         p_v = self.bible_provider.get_verse(b, c, v, version=v_code)
                         if p_v:
                             item_parallels.append(p_v)
                     except:
                         pass
                 
                 header_name = None
                 is_french = False
                 if current_translations:
                     if 'fr' in [t.lower() for t in current_translations]: is_french = True
                 else:
                     is_french = True
                 
                 code = item_primary.book_code
                 if is_french:
                     n1904_name = self.normalizer.code_to_n1904.get(code, code)
                     tob_name = self.normalizer.n1904_to_tob.get(n1904_name)
                     if tob_name: header_name = tob_name
                 
                 if not header_name:
                     is_english = False
                     if current_translations and 'en' in [t.lower() for t in current_translations]: is_english = True
                     if item_primary.version == "N1904_EN": is_english = True
                     
                     if is_english:
                         en_name = self.normalizer.code_to_n1904.get(code, code)
                         if en_name: header_name = en_name.replace("_", " ")

                 import dataclasses
                 item_primary = dataclasses.replace(item_primary, book_name=header_name)
                 
                 verses_data.append(VerseItem(
                     ref=f"{b} {c}:{v}",
                     primary=item_primary,
                     parallels=item_parallels
                 ))
            except Exception:
                pass
        
        c_refs_model = None
        if (show_crossrefs or crossref_full) and verse != 0:
             s_filter = crossref_source
             scope = 'nt' if is_nt else 'ot'
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
                       rel_type=CrossReferenceType(r.get("type", "parallel")),
                       note=r.get("note")
                     ))
                 
                 c_refs_model = VerseCrossReferences(
                     notes=refs_dict.get("notes", []),
                     relations=relations
                 )
                 
                 def sort_key(rel):
                     parsed = self.bible_provider.normalize_reference(rel.target_ref)
                     if parsed:
                         bk, ch, vs = parsed
                         order = self.normalizer.book_order.get(bk, 999)
                         return (0, order, ch, vs)
                     return (1, rel.target_ref)
                 
                 c_refs_model.relations.sort(key=sort_key)
                 
                 if crossref_full:
                     new_relations = []
                     for rel in c_refs_model.relations:
                         text_content = None
                         target = rel.target_ref
                         
                         parsed = None
                         verses_to_fetch_list = []
                         
                         if "-" in target:
                             parts = target.split("-")
                             if len(parts) == 2:
                                 start_ref = parts[0].strip()
                                 end_part = parts[1].strip()
                                 
                                 parsed_start = self.bible_provider.normalize_reference(start_ref)
                                 if parsed_start:
                                     b_s, c_s, v_s = parsed_start 
                                     
                                     if end_part.isdigit():
                                         v_e = int(end_part)
                                         c_e = c_s
                                         b_e = b_s
                                     elif ":" in end_part:
                                         candidate_end = f"{b_s} {end_part}"
                                         parsed_end = self.bible_provider.normalize_reference(candidate_end)
                                         if parsed_end:
                                             b_e, c_e, v_e = parsed_end
                                         else:
                                             b_e, c_e, v_e = None, None, None
                                     else:
                                         parsed_end = self.bible_provider.normalize_reference(end_part)
                                         if parsed_end:
                                             b_e, c_e, v_e = parsed_end
                                         else:
                                             b_e, c_e, v_e = None, None, None
                                     
                                     if b_e and b_s == b_e:
                                         if c_s == c_e:
                                             for v in range(v_s, v_e + 1):
                                                 verses_to_fetch_list.append((b_s, c_s, v))
                         else:
                             parsed = self.bible_provider.normalize_reference(target)
                             if parsed:
                                 verses_to_fetch_list.append(parsed)

                         if verses_to_fetch_list:
                             tb_first = verses_to_fetch_list[0][0]
                             is_target_nt = self.normalizer.is_nt(tb_first)
                             
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
                                         v_obj = self.bible_provider.get_verse(b, c, v, version=v_code)
                                         if v_obj and v_obj.text:
                                             v_texts.append(v_obj.text)
                                     except: pass
                                 if v_texts:
                                     texts_acc.append(" ".join(v_texts))
                             
                             if texts_acc:
                                  text_content = "\n".join(texts_acc)

                         new_relations.append(CrossReferenceRelation(
                             target_ref=rel.target_ref,
                             target_ref_localized=rel.target_ref_localized,
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
