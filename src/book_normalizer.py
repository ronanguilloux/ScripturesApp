import json
import os

class BookNormalizer:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.abbreviations = {}
        self.n1904_to_tob = {}
        self.n1904_to_code = {}
        self.code_to_fr_abbr = {}
        self.code_to_en_abbr = {}
        self.code_to_abbreviations = {}
        self.code_to_n1904 = {}
        self.book_order = {}
        self._load_mappings()

    def _load_mappings(self):
        path = os.path.join(self.data_dir, "bible_books.json")
        if not os.path.exists(path):
            print(f"Warning: Mapping file not found at {path}")
            return

        try:
            with open(path, "r") as f:
                data = json.load(f)
            
            books = data.get("books", {})
            for i, (code, info) in enumerate(books.items()):
                self.book_order[code] = i
                en_info = info.get("en", {})
                en_label = en_info.get("label")
                abbreviations = en_info.get("abbreviations", [])
                
                # Canonical is first element
                en_abbr = abbreviations[0] if abbreviations else None

                # Internal N1904 key construction (legacy logic preserved)
                en_key = en_label if en_label else ""
                if en_key.startswith("1 "): en_key = "I_" + en_key[2:]
                elif en_key.startswith("2 "): en_key = "II_" + en_key[2:]
                elif en_key.startswith("3 "): en_key = "III_" + en_key[2:]
                en_key = en_key.replace(" ", "_")
                
                fr = info.get("fr", {})
                fr_label = fr.get("label")
                fr_abbreviations = fr.get("abbreviations", [])
                fr_abbr = fr_abbreviations[0] if fr_abbreviations else None
                
                if en_key:
                    self.n1904_to_tob[en_key] = fr_label
                    self.n1904_to_code[en_key] = code
                    self.code_to_fr_abbr[code] = fr_abbr
                    self.code_to_en_abbr[code] = en_abbr
                    self.code_to_abbreviations[code] = abbreviations # Now stores all abbreviations
                    self.code_to_n1904[code] = en_key
                    
                    # Register English variations
                    self.abbreviations[en_key] = en_key
                    self.abbreviations[code] = en_key 
                    if en_label: self.abbreviations[en_label] = en_key
                    
                    # Register all abbreviations
                    for abbr in abbreviations:
                        self.abbreviations[abbr] = en_key
                        if " " in abbr:
                            self.abbreviations[abbr.replace(" ", "")] = en_key

                # Register French variations
                for fr_abbr_item in fr_abbreviations:
                    self.abbreviations[fr_abbr_item] = en_key
                    if " " in fr_abbr_item:
                         self.abbreviations[fr_abbr_item.replace(" ", "")] = en_key
                
                if fr_label: self.abbreviations[fr_label] = en_key
            
            # Clean up: No more hardcoded aliases here!

        except Exception as e:
            print(f"Warning: Could not load book mappings: {e}")

    def normalize_reference(self, ref_str):
        """
        Normalize a reference string (e.g. "Mc 1:1") to a tuple (BookCode, Chapter, Verse) 
        and a standardized string (e.g. "MRK.1.1").
        Returns (book_code, chapter, verse, standardized_str) or None if invalid.
        """
        # Simple cleanup
        ref_str = ref_str.strip().replace(',', ':')
        
        # 1. Identify valid book name/abbr
        # We need to split space-separated or find longest match
        parts = ref_str.split()
        book_key = None
        remaining = ""
        
        if len(parts) >= 2:
            two_word = f"{parts[0]} {parts[1]}"
            if two_word in self.abbreviations:
                book_key = self.abbreviations[two_word]
                remaining = " ".join(parts[2:])
            elif parts[0] in self.abbreviations:
                book_key = self.abbreviations[parts[0]]
                remaining = " ".join(parts[1:])
        elif len(parts) == 1:
            # Maybe just "Gen.1.1" or "Gen"
            # Try splitting by dot if present
            if "." in parts[0] and not parts[0].replace(".", "").isdigit():
                 subparts = parts[0].split(".")
                 if subparts[0] in self.abbreviations:
                     book_key = self.abbreviations[subparts[0]]
                     # Reconstruct 1.1 part
                     remaining = ".".join(subparts[1:])
            elif parts[0] in self.abbreviations:
                book_key = self.abbreviations[parts[0]]
        
        if not book_key:
            return None

        book_code = self.n1904_to_code.get(book_key) or self.n1904_to_code.get(book_key.replace(" ", "_"))
        if not book_code:
            return None

        # 2. Parse Chapter:Verse
        # remaining could be "1:1", "1.1", "1", etc.
        # standardize separators
        clean_rem = remaining.replace(":", ".")
        
        chapter = 0
        verse = 0
        
        if "." in clean_rem:
            c_v = clean_rem.split(".")
            if len(c_v) >= 2:
                try:
                    chapter = int(c_v[0])
                    verse = int(c_v[1])
                except ValueError:
                    pass
        else:
             try:
                 if clean_rem:
                    chapter = int(clean_rem)
             except ValueError:
                 pass
        
        if chapter > 0:
            std_str = f"{book_code}.{chapter}.{verse}" if verse > 0 else f"{book_code}.{chapter}"
            return (book_code, chapter, verse, std_str)
        
        return None
