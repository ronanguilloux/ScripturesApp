import dataclasses
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

    def _book_label(self, book_code: str) -> str:
        """The French abbreviation _localize_ref puts at the head of a reference."""
        n1904 = self.normalizer.code_to_n1904.get(book_code, book_code)
        return self.normalizer.n1904_to_tob.get(n1904, book_code)

    def _margin_labels(self, relations, current_book):
        """Apply the BJ margin convention to one verse's stack of references.

        A reference drops its book name when it repeats the book being read
        ('2:33' for Ac 2,33 while reading Acts) or the book of the reference just
        above it in the same stack ('Rm 7:5' then '11:27'). A '+' marker, meaning
        the reference carries an explanatory note, is kept.
        """
        out = []
        previous_book = None
        for rel in relations:
            label = rel.target_ref_localized or rel.target_ref

            # Only a canonical "BOOK.C.V" target tells us its book; anything else
            # (a hand-written "Jn 1:1" in a personal collection) goes through as-is.
            if "." not in rel.target_ref:
                out.append(dataclasses.replace(rel, target_ref_margin=label))
                previous_book = None
                continue

            book = rel.target_ref.split(".")[0]

            # _localize_ref spells the book out ("Joël 3:1-5"); a margin needs the
            # abbreviation the BJ uses ("Jl 3:1-5"). Strip the full name, re-prefix
            # with the abbreviation unless the convention elides it.
            full = self._book_label(book) + " "
            if label.startswith(full):
                label = label[len(full):]
                if book != current_book and book != previous_book:
                    label = f"{self.normalizer.code_to_fr_abbr.get(book, book)} {label}"

            if rel.note == "+":
                label += "+"
            out.append(dataclasses.replace(rel, target_ref_margin=label))
            previous_book = book
        return out

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

    def _chapter_verses(self, book, chap):
        """All (book, chapter, verse) tuples of a chapter, in the corpus' own version."""
        temp_v = 'N1904' if self.normalizer.is_nt(book) else 'BHSA'
        objs = self.bible_provider.get_chapter(book, chap, temp_v)
        if not objs and not self.normalizer.is_nt(book):
            objs = self.bible_provider.get_chapter(book, chap, 'LXX')
        return [(book, chap, v_obj.verse) for v_obj in (objs or [])]

    def _expand_one(self, seg: str):
        """One passage ('Lc 24', 'Lc 24:24', 'Lc 24:24-26', 'Lc 23-24') ->
        (verses, book_code, chapter, verse). verse == 0 means chapter-level."""
        target_verses = []
        book_code = None
        chapter = None
        verse = None

        parsed_range = False
        if "-" in seg:
            parts = seg.split("-")
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
                                     target_verses.extend(self._chapter_verses(b_s, c))

                                 parsed_range = True
                                 book_code, chapter, verse = b_s, c_s, 0

        if not parsed_range:
             norm_ref = self.bible_provider.normalize_reference(seg)
             if not norm_ref:
                 raise ValueError(f"Invalid reference '{seg}'")

             book_code, chapter, verse = norm_ref

             if verse != 0:
                  target_verses.append((book_code, chapter, verse))

        return target_verses, book_code, chapter, verse

    def _expand(self, reference: str):
        """Multi-passage reference ('Lc 24:24-26;44', 'Lc 23:1-2;24:24-26') ->
        (verses, book_code, chapter, verse) of the first passage.
        A segment without any letter continues the previous one: it reuses its book,
        and its chapter too when the segment is a bare verse number."""
        segments = [s.strip() for s in reference.split(";") if s.strip()]
        if not segments:
            raise ValueError(f"Invalid reference '{reference}'")

        all_verses = []
        head = None
        book = chapter = None
        has_verse = False

        for seg in segments:
            if not any(ch.isalpha() for ch in seg):
                if not book:
                    raise ValueError(f"Invalid reference '{reference}'")
                if ":" in seg or "." in seg or "," in seg:
                    seg = f"{book} {seg}"
                elif has_verse:
                    seg = f"{book} {chapter}:{seg}"
                else:
                    raise ValueError(
                        f"Ambiguous reference '{reference}': write 'Lc 23;Lc 24' for "
                        f"chapters, or 'Lc 23:24' for a verse"
                    )

            verses, b, c, v = self._expand_one(seg)
            # A whole chapter inside a list must be materialized now: the single-passage
            # fallback in execute() only fires when nothing else was resolved.
            if not verses and v == 0 and len(segments) > 1:
                verses = self._chapter_verses(b, c)

            all_verses.extend(verses)
            book, chapter, has_verse = b, c, v != 0
            if head is None:
                head = (b, c, v)

        return list(dict.fromkeys(all_verses)), *head

    def execute(
        self,
        reference: str,
        translations: Optional[List[str]] = None,
        version: str = "N1904",
        french_version: Optional[str] = None,
        show_crossrefs: bool = False,
        crossref_full: bool = False,
        crossref_source: Optional[str] = None,
        crossref_max: int = 3
    ) -> VerseResponse:

        target_verses, book_code, chapter, verse = self._expand(reference)

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
        per_verse_refs = {}
        # No `verse != 0` gate: a whole chapter is materialized into target_verses
        # above, and each of its verses deserves its own margin.
        if show_crossrefs or crossref_full:
             s_filter = crossref_source
             # load_all() clears its cache on every call, so resolve the scope once for
             # the whole passage list; 'all' when it straddles OT and NT.
             scopes = {'nt' if self.normalizer.is_nt(b) else 'ot' for b, _, _ in target_verses}
             scope = scopes.pop() if len(scopes) == 1 else 'all'
             self.ref_db.load_all(source_filter=s_filter, scope=scope)

             def sort_key(rel):
                 parsed = self.bible_provider.normalize_reference(rel.target_ref)
                 if parsed:
                     bk, ch, vs = parsed
                     order = self.normalizer.book_order.get(bk, 999)
                     return (0, order, ch, vs)
                 return (1, rel.target_ref)

             def build(r):
                 return CrossReferenceRelation(
                     target_ref=r["target"],
                     target_ref_localized=self._localize_ref(r["target"]),
                     rel_type=CrossReferenceType(r.get("type", "parallel")),
                     note=r.get("note")
                 )

             notes = []
             relations = []
             seen = set()
             for b, c, v in target_verses:
                 refs_dict = self.ref_db.in_memory_refs.get(f"{b}.{c}.{v}")
                 if not refs_dict: continue

                 raw = refs_dict.get("relations", [])
                 v_notes = list(refs_dict.get("notes", []))

                 # ponytail: openbible stores relations in vote-rank order and can carry
                 # 30+ on a single verse, where the BJ margin shows 2 or 3. Cap on that
                 # order BEFORE sorting canonically, so the cut keeps the best-ranked.
                 # Rank is positional only -- if a source ever ships an explicit score,
                 # rank on it here instead.
                 v_relations = [build(r) for r in raw[:crossref_max]]
                 v_relations.sort(key=sort_key)
                 v_relations = self._margin_labels(v_relations, b)
                 if v_notes or v_relations:
                     per_verse_refs[f"{b}.{c}.{v}"] = VerseCrossReferences(
                         notes=v_notes, relations=v_relations
                     )

                 for n in v_notes:
                     if n not in notes: notes.append(n)

                 for r in raw:
                     dedup_key = (r["target"], r.get("type"), r.get("note"))
                     if dedup_key in seen: continue
                     seen.add(dedup_key)
                     relations.append(build(r))

             if notes or relations:
                 c_refs_model = VerseCrossReferences(
                     notes=notes,
                     relations=relations
                 )
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

        if per_verse_refs:
            verses_data = [
                dataclasses.replace(
                    item,
                    cross_references=per_verse_refs.get(
                        f"{item.primary.book_code}.{item.primary.chapter}.{item.primary.verse}"
                    )
                )
                for item in verses_data
            ]

        return VerseResponse(
            reference=reference,
            verses=verses_data,
            cross_references=c_refs_model
        )
