class ReferenceHandler:
    def __init__(self, n1904_app, lxx_provider, normalizer, verse_printer):
        self.app = n1904_app
        self.lxx_provider = lxx_provider # Callable that returns LXX app or None
        self.normalizer = normalizer
        self.printer = verse_printer

    def _get_node_and_app(self, ref_str):
        # Try N1904 first
        node = self.app.nodeFromSectionStr(ref_str)
        if node:
            # nodeFromSectionStr sometimes returns a list or error msg if not safe? 
            # In TF it usually returns int (node) or None.
            # But the original code checked isinstance(node, int)
            if isinstance(node, int):
                return node, self.app

        # Try LXX (Lazy Load)
        if self.lxx_provider:
            lxx_app = self.lxx_provider()
            if lxx_app:
                node = lxx_app.nodeFromSectionStr(ref_str)
            if node and isinstance(node, int):
                return node, lxx_app
        
        return None, None

    def handle_reference(self, ref_str, show_english=False, show_greek=True, show_french=True, show_crossref=False, cross_refs=None, show_crossref_text=False):
        api = self.app.api
        F = api.F
        L = api.L
        # Note: T, F, L here are from N1904. If we switch to LXX, we need that app's API.
        # But for logic that doesn't use T/F/L directly (like _get_node_and_app wrapper), it's fine.
        # However, "Chapter reference" logic below uses F.otype.s('chapter') from N1904.
        # We need to adapt that logic too.

        # Normalize reference
        ref_str = ref_str.replace(',', ':')
        
        # Check if reference starts with any abbreviation
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
                            book_fr = self.normalizer.n1904_to_tob.get(book)
                            if not book_fr: book_fr = book
                        else:
                            book = book_chapter
                            chapter = ""
                        
                        for v_num in range(start_v, end_v + 1):
                            single_ref = f"{book_chapter}:{v_num}"
                            node, source_app = self._get_node_and_app(single_ref)
                            if node:
                                self.printer.print_verse(node=node, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text, source_app=source_app)
                            else:
                                if ' ' in book_chapter:
                                    b, c = book_chapter.rsplit(' ', 1)
                                    self.printer.print_verse(book_en=b, chapter=c, verse=v_num, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text)
                                else:
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
                        
                        # Try N1904 Chapter
                        chapter_nodes = [n for n in F.otype.s('chapter') 
                                        if F.book.v(n) == book_name and F.chapter.v(n) == chapter_num]
                        
                        if chapter_nodes:
                            chapter_node = chapter_nodes[0]
                            verse_nodes = L.d(chapter_node, otype='verse')
                            for verse_node in verse_nodes:
                                self.printer.print_verse(node=verse_node, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text, source_app=self.app)
                            return
                        
                        # Try LXX Chapter (Lazy Load)
                        if self.lxx_provider:
                             lxx_app = self.lxx_provider()
                             if lxx_app:
                                 # Use the app's lookup since it handles normalization and overrides
                                 lxx_node = lxx_app.nodeFromSectionStr(f"{book_name} {chapter_num}")
                                 
                                 if lxx_node and lxx_app.api.F.otype.v(lxx_node) == 'chapter':
                                     verse_nodes = lxx_app.api.L.d(lxx_node, otype='verse')
                                     for verse_node in verse_nodes:
                                         self.printer.print_verse(node=verse_node, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text, source_app=lxx_app)
                                     return

                        # Fallback to TOB extraction loop
                        v = 1
                        found_any = False
                        while True:
                            txt = self.printer.get_french_text(book_name, chapter_num, v)
                            if (not txt or txt.startswith("[TOB:")) and v > 1:
                                break
                            if txt and not txt.startswith("[TOB:"):
                                self.printer.print_verse(book_en=book_name, chapter=chapter_num, verse=v, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text)
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
                otype = source_app.api.F.otype.v(node)
                self.printer.print_verse(node=node, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text, source_app=source_app)
            else:
                if ":" in ref_str and " " in ref_str:
                    parts = ref_str.rsplit(' ', 1)
                    book_name = parts[0]
                    if ":" in parts[1]:
                        ch_v = parts[1].split(":")
                        if len(ch_v) == 2:
                            try:
                                ch = int(ch_v[0])
                                vs = int(ch_v[1])
                                self.printer.print_verse(book_en=book_name, chapter=ch, verse=vs, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text)
                                return
                            except ValueError:
                                pass

                print(f"Could not find reference: {ref_str}")
                
        except Exception as e:
            print(f"Error processing reference: {e}")
