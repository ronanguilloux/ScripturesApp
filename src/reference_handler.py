class ReferenceHandler:
    def __init__(self, n1904_provider, lxx_provider, bhsa_provider, normalizer, verse_printer):
        self.n1904_provider = n1904_provider # Callable returning N1904 app
        self.lxx_provider = lxx_provider 
        self.bhsa_provider = bhsa_provider
        self.normalizer = normalizer
        self.printer = verse_printer

    def _get_node_and_app(self, ref_str):
        # Determine book type
        norm = self.normalizer.normalize_reference(ref_str)
        if not norm:
            return None, None
            
        code, ch, vs, _ = norm
        
        # Smart Loading Logic
        if self.normalizer.is_nt(code):
             # Try N1904 (New Testament)
             if self.n1904_provider:
                 n1904_app = self.n1904_provider()
                 if n1904_app:
                     # Use tuple lookup for robustness
                     book_name = self.normalizer.code_to_n1904.get(code)
                     if book_name:
                         # Verify if nodeFromSection can accept the tuple
                         # TF API: T.nodeFromSection((book, chapter, verse))
                         node = n1904_app.api.T.nodeFromSection((book_name, ch, vs))
                         if node:
                             return node, n1904_app
                         
        elif self.normalizer.is_ot(code):
             # Try LXX (Old Testament)
             if self.lxx_provider:
                 lxx_app = self.lxx_provider()
                 if lxx_app:
                     node = lxx_app.nodeFromSectionStr(ref_str)
                     if node and isinstance(node, int):
                         return node, lxx_app
                         
             # Also try BHSA (Hebrew) if lxx fails or as alternative?
             # Usually we return the "driver" app (LXX for OT Greek usually, or BHSA for Hebrew).
             # If strict Hebrew requested, handle_reference logic handles it via show_hebrew flag.
             # But for a default node, we prefer LXX (Greek) if consistent with N1904?
             # Actually, if we want to show Hebrew by default, maybe return BHSA node?
             # But VersePrinter expects a node to print.
             
             # Fallback: if LXX didn't work (e.g. not loaded or book missing), try BHSA
             if self.bhsa_provider:
                  bhsa = self.bhsa_provider()
                  if bhsa:
                      node = bhsa.nodeFromSectionStr(ref_str)
                      if node: return node, bhsa

        return None, None

    def handle_reference(self, ref_str, show_english=False, show_greek=True, show_french=True, show_arabic=False, show_crossref=False, cross_refs=None, show_crossref_text=False, show_hebrew=False, french_version='tob', compact_mode=0):
        # 1. Normalize first to decide strategies
        norm = self.normalizer.normalize_reference(ref_str)
        
        # Defaults if normalization fails (shouldn't happen often if we want to proceed)
        is_ot = False
        is_nt = False
        book_code = None
        
        if norm:
            book_code = norm[0]
            is_ot = self.normalizer.is_ot(book_code)
            is_nt = self.normalizer.is_nt(book_code)
        
        # SMART DEFAULTS Override
        # If no explicit "show" flags were likely toggled (we can't easily know if they were defaults or user choice here easily without passing more args).
        # But we can enforce:
        # If NT -> Force show_hebrew = False (unless user really tried? No, physically impossible reference)
        # If OT -> We want to show Hebrew by default? 
        # The user said: "tob Gn 1:1" should show Hebrew. "tob Mc 1:1" should NOT load Hebrew.
        
        if is_nt:
            show_hebrew = False
            # Ensure N1904 is loaded
            driver_app = self.n1904_provider() if self.n1904_provider else None
        elif is_ot:
            # For OT, user wants Hebrew. 
            # If show_hebrew was passed as False (CLI default might be False?), force True?
            # Wait, main.py passes show_hebrew based on flags.
            # I should update main.py defaults? Or here?
            # "I'd like the change in tob Gn 1:1 where it displays hebrew not to affect..."
            # Implies by default it SHOULD display Hebrew for OT.
            # if not show_hebrew: # If not already enabled explicitly
            #      show_hebrew = True
            
            # Ensure proper drivers for text
            # We don't need N1904
            pass
        
        if not norm:
             # Basic handling if normalization failed drastically but ref_str exists
             pass

        # ... (rest of logic needs to use providers)
        
        # We need an app to get F/L/TF logic for "chapter" or range iteration?
        # N1904 app was the "main" app. functionality like F.otype lives there.
        # If we are in OT mode, we might not HAVE N1904 app if we skip loading it!
        # We should use the "driver" app for structural logic.
        
        app = None
        if is_nt and self.n1904_provider:
            app = self.n1904_provider()
        elif is_ot and self.lxx_provider:
            app = self.lxx_provider()
        
        if not app and self.bhsa_provider: 
             app = self.bhsa_provider() # Fallback for OT if LXX missing?
        
        if not app and self.n1904_provider:
             app = self.n1904_provider() # Ultimate fallback (e.g. unknown book)

        if not app:
             print("Error: No suitable dataset loaded for this reference.")
             return

        api = app.api
        F = api.F
        L = api.L
        
        # ... logic continues ...
        # I need to be careful about replacing "self.app" with "app" in the snippet.
        
        # (Snippet replacement follows)
        ref_str = ref_str.replace(',', ':')
        
        # ... abbrevs ...
        parts = ref_str.split()
        if len(parts) >= 2:
            two_word_abbr = f"{parts[0]} {parts[1]}"
            if two_word_abbr in self.normalizer.abbreviations:
                ref_str = f"{self.normalizer.abbreviations[two_word_abbr]} {' '.join(parts[2:])}"
                parts = ref_str.split() 
            elif parts[0] in self.normalizer.abbreviations:
                ref_str = f"{self.normalizer.abbreviations[parts[0]]} {' '.join(parts[1:])}"
                parts = ref_str.split() 
        elif len(parts) == 1:
            if parts[0] in self.normalizer.abbreviations:
                ref_str = self.normalizer.abbreviations[parts[0]]
                parts = [ref_str]
                
        try:
            # Check if it's a range (e.g., "Luke 1:4-7")
            if "-" in ref_str and ":" in ref_str:
                last_colon_idx = ref_str.rfind(":")
                if last_colon_idx != -1:
                    book_chapter = ref_str[:last_colon_idx]
                    verses_part = ref_str[last_colon_idx+1:]
                    
                    if "-" in verses_part:
                        start_v, end_v = verses_part.split("-")
                        start_v = int(start_v)
                        end_v = int(end_v)
                        
                        if ' ' in book_chapter:
                            book, chapter = book_chapter.rsplit(' ', 1)
                            # book_fr = self.normalizer.n1904_to_tob.get(book)
                            # if not book_fr: book_fr = book
                        else:
                            book = book_chapter
                            chapter = ""
                        
                        # Print Header once if in compact mode
                        if compact_mode > 0:
                            if ' ' in book_chapter:
                                b_name = book_chapter.rsplit(' ', 1)[0]
                                # localized name logic
                                header_name = b_name
                                if not show_english:
                                     # Try to map to French
                                     fr_name = self.normalizer.n1904_to_tob.get(b_name)
                                     if not fr_name:
                                         # Try code based lookup
                                         code = self.normalizer.n1904_to_code.get(b_name)
                                         if code:
                                             fr_name = self.normalizer.n1904_to_tob.get(self.normalizer.code_to_n1904.get(code))
                                     
                                     if fr_name: header_name = fr_name
                                
                                print(f"\n{header_name} {book_chapter.split()[-1]}:{start_v}-{end_v}")
                            else:
                                print(f"\n{book_chapter} {start_v}-{end_v}")

                        for v_num in range(start_v, end_v + 1):
                            single_ref = f"{book_chapter}:{v_num}"
                            node, source_app = self._get_node_and_app(single_ref)
                            if node:
                                self.printer.print_verse(node=node, show_english=show_english, show_greek=show_greek, show_french=show_french, show_arabic=show_arabic, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text, source_app=source_app, show_hebrew=show_hebrew, french_version=french_version, compact_mode=compact_mode)
                            else:
                                if ' ' in book_chapter:
                                    b, c = book_chapter.rsplit(' ', 1)
                                    self.printer.print_verse(book_en=b, chapter=c, verse=v_num, show_english=show_english, show_greek=show_greek, show_french=show_french, show_arabic=show_arabic, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text, show_hebrew=show_hebrew, french_version=french_version, compact_mode=compact_mode)
                                else: # book only?
                                    print(f"Could not find verse: {single_ref}")
                        return

            # Check if it's a chapter reference (e.g., "John 13")
            if ":" not in ref_str and " " in ref_str:
                parts = ref_str.rsplit(' ', 1)
                if len(parts) == 2:
                    book_name = parts[0]
                    try:
                        chapter_num = int(parts[1])
                        
                        book_fr = self.normalizer.n1904_to_tob.get(book_name)
                        if not book_fr: book_fr = book_name
                        print(f"\n{book_fr} {chapter_num}")
                        
                        # Use driver app to list verses
                        # NOTE: For lazy N1904, we might not have 'app' if we are in OT mode. 
                        # We use the app determined above.
                        
                        # Try finding chapter node in the driver app
                        # For N1904/LXX/BHSA, logic is similar if using TF
                        
                        # But standard TF search might differ.
                        # N1904: F.otype.s('chapter')
                        # LXX: same
                        # BHSA: same
                        
                        # We need to use nodeFromSectionStr logic for chapters?
                        # Or just iterate.
                        
                        # Let's try to find chapter node using app's section lookup if available, or manual filter.
                        # Apps usually have nodeFromSectionStr("Book Chapter")
                        
                        chapter_node = app.nodeFromSectionStr(f"{book_name} {chapter_num}")
                        if chapter_node and F.otype.v(chapter_node) == 'chapter':
                             verse_nodes = L.d(chapter_node, otype='verse')
                             # Print Header for Chapter block
                             if compact_mode > 0:
                                 # Header already printed above at line 187?
                                 # Yes: print(f"\n{book_fr} {chapter_num}") is unconditional above.
                                 # Wait, if compact_mode, print_verse suppresses its own header.
                                 # So the header at 187 covers the whole block. Perfect.
                                 pass
                                 
                             for verse_node in verse_nodes:
                                 self.printer.print_verse(node=verse_node, show_english=show_english, show_greek=show_greek, show_french=show_french, show_arabic=show_arabic, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text, source_app=app, show_hebrew=show_hebrew, french_version=french_version, compact_mode=compact_mode)
                             return

                        # Fallback to TOB extraction loop
                        v = 1
                        found_any = False
                        while True:
                            txt = self.printer.get_french_text(book_name, chapter_num, v)
                            if (not txt or txt.startswith("[TOB:")) and v > 1:
                                break
                            if txt and not txt.startswith("["):
                                self.printer.print_verse(book_en=book_name, chapter=chapter_num, verse=v, show_english=show_english, show_greek=show_greek, show_french=show_french, show_arabic=show_arabic, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text, show_hebrew=show_hebrew, french_version=french_version, compact_mode=compact_mode)
                                found_any = True
                            v += 1
                        if found_any: return
                        
                        print(f"Could not find chapter: {ref_str}")
                        return

                    except ValueError:
                        pass  
            
            # Fallback to single reference lookup
            node, source_app = self._get_node_and_app(ref_str)
            
            if node:
                # For single verse, compact mode basically just suppresses header and adds prefix?
                # User asked for it "when it is a suite of verses... OR Mc 1 tout seul".
                # "Mc 1:1" is also a single verse.
                # If compact mode is on, we print Header once.
                if compact_mode > 0:
                     # Calculate header
                     header_str = ref_str
                     if not show_english:
                         # Attempt to localize the book part of ref_str
                         # ref_str could be "Luke 24:49" or "Luke 24:49" (normalized)
                         if " " in ref_str:
                             parts = ref_str.rsplit(" ", 1) # Split book / chapter:verse
                             b_name = parts[0]
                             rest = parts[1]
                             
                             fr_name = self.normalizer.n1904_to_tob.get(b_name)
                             if not fr_name:
                                 code = self.normalizer.n1904_to_code.get(b_name)
                                 if code:
                                      fr_name = self.normalizer.n1904_to_tob.get(self.normalizer.code_to_n1904.get(code))
                             
                             if fr_name:
                                 header_str = f"{fr_name} {rest}"
                     
                     print(f"\n{header_str}")
                     
                self.printer.print_verse(node=node, show_english=show_english, show_greek=show_greek, show_french=show_french, show_arabic=show_arabic, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text, source_app=source_app, show_hebrew=show_hebrew, french_version=french_version, compact_mode=compact_mode)
            else:
                 # Last ditch manual parse for TOB if node failed
                if ":" in ref_str and " " in ref_str:
                    parts = ref_str.rsplit(' ', 1)
                    book_name = parts[0]
                    if ":" in parts[1]:
                        ch_v = parts[1].split(":")
                        if len(ch_v) == 2:
                            try:
                                ch = int(ch_v[0])
                                vs = int(ch_v[1])
                                self.printer.print_verse(book_en=book_name, chapter=ch, verse=vs, show_english=show_english, show_greek=show_greek, show_french=show_french, show_arabic=show_arabic, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text, show_hebrew=show_hebrew, french_version=french_version, compact_mode=compact_mode)
                                return
                            except ValueError:
                                pass

                print(f"Could not find reference: {ref_str}")
                
        except Exception as e:
            # import traceback
            # traceback.print_exc()
            print(f"Error processing reference: {e}")
