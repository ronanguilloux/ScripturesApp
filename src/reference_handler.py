class ReferenceHandler:
    def __init__(self, n1904_app, normalizer, verse_printer):
        self.app = n1904_app
        self.normalizer = normalizer
        self.printer = verse_printer

    def handle_reference(self, ref_str, show_english=False, show_greek=True, show_french=True, show_crossref=False, cross_refs=None, show_crossref_text=False):
        api = self.app.api
        T = api.T
        F = api.F
        L = api.L

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
                            print(f"\n{book_fr} {chapter}:{start_v}-{end_v}")
                        else:
                            book = book_chapter
                            chapter = ""
                            print(f"\n{book_chapter}:{start_v}-{end_v}")
                        
                        for v_num in range(start_v, end_v + 1):
                            single_ref = f"{book_chapter}:{v_num}"
                            node = self.app.nodeFromSectionStr(single_ref)
                            if node and isinstance(node, int):
                                self.printer.print_verse(node=node, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text)
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
                        
                        chapter_nodes = [n for n in F.otype.s('chapter') 
                                        if F.book.v(n) == book_name and F.chapter.v(n) == chapter_num]
                        
                        if chapter_nodes:
                            chapter_node = chapter_nodes[0]
                            verse_nodes = L.d(chapter_node, otype='verse')
                            
                            for verse_node in verse_nodes:
                                self.printer.print_verse(node=verse_node, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text)
                            return
                        else:
                            # Fallback to printer's internal TOB check if N1904 node missing? 
                            # Or rely on printer.get_french_text returning empty if not found.
                            # The original logic had a fallback using API_TOB directly/indirectly.
                            # self.printer handles TOB logic if N1904 node is missing or we just iterate verses.
                            # Actually, original code had a specific loop using get_french_text
                            
                            # Let's replicate original logic:
                            # printer has get_french_text method.
                            
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
            node = self.app.nodeFromSectionStr(ref_str)
            
            if node and isinstance(node, int):
                self.printer.print_verse(node=node, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text)
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
