class VersePrinter:
    def __init__(self, tob_api, n1904_app, normalizer, reference_db):
        self.tob_api = tob_api
        self.app = n1904_app
        self.normalizer = normalizer
        self.ref_db = reference_db

    def get_french_text(self, book_en, chapter_num, verse_num):
        if not self.tob_api:
            return ""
            
        F = self.tob_api.F
        L = self.tob_api.L
        
        book_fr = self.normalizer.n1904_to_tob.get(book_en)
        if not book_fr:
            # Try direct mapping if not found (e.g. if N1904 uses spaces instead of underscores)
            book_fr = self.normalizer.n1904_to_tob.get(book_en.replace(" ", "_"))
            
        if not book_fr:
            return f"[TOB: Book '{book_en}' not found]"

        # 1. Find book node
        book_node = None
        for n in F.otype.s('book'):
            if F.book.v(n) == book_fr:
                book_node = n
                break
                
        if not book_node:
            return f"[TOB: Book '{book_fr}' node not found]"

        # 2. Find chapter node
        chapter_node = None
        for n in L.d(book_node, otype='chapter'):
            if F.chapter.v(n) == int(chapter_num):
                chapter_node = n
                break
                
        if not chapter_node:
            return f"[TOB: Chapter {chapter_num} not found]"

        # 3. Find verse node
        verse_node = None
        for n in L.d(chapter_node, otype='verse'):
            if F.verse.v(n) == int(verse_num):
                verse_node = n
                break
                
        if not verse_node:
            return "" # Verse might not exist in TOB or mapping issue

        # 4. Get text
        return F.text.v(verse_node)

    def format_ref_fr(self, target_str):
        """
        Format a reference like 'ACT.1.25-ACT.1.26' into 'Ac 1:25-26'.
        Converts book codes to French abbreviations.
        """
        if not target_str: return ""
        
        def parse_one(ref):
            parts = ref.split(".")
            if len(parts) >= 3:
                book_code = parts[0]
                chapter = parts[1]
                verse = parts[2]
                fr_abbr = self.normalizer.code_to_fr_abbr.get(book_code, book_code)
                return fr_abbr, chapter, verse
            return None, None, None

        if "-" in target_str:
            ranges = target_str.split("-")
            if len(ranges) == 2:
                start_ref = ranges[0]
                end_ref = ranges[1]
                
                s_abbr, s_ch, s_vs = parse_one(start_ref)
                
                if "." not in end_ref:
                    if s_abbr:
                        return f"{s_abbr} {s_ch}:{s_vs}-{end_ref}"
                
                e_abbr, e_ch, e_vs = parse_one(end_ref)
                
                if s_abbr:
                    if e_abbr and s_abbr == e_abbr and s_ch == e_ch:
                        return f"{s_abbr} {s_ch}:{s_vs}-{e_vs}"
                    elif e_abbr and s_abbr == e_abbr:
                        return f"{s_abbr} {s_ch}:{s_vs}-{e_ch}:{e_vs}"
                    elif e_abbr:
                        return f"{s_abbr} {s_ch}:{s_vs}-{e_abbr} {e_ch}:{e_vs}"
        
        abbr, ch, vs = parse_one(target_str)
        if abbr:
            return f"{abbr} {ch}:{vs}"
            
        return target_str

    def print_verse(self, node=None, book_en=None, chapter=None, verse=None, show_english=False, show_greek=True, show_french=True, show_crossref=False, cross_refs=None, show_crossref_text=False):
        if not self.app:
            return
            
        api = self.app.api
        T = api.T
        F = api.F
        L = api.L
        
        if node:
            section = T.sectionFromNode(node)
            book_en = section[0]
            chapter = int(section[1])
            verse = int(section[2])
        else:
            chapter = int(chapter)
            verse = int(verse)

        book_fr = self.normalizer.n1904_to_tob.get(book_en)
        if not book_fr:
            book_fr = self.normalizer.n1904_to_tob.get(book_en.replace(" ", "_"))
        if not book_fr:
            book_fr = book_en
        
        # Header
        print(f"\n{book_fr} {chapter}:{verse}")

        # Greek text
        if show_greek and node:
            greek_text = T.text(node)
            if greek_text and greek_text.strip():
                print(f"{greek_text}")
        
        # English translation
        if show_english and node:
            words = L.d(node, otype='word')
            english_text = []
            for w in words:
                trans = F.trans.v(w) if hasattr(F, 'trans') else ""
                if not trans and hasattr(F, 'gloss'):
                    trans = F.gloss.v(w)
                english_text.append(trans)
            print(f"{' '.join(english_text)}")
        
        # French translation (TOB)
        if show_french:
            french_text = self.get_french_text(book_en, chapter, verse)
            if french_text and not french_text.startswith("[TOB:"):
                print(f"{french_text}")
            elif french_text and node:
                 print(f"{french_text}")

        # Cross-references
        if show_crossref:
            # We need the 3-letter code for the current book to look up refs
            # normalizer has n1904_to_code
            
            # Key lookup: e.g. "JHN.1.1"
            # book_en might be "John" or "1_John" etc.
            
            # Try to get book code
            book_code = self.normalizer.n1904_to_code.get(book_en)
            if not book_code:
                 book_code = self.normalizer.n1904_to_code.get(book_en.replace(" ", "_"))
            
            if book_code:
                ref_key = f"{book_code}.{chapter}.{verse}"
                
                # Filter refs for this specific verse
                # If cross_refs is passed (pre-filtered dict), utilize it
                # The 'cross_refs' arg in the original function seemed to be the whole DB dictionary
                # Here we can use self.ref_db.in_memory_refs
                
                # If the caller didn't ensure data is loaded, we might miss it.
                # Ideally main.py calls ref_db.load_all() before using this.
                
                if ref_key in self.ref_db.in_memory_refs:
                    data = self.ref_db.in_memory_refs[ref_key]
                    
                    print("\n––––––––––")
                    
                    # 1. Notes
                    if data.get("notes"):
                        print("    Notes:")
                        for n in data["notes"]:
                            print(f"        {n}")
                        print("")
                    
                    # 2. Relations grouped by type
                    relations = data.get("relations", [])
                    by_type = {}
                    for r in relations:
                         t = r.get("type", "other").capitalize()
                         if t not in by_type: by_type[t] = []
                         by_type[t].append(r)
                    
                    for t, rels in by_type.items():
                        print(f"    {t}: ")
                        for r in rels:
                            target = r["target"]
                            fmt_target = self.format_ref_fr(target)
                            note = r.get("note", "")
                            # If detailed crossref requested (text), we would fetch it here
                            # But current specs say "crossref-full" was partial in original
                            # Let's simple print
                            line = f"        {fmt_target}"
                            if show_crossref_text: 
                                if note: line += f" ({note})"
                            else:
                                if note: line += "" # Original didn't show note in simple list often?
                                # Let's stick to original behavior:
                                # Original code:
                                # print(f"        {fmt_target}")
                            print(line)
