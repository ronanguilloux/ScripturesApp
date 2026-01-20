class VersePrinter:
    def __init__(self, tob_provider, n1904_provider, normalizer, reference_db, bhsa_provider=None, bj_provider=None, nav_provider=None):
        self.tob_provider = tob_provider
        self.n1904_provider = n1904_provider
        self.bj_provider = bj_provider
        self.nav_provider = nav_provider
        self._tob_api = None
        self._bj_api = None
        self._nav_api = None
        self._n1904_app = None
        self.lxx = None 
        self.normalizer = normalizer
        self.ref_db = reference_db
        self.bhsa_provider = bhsa_provider

    @property
    def tob_api(self):
        if self._tob_api is None and self.tob_provider:
            self._tob_api = self.tob_provider()
        return self._tob_api
        
    @property
    def bj_api(self):
        if self._bj_api is None and self.bj_provider:
            self._bj_api = self.bj_provider()
        return self._bj_api

    @property
    def app(self):
        if self._n1904_app is None and self.n1904_provider:
             self._n1904_app = self.n1904_provider()
        return self._n1904_app

    @property
    def nav_api(self):
        if self._nav_api is None and self.nav_provider:
            self._nav_api = self.nav_provider()
        return self._nav_api

    def get_hebrew_text(self, book_en, chapter_num, verse_num):
        if not self.bhsa_provider: 
            return None
            
        bhsa_app = self.bhsa_provider()
        if not bhsa_app: return None

        # Look up node in BHSA
        # Ideally use OfflineBHSAApp nodeFromSectionStr, but here we might not have that method exposed on VersePrinter interface easily without creating a new instance.
        # But wait, bhsa_provider returns the OfflineBHSAApp instance.
        
        node = bhsa_app.nodeFromSectionStr(f"{book_en} {chapter_num}:{verse_num}")
        if node:
            # Get text from words
            # Confirmed via research: g_word_utf8
            words = bhsa_app.api.L.d(node, otype='word')
            text = " ".join([bhsa_app.api.F.g_word_utf8.v(w) for w in words])
            return text
        return None

    def get_nav_text(self, book_en, chapter_num, verse_num):
        if not self.nav_api:
            return ""
        
        # NAV uses English titles (e.g. Genesis) matching features.
        # Ensure we use the correct book name.
        # N1904 'book_en' typically matches standard English.
        # Note: NAV features are stored as Strings (default), so we must pass str(chapter).
        
        
        # Normalize book name to match NAV (usually expects full English name like "Genesis")
        # Try code lookup first
        mapped_name = self.normalizer.code_to_n1904.get(book_en)
        if not mapped_name:
             # Try abbreviations
             mapped_name = self.normalizer.abbreviations.get(book_en)
        
        if mapped_name:
             book_en = mapped_name
             
        node = self.nav_api.T.nodeFromSection((book_en, str(chapter_num), str(verse_num)))
        
        if not node:
             # Try replacing spaces or underscores if mismatch
             node = self.nav_api.T.nodeFromSection((book_en.replace("_", " "), str(chapter_num), str(verse_num)))

        if not node:
             return f"[NAV: Verse not found]"

        # Get text
        return self.nav_api.T.text(node)

    def get_bj_text(self, book_en, chapter_num, verse_num):
        if not self.bj_api:
            return ""
        
        # Determine BJ book label from "bj" entry in bible_books.json
        # 1. Normalize book_en to code
        book_code = self.normalizer.n1904_to_code.get(book_en)
        if not book_code:
             # Try abbreviation
             canon = self.normalizer.abbreviations.get(book_en)
             if canon:
                 book_code = self.normalizer.n1904_to_code.get(canon)
        
        if not book_code:
            return f"[BJ: Unknown Book '{book_en}']"
            
        # 2. Get BJ label from JSON data (loaded in normalizer?)
        # Normalizer has `code_to_fr_abbr` but not `code_to_bj` directly exposed?
        # We might need to load it or use a mapping.
        # But wait, BJ TF uses the *label* as the value of the 'book' feature in my conversion?
        # Yes: `f.write(f"{d['id']}\t{d['book']}\n")` where `d['book']` was the Code (e.g. "GEN")?
        # Let me re-verify convert_bj_epub.py.
        # I set `self.current_book_code = code` (GEN, EXO).
        # And I used that for the feature value. 
        # So BJ TF uses STANDARD CODES (GEN, EXO) for the `book` feature!
        # It does NOT use "La Genèse" as the feature value.
        # It uses Codes.
        # So I just need to match `book_code`.
        
        F = self.bj_api.F
        L = self.bj_api.L
        
        # 1. Find book node
        # In BJ TF, book feature is on book node.
        # We can iterate book nodes.
        book_node = None
        for n in F.otype.s('book'):
            if F.book.v(n) == book_code:
                book_node = n
                break
                
        if not book_node:
             # Try fallback to French name just in case my memory is wrong?
             # No, verify_bj output showed `Node ...: [JOB 19:14]`. "JOB" is code.
             return f"[BJ: Book '{book_code}' not found]"

        # 2. Find chapter
        chapter_node = None
        for n in L.d(book_node, otype='chapter'):
            # BJ chapter feature is int
            if F.chapter.v(n) == int(chapter_num):
                chapter_node = n
                break
                
        if not chapter_node:
            return f"[BJ: Chapter {chapter_num} not found]"
            
        # 3. Find verse
        verse_node = None
        for n in L.d(chapter_node, otype='verse'):
             if F.verse.v(n) == int(verse_num):
                 verse_node = n
                 break
                 
        if not verse_node:
            return ""

        # 4. Get Text
        # Iterate words and join 'text' feature (which is surface form)
        words = L.d(verse_node, otype='word')
        # BJ text feature handles spacing?
        # My script: `safe_text = w['text']...`
        # `f.write(f"{safe_text}\n")`
        # Using `T.text` might automatically add spaces if configured.
        # My `otext.config` had `@fmt:text-orig-full={text}`.
        # Standard TF behavior for unconfigured formats is separated by space?
        # Let's manual join to be safe, or use `features='text'`
        return " ".join([F.text.v(w) for w in words])

    def get_french_text(self, book_en, chapter_num, verse_num):
        if not self.tob_api:
            return ""
            
        F = self.tob_api.F
        L = self.tob_api.L
        
        # 1. Normalize book_en to code
        book_code = self.normalizer.n1904_to_code.get(book_en)
        if not book_code:
             # Try abbreviation
             canon = self.normalizer.abbreviations.get(book_en)
             if canon:
                 book_code = self.normalizer.n1904_to_code.get(canon)
        
        if not book_code:
            return f"[TOB: Book '{book_en}' not found]"

        # 1. Find book node
        book_node = None
        for n in F.otype.s('book'):
            if F.book.v(n) == book_code:
                book_node = n
                break
                
        if not book_node:
            return f"[TOB: Book '{book_code}' node not found]"

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

        # 4. Get text (Join words)
        words = L.d(verse_node, otype='word')
        return " ".join([F.text.v(w) for w in words])

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

    def print_verse(self, node=None, book_en=None, chapter=None, verse=None, show_english=False, show_greek=True, show_french=True, show_arabic=False, show_crossref=False, cross_refs=None, show_crossref_text=False, source_app=None, show_hebrew=False, french_version='tob', compact_mode=0):
        if not source_app:
            source_app = self.app
            
        if not source_app:
            return
            
        api = source_app.api
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

        # Try to resolve book_fr using normalizer logic if direct key fails
        # 'book_en' might be 'Gen' (LXX) or 'Genesis' or 'MAT'
        # 1. Try resolving to code first, then to French label
        book_code = self.normalizer.n1904_to_code.get(book_en)
        if not book_code:
             # Try abbreviations or reverse lookup (if book_en is 'Numeri' from BHSA)
             # If book_en is 'Numeri', n1904_to_code won't find it directly maybe?
             # But let's rely on standard flow.
             canon = self.normalizer.abbreviations.get(book_en)
             if canon:
                 book_code = self.normalizer.n1904_to_code.get(canon)
        
        book_fr = None
        if book_code:
            en_key = self.normalizer.code_to_n1904.get(book_code)
            if en_key:
                book_fr = self.normalizer.n1904_to_tob.get(en_key)
        
        # Fallback to direct lookup if code path failed
        if not book_fr:
            book_fr = self.normalizer.n1904_to_tob.get(book_en)
        if not book_fr:
            book_fr = self.normalizer.n1904_to_tob.get(book_en.replace(" ", "_"))
            
        if not book_fr:
            book_fr = book_en
        
        # Determine Header Language
        header_book_name = book_fr
        
        if show_english:
             # Prefer English name if English translation is requested
             if book_code:
                 raw_en = self.normalizer.code_to_n1904.get(book_code)
                 if raw_en:
                      header_book_name = raw_en.replace("_", " ")
                 else:
                      header_book_name = book_en
             else:
                 header_book_name = book_en

        # Header logic
        # If compact_mode > 0, we suppress the per-verse header
        if compact_mode == 0:
            print(f"\n{header_book_name} {chapter}:{verse}")
            
        # Prefix logic
        prefix = ""
        if compact_mode == 1:
            prefix = f"v{verse}. "
        elif compact_mode == 2:
            prefix = "" # No prefix for very compact
            
        # For compact mode, we might want to collect all text and print in one go?
        # But print_verse is called per verse. 
        # Standard compact behavior: print(f"{prefix}{text}")
        
        # NOTE: Multiple requests (show_greek and show_french) in compact mode?
        # User said: "vers s'affichent chacun sur une ligne".
        # If showing multiple languages, putting them on ONE line might be messy.
        # But usually compact is used for single translation reading.
        # Let's print each requested text on its own line (or same line?).
        # If multiple languages, `print_verse` prints multiple lines naturally.
        # With compact mode, we retain the line breaks between LANGUAGES, but avoid the main Header.
        # And we prefix the FIRST language line? Or all? 
        # Usually prefix the first line is best.
        
        has_printed_prefix = False
        def get_prefix():
            nonlocal has_printed_prefix
            if not has_printed_prefix:
                has_printed_prefix = True
                return prefix
            # For subsequent lines of the SAME verse (e.g. diff languages), indent or repeat?
            # Repeating is ugly. Indenting is better. Or empty.
            if compact_mode > 0:
                 return " " * len(prefix) # Indent alignment?
            return ""

        # Hebrew Text
        if show_hebrew:
            # If current node IS Hebrew, print it
            # How to check? We can check if source_app has specific features or check if the app match BHSA
            # Or simpler: always try to fetch Hebrew from BHSA provider if show_hebrew is True
            # regardless of whether the driving node is N1904, LXX or BHSA.
            # BUT if the driving node IS BHSA, we already have the node!
            hebrew_text = None
            if self.bhsa_provider:
                 bhsa_app = self.bhsa_provider()
                 if bhsa_app and source_app.api == bhsa_app.api:
                     # Driving node is BHSA
                     if node:
                         words = L.d(node, otype='word')
                         # BHSA features: g_word_utf8
                         if hasattr(F, 'g_word_utf8'):
                             hebrew_text = " ".join([F.g_word_utf8.v(w) for w in words])
                 else:
                     # Fetch via alignment (Book/Chapter/Verse)
                     hebrew_text = self.get_hebrew_text(book_en, chapter, verse)
            
            if hebrew_text:
                print(f"{get_prefix()}{hebrew_text}")

        # Greek text
        if show_greek and node:
            # Check if source app has Greek text feature
            # N1904 and LXX use T.text logic or standard TF text
            greek_text = T.text(node)
            if greek_text and greek_text.strip():
                print(f"{get_prefix()}{greek_text}")
        
        # English translation (Only for N1904 source currently)
        if show_english and node and source_app == self.app:
            words = L.d(node, otype='word')
            english_text = []
            for w in words:
                trans = F.trans.v(w) if hasattr(F, 'trans') else ""
                if not trans and hasattr(F, 'gloss'):
                    trans = F.gloss.v(w)
                english_text.append(trans)
            print(f"{get_prefix()}{' '.join(english_text)}")
        
        # French/Arabic translation (TOB, BJ, NAV)
        if show_french:
            french_text = ""
            if french_version == 'bj':
                french_text = self.get_bj_text(book_en, chapter, verse)
            else:
                # Default to TOB
                french_text = self.get_french_text(book_en, chapter, verse)


            if french_text:
                 # Check for None/Empty or Error strings
                 if not french_text.startswith(f"[{french_version.upper()}:") or french_text.startswith(f"[{french_version.upper()}: Book"):
                     # We print errors if they are about missing books?
                     # Existing logic: `if french_text and not french_text.startswith("[TOB:")`
                     # But sometimes we might want to see it?
                     # Let's hide errors if typical mismatch.
                     if not french_text.startswith("["):
                         print(f"{get_prefix()}{french_text}")
                     elif node: # If driving node exists, output even if error?
                         # Only if it is NOT a "not found" error which is common for cross-versions
                         pass
 
        if show_arabic:
            # print(f"DEBUG: show_arabic is True. Book: {book_en}, Ch: {chapter}, Vs: {verse}")
            arabic_text = self.get_nav_text(book_en, chapter, verse)
            # print(f"DEBUG: arabic_text: {arabic_text}")
            if arabic_text:
                 # Check/Clean text
                 if not arabic_text.startswith("[NAV:"):
                      print(f"{get_prefix()}{arabic_text}")

        # Cross-references (Header logic might differ? No, cross-refs usually separate block)
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
                    
                    if compact_mode == 0:
                        print("\n––––––––––")
                    
                    # 1. Notes
                    if data.get("notes"):
                        if compact_mode == 0: print("    Notes:")
                        for n in data["notes"]:
                            if compact_mode > 0:
                                print(f"    [Note]: {n}")
                            else:
                                print(f"        {n}")
                        if compact_mode == 0: print("")
                    
                    # 2. Relations grouped by type
                    relations = data.get("relations", [])
                    by_type = {}
                    for r in relations:
                         t = r.get("type", "other").capitalize()
                         if t not in by_type: by_type[t] = []
                         by_type[t].append(r)
                    
                    for t, rels in by_type.items():
                        if compact_mode == 0: print(f"    {t}: ")
                        for r in rels:
                            target = r["target"]
                            fmt_target = self.format_ref_fr(target)
                            note = r.get("note", "")
                            # If detailed crossref requested (text), we would fetch it here
                            # But current specs say "crossref-full" was partial in original
                            # Let's simple print
                            if compact_mode == 0:
                                line = f"        {fmt_target}"
                            else:
                                line = f"    [{t}]: {fmt_target}"
                                
                            if show_crossref_text: 
                                if note: line += f" ({note})"
                            else:
                                if note: line += "" # Original didn't show note in simple list often?
                                # Let's stick to original behavior:
                                # Original code:
                                # print(f"        {fmt_target}")
                            print(line)
                            
                            if show_crossref_text:
                                refs_to_fetch = []
                                # Parse target for text fetching
                                # Logic compatible with 'ACT.1.25-ACT.1.26' or 'ACT.1.25'
                                if "-" in target:
                                    parts = target.split("-")
                                    if len(parts) == 2:
                                        start_p = parts[0].split(".")
                                        end_p = parts[1].split(".")
                                        
                                        # Case 1: Full ref to full ref "BOOK.C.V-BOOK.C.V"
                                        if len(start_p) == 3 and len(end_p) == 3:
                                            b_code = start_p[0]
                                            ch = int(start_p[1])
                                            s_v = int(start_p[2])
                                            # End verse check basic
                                            if b_code == end_p[0] and ch == int(end_p[1]):
                                                e_v = int(end_p[2])
                                                for v in range(s_v, e_v + 1):
                                                    refs_to_fetch.append((b_code, ch, v))
                                        
                                        # Case 2: Full ref to verse only? (unlikely in standardized db but possible in display logic)
                                        # The DB standardizes to full refs usually, but let's be safe.
                                else:
                                    parts = target.split(".")
                                    if len(parts) == 3:
                                        refs_to_fetch.append((parts[0], int(parts[1]), int(parts[2])))
                                
                                for b_code, ch, vs in refs_to_fetch:
                                    # Convert 3-letter code back to N1904 English name for get_french_text lookup?
                                    # get_french_text takes (book_en, ...). 
                                    # We need code_to_n1904 mapping.
                                    # normalizer has code_to_n1904.
                                    b_en = self.normalizer.code_to_n1904.get(b_code)
                                    if b_en:
                                        txt = ""
                                        if french_version == 'bj':
                                            txt = self.get_bj_text(b_en, ch, vs)
                                        elif french_version == 'nav':
                                            txt = self.get_nav_text(b_en, ch, vs)
                                        else:
                                            txt = self.get_french_text(b_en, ch, vs)
                                            
                                        if txt and not txt.startswith("["):
                                            print(f"            {txt}")
