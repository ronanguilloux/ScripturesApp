import os
import contextlib
from typing import List, Optional, Any
from tf.app import use
from tf.fabric import Fabric

from src.ports.bible_provider import BibleProvider, MetadataProvider
from src.domain.models import Verse, Book, VerseCrossReferences, Language
from src.book_normalizer import BookNormalizer

class TextFabricAdapter(BibleProvider, MetadataProvider):
    def __init__(self, data_dir: str, n1904_provider=None, lxx_provider=None, bhsa_provider=None, tob_provider=None, bj_provider=None, nav_provider=None):
        self.data_dir = data_dir
        self.normalizer = BookNormalizer(data_dir)
        
        # Injected providers (callables returning app/api)
        self._n1904_provider = n1904_provider
        self._lxx_provider = lxx_provider
        self._bhsa_provider = bhsa_provider
        self._tob_provider = tob_provider
        self._bj_provider = bj_provider
        self._nav_provider = nav_provider

        # Lazy loading state (cache)
        self._n1904_app = None
        self._lxx_app = None
        self._bhsa_app = None
        self._tob_api = None
        self._bj_api = None
        self._nav_api = None 
        
        # Paths (should be injected via config, but hardcoded for now matching main.py)
        self.tob_dir = os.path.expanduser("~/text-fabric-data/TOB/1.0/")
        self.bj_dir = os.path.expanduser("~/text-fabric-data/BJ/1.0/")
        self.nav_dir = os.path.expanduser("~/text-fabric-data/NAV/1.0/")
        self.lxx_dir = os.path.expanduser("~/text-fabric-data/github/CenterBLC/LXX/tf/1935")

    # --- Lazy Loaders ---
    @property
    def n1904(self):
        if not self._n1904_app:
            if self._n1904_provider:
                 self._n1904_app = self._n1904_provider()
            
            if not self._n1904_app:
                with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                    try:
                        self._n1904_app = use("CenterBLC/N1904", version="1.0.0", silent=True)
                    except Exception:
                        pass
        return self._n1904_app

    @property
    def lxx(self):
        if not self._lxx_app:
            if self._lxx_provider:
                self._lxx_app = self._lxx_provider()

            if not self._lxx_app:
                 # Try offline first
                if os.path.exists(self.lxx_dir):
                    with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                        try:
                            TF = Fabric(locations=[self.lxx_dir], silent=True)
                            api = TF.load("", silent=True)
                            self._lxx_app = type('LXXStub', (), {'api': api})() # Mock app wrapper
                        except Exception:
                             pass
                if not self._lxx_app:
                     with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                        try:
                            self._lxx_app = use("CenterBLC/LXX", version="1935", check=False, silent=True)
                        except Exception:
                            pass
        return self._lxx_app

    @property
    def bhsa(self):
        if not self._bhsa_app:
            if self._bhsa_provider:
                self._bhsa_app = self._bhsa_provider()
                
            if not self._bhsa_app:
                with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                     try:
                         self._bhsa_app = use("ETCBC/bhsa", version="2021", silent=True)
                     except Exception:
                         pass
        return self._bhsa_app
    
    @property
    def tob(self):
        if not self._tob_api:
             if self._tob_provider:
                 self._tob_api = self._tob_provider()
                 
             if not self._tob_api:
                 if os.path.exists(self.tob_dir):
                     with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                         try:
                             TF = Fabric(locations=[self.tob_dir], silent=True)
                             self._tob_api = TF.load('text book chapter verse', silent=True)
                         except Exception:
                             pass
        return self._tob_api

    @property
    def bj_api(self):
        if not self._bj_api:
            if self._bj_provider:
                self._bj_api = self._bj_provider()
            
            if not self._bj_api:
                 if os.path.exists(self.bj_dir):
                     with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                         try:
                             TF = Fabric(locations=[self.bj_dir], silent=True)
                             self._bj_api = TF.load('text book chapter verse', silent=True)
                         except Exception:
                             pass
        return self._bj_api

    @property
    def nav_api(self):
        if not self._nav_api:
            if self._nav_provider:
                self._nav_api = self._nav_provider()
                
            if not self._nav_api:
                 if os.path.exists(self.nav_dir):
                     with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                         try:
                             TF = Fabric(locations=[self.nav_dir], silent=True)
                             self._nav_api = TF.load('text', silent=True)
                         except Exception:
                             pass
        return self._nav_api

    def normalize_reference(self, ref_string: str) -> Optional[tuple[str, int, int]]:
        res = self.normalizer.normalize_reference(ref_string)
        if res:
            return (res[0], res[1], res[2])
        return None

    def get_book_info(self, book_code: str) -> Optional[Book]:
        # Implement using normalizer data
        # BookNormalizer doesn't expose strict Book objects, we can construct one
        # using the internal mappings if we exposed them.
        # For now, let's look at `self.normalizer.code_to_n1904` etc.
        name_en = self.normalizer.code_to_n1904.get(book_code)
        if not name_en: return None
        
        return Book(
            code=book_code,
            name_en=name_en,
            name_fr=self.normalizer.n1904_to_tob.get(name_en),
            chapters=0 # TODO: Fetch chapter count from TF
        )

    def get_verse(self, book_code: str, chapter: int, verse: int, version: str) -> Optional[Verse]:
        # Switch based on version strategy
        if version.lower() == "n1904":
            return self._get_n1904_verse(book_code, chapter, verse)
        elif version.lower() == "n1904_en":
            return self._get_n1904_english_verse(book_code, chapter, verse)
        elif version.lower() == "lxx":
            return self._get_lxx_verse(book_code, chapter, verse)
        elif version.lower() == "bhsa":
            return self._get_bhsa_verse(book_code, chapter, verse)
        elif version.lower() == "tob":
            return self._get_tob_verse(book_code, chapter, verse)
        elif version.lower() == "bj":
             return self._get_bj_verse(book_code, chapter, verse)
        elif version.lower() == "nav":
             return self._get_nav_verse(book_code, chapter, verse)
        return None

    def _get_n1904_verse(self, book_code: str, chapter: int, verse: int) -> Optional[Verse]:
        app = self.n1904
        if not app: return None
        
        # Check if valid NT book
        if not self.normalizer.is_nt(book_code): return None
        
        book_name = self.normalizer.code_to_n1904.get(book_code)
        if not book_name: return None
        
        node = app.api.T.nodeFromSection((book_name, chapter, verse))
        if not node or not isinstance(node, int): return None
        
        # Text extraction
        # N1904 is Greek text.
        text = app.api.T.text(node)
            
        return Verse(
            book_code=book_code,
            chapter=chapter,
            verse=verse,
            text=text,
            language=Language.GREEK,
            version="N1904",
            node=node
        )
            
    def _get_n1904_english_verse(self, book_code: str, chapter: int, verse: int) -> Optional[Verse]:
        app = self.n1904
        if not app: return None
        
        # Check if valid NT book
        if not self.normalizer.is_nt(book_code): return None
        
        book_name = self.normalizer.code_to_n1904.get(book_code)
        if not book_name: return None
        
        node = app.api.T.nodeFromSection((book_name, chapter, verse))
        if not node or not isinstance(node, int): return None
        
        # English Gloss extraction
        text_list = []
        words = app.api.L.d(node, otype='word')
        for w in words:
            trans = ""
            if hasattr(app.api.F, 'trans'):
                trans = app.api.F.trans.v(w)
            if not trans and hasattr(app.api.F, 'gloss'):
                trans = app.api.F.gloss.v(w)
            text_list.append(trans or "")
            
        return Verse(
            book_code=book_name, # Use full English name
            chapter=chapter,
            verse=verse,
            text=" ".join(text_list),
            language=Language.ENGLISH,
            version="N1904_EN",
            node=node
        )
        
    # ... (skipping _get_lxx_verse etc) ...

    def _get_nav_verse(self, book_code: str, chapter: int, verse: int) -> Optional[Verse]:
        api = self.nav_api # Need property
        if not self._nav_api and self._nav_provider:
             self._nav_api = self._nav_provider()
        if not self._nav_api: return None
        api = self._nav_api
        
        # NAV uses English Names "Genesis" etc, but prefers "1 Samuel" over "I Samuel"
        # Try code_to_bhsa (e.g. 1_Samuel)
        name_en = self.normalizer.code_to_bhsa.get(book_code)
        if not name_en: 
             name_en = self.normalizer.code_to_n1904.get(book_code)
             
        if not name_en: return None
        
        node = api.T.nodeFromSection((name_en, str(chapter), str(verse)))
        if not node:
             # Try replacing underscore with space (e.g. "1_Samuel" -> "1 Samuel")
             node = api.T.nodeFromSection((name_en.replace("_", " "), str(chapter), str(verse)))
             
        if not node:
             # Fallback to N1904 name if BHSA failed (e.g. maybe some books differ)
             name_alt = self.normalizer.code_to_n1904.get(book_code)
             if name_alt and name_alt != name_en:
                  node = api.T.nodeFromSection((name_alt, str(chapter), str(verse)))
                  if not node:
                       node = api.T.nodeFromSection((name_alt.replace("_", " "), str(chapter), str(verse)))
        
        if not node or not isinstance(node, int): return None
        
        text = api.T.text(node)
        
        # Determine strict display name
        display_name = name_en.replace("_", " ") if name_en else book_code
        
        return Verse(
             book_code=display_name,
             chapter=chapter,
             verse=verse,
             text=text,
             language=Language.ARABIC,
             version="NAV",
             node=node
        )

    # ... (get_chapter dispatch) ...

    def _get_n1904_english_chapter(self, book_code: str, chapter: int) -> List[Verse]:
        app = self.n1904
        if not app: return []
        
        if not self.normalizer.is_nt(book_code): return []
        book_name = self.normalizer.code_to_n1904.get(book_code)
        if not book_name: return []
        
        api = app.api
        node = api.T.nodeFromSection((book_name, chapter))
        
        if node and api.F.otype.v(node) == 'chapter':
             pass 
        else:
             book_node = api.T.nodeFromSection((book_name,))
             if not book_node: return []
             
             node = None
             for ch_node in api.L.d(book_node, otype='chapter'):
                 if api.F.chapter.v(ch_node) == int(chapter):
                     node = ch_node
                     break
        
        if not node: return []
        
        verses = []
        for v_node in api.L.d(node, otype='verse'):
            v_num = api.F.verse.v(v_node)
            
            # English Gloss extraction
            text_list = []
            words = api.L.d(v_node, otype='word')
            for w in words:
                trans = ""
                if hasattr(api.F, 'trans'):
                    trans = api.F.trans.v(w)
                if not trans and hasattr(api.F, 'gloss'):
                    trans = api.F.gloss.v(w)
                text_list.append(trans or "")
            
            verses.append(Verse(
                book_code=book_name, # Use full Name
                chapter=chapter,
                verse=v_num,
                text=" ".join(text_list),
                language=Language.ENGLISH,
                version="N1904_EN",
                node=v_node
            ))
        return verses

    # ... (skip other methods) ...
    
    def _get_nav_chapter(self, book_code: str, chapter: int) -> List[Verse]:
        api = self.nav_api
        if not api: return []
        
        # Try code_to_bhsa (e.g. 1_Samuel)
        name_en = self.normalizer.code_to_bhsa.get(book_code)
        if not name_en: 
             name_en = self.normalizer.code_to_n1904.get(book_code)
        
        if not name_en: return []
        
        node = api.T.nodeFromSection((name_en, str(chapter)))
        if not node:
               node = api.T.nodeFromSection((name_en.replace("_", " "), str(chapter)))
        
        if not node:
             # Fallback to N1904
             name_alt = self.normalizer.code_to_n1904.get(book_code)
             if name_alt and name_alt != name_en:
                  node = api.T.nodeFromSection((name_alt, str(chapter)))
                  if not node:
                       node = api.T.nodeFromSection((name_alt.replace("_", " "), str(chapter)))
        
        if not node or api.F.otype.v(node) != 'chapter':
             return []
             
        verses = []
        display_name = name_en.replace("_", " ") if name_en else book_code
        
        for v_node in api.L.d(node, otype='verse'):
             if hasattr(api.F, 'verse'):
                 v_val = api.F.verse.v(v_node)
             else:
                 v_val = api.T.sectionFromNode(v_node)[2]
             try:
                 v_num = int(v_val)
             except:
                 continue
                 
             text = api.T.text(v_node)
             verses.append(Verse(
                book_code=display_name,
                chapter=chapter,
                verse=v_num,
                text=text,
                language=Language.ARABIC,
                version="NAV",
                node=v_node
             ))
        return verses

    def _get_lxx_verse(self, book_code: str, chapter: int, verse: int) -> Optional[Verse]:
        app = self.lxx
        if not app: return None
        
        # Check if valid OT book (LXX covers OT + Apocrypha)
        if not self.normalizer.is_ot(book_code) and not self.normalizer.is_apocrypha(book_code): 
            # Loose check, proceed if app can find it
            pass

        # LXX apps usually handle nodeFromSectionStr with standard English names or codes
        # Try code first
        ref_str = f"{book_code} {chapter}:{verse}"
        node = None
        
        # The app might be a mock wrapper (see self.lxx property) which has only 'api'.
        # If it's a real TF app, it has nodeFromSectionStr.
        if hasattr(app, 'nodeFromSectionStr'):
             node = app.nodeFromSectionStr(ref_str)
        
        # Try TF API directly: T.nodeFromSection
             # Need correct book name in LXX dataset. 
             # Iterate candidates: abbreviations, spacerless abbreviations, code, english name.
             candidates = []
             
             # 1. Abbreviations
             abbreviations = self.normalizer.code_to_abbreviations.get(book_code, [])
             candidates.extend(abbreviations)
             
             # 2. Spacerless abbreviations
             spacerless = [abbr.replace(" ", "") for abbr in abbreviations if " " in abbr]
             candidates.extend(spacerless)
             
             # 3. Code (e.g. DEU)
             candidates.append(book_code)
             
             # 4. English Name (e.g. Deuteronomy)
             name_en = self.normalizer.code_to_n1904.get(book_code)
             if name_en: candidates.append(name_en)
             
             for cand in candidates:
                 try:
                     candidate_node = app.api.T.nodeFromSection((cand, chapter, verse))
                     if candidate_node and isinstance(candidate_node, int):
                         node = candidate_node
                         break
                 except:
                     continue
             
        if not node: return None

        # Text extraction
        try:
             text = app.api.T.text(node)
        except Exception:
             text = ""
        
        return Verse(
            book_code=book_code,
            chapter=chapter,
            verse=verse,
            text=text,
            language=Language.GREEK,
            version="LXX",
            node=node
        )

    def _get_bhsa_verse(self, book_code: str, chapter: int, verse: int) -> Optional[Verse]:
        app = self.bhsa
        if not app: return None
        
        # BHSA expects specific book names (e.g. "1_Kings" not "I_Kings")
        name_en = self.normalizer.code_to_bhsa.get(book_code, book_code)
        
        node = app.nodeFromSectionStr(f"{name_en} {chapter}:{verse}")
        if not node or not isinstance(node, int): return None
        
        # Text extraction: g_word_utf8
        words = app.api.L.d(node, otype='word')
        text_list = []
        for w in words:
            if hasattr(app.api.F, 'g_word_utf8'):
                 text_list.append(app.api.F.g_word_utf8.v(w))
        
        return Verse(
            book_code=book_code,
            chapter=chapter,
            verse=verse,
            text=" ".join(text_list),
            language=Language.HEBREW,
            version="BHSA",
            node=node
        )

    def _get_tob_verse(self, book_code: str, chapter: int, verse: int) -> Optional[Verse]:
        api = self.tob
        if not api: return None
        
        # TOB uses French Book Names as feature 'book'
        name_en = self.normalizer.code_to_n1904.get(book_code)
        book_fr = self.normalizer.n1904_to_tob.get(name_en) if name_en else None
        
        if not book_fr: return None 
        
        # Optimize: Use nodeFromSection
        node = api.T.nodeFromSection((book_fr, int(chapter), int(verse)))
        
        # Fallback if nodeFromSection failed (e.g. feature mismatch)
        if not node:
             F = api.F
             L = api.L
             for n in F.otype.s('book'):
                 if F.book.v(n) == book_fr:
                     book_node = n
                     for ch_n in L.d(book_node, otype='chapter'):
                         if F.chapter.v(ch_n) == int(chapter):
                             for v_n in L.d(ch_n, otype='verse'):
                                 if F.verse.v(v_n) == int(verse):
                                     node = v_n
                                     break
                             break
                     break

        if not node: return None
        
        try:
            text = api.T.text(node)
        except Exception:
            text = ""

        return Verse(
            book_code=book_code,
            chapter=chapter,
            verse=verse,
            text=text,
            language=Language.FRENCH,
            version="TOB",
            node=node
        )

    def _get_bj_verse(self, book_code: str, chapter: int, verse: int) -> Optional[Verse]:
        api = self.bj_api
        if not api: return None
        F, L = api.F, api.L
        
        # BJ uses CODES as book feature (e.g. "GEN") (Verified by debug script)
        node = api.T.nodeFromSection((book_code, int(chapter), int(verse)))
        
        if not node or not isinstance(node, int): return None

        # Text extraction: Safe T.text
        try:
             text = api.T.text(node)
        except Exception:
             text = ""

        return Verse(
            book_code=book_code,
            chapter=chapter,
            verse=verse,
            text=text,
            language=Language.FRENCH,
            version="BJ",
            node=node
        )

    def _get_nav_verse(self, book_code: str, chapter: int, verse: int) -> Optional[Verse]:
        api = self.nav_api # Need property
        if not self._nav_api and self._nav_provider:
             self._nav_api = self._nav_provider()
        if not self._nav_api: return None
        api = self._nav_api
        
        # NAV uses English Names "Genesis" etc, but prefers "1 Samuel" over "I Samuel"
        # Try code_to_bhsa (e.g. 1_Samuel)
        name_en = self.normalizer.code_to_bhsa.get(book_code)
        if not name_en: 
             name_en = self.normalizer.code_to_n1904.get(book_code)
             
        if not name_en: return None
        
        node = api.T.nodeFromSection((name_en, str(chapter), str(verse)))
        if not node:
             # Try replacing underscore with space (e.g. "1_Samuel" -> "1 Samuel")
             node = api.T.nodeFromSection((name_en.replace("_", " "), str(chapter), str(verse)))
             
        if not node:
             # Fallback to N1904 name if BHSA failed (e.g. maybe some books differ)
             name_alt = self.normalizer.code_to_n1904.get(book_code)
             if name_alt and name_alt != name_en:
                  node = api.T.nodeFromSection((name_alt, str(chapter), str(verse)))
                  if not node:
                       node = api.T.nodeFromSection((name_alt.replace("_", " "), str(chapter), str(verse)))
        
        if not node or not isinstance(node, int): return None
        
        text = api.T.text(node)
        
        display_name = name_en.replace("_", " ") if name_en else book_code
        
        return Verse(
             book_code=display_name,
             chapter=chapter,
             verse=verse,
             text=text,
             language=Language.ARABIC,
             version="NAV",
             node=node
        )

    def find_lemma(self, lemma: str) -> List[Verse]:
        """
        Find all verses containing a specific Greek lemma in the N1904 dataset.
        Counts matches using NFC normalization to handle accent variations (Oxia vs Tonos).
        """
        app = self.n1904
        if not app: return []
        api = app.api
        F, L = api.F, api.L
        
        import unicodedata
        
        # Normalize input
        target = unicodedata.normalize('NFC', lemma)
        
        verse_nodes = set()
        
        # Linear scan for exact lemma match
        # Optimized: pre-normalize or normalize on fly?
        # 140k words. normalize on fly is fine for CLI command (approx 0.2s overhead).
        
        for w in F.otype.s('word'):
            l_raw = F.lemma.v(w)
            # Check Lemma
            if l_raw and unicodedata.normalize('NFC', l_raw) == target:
                v_list = L.u(w, otype='verse')
                if v_list:
                    verse_nodes.add(v_list[0])
                continue

            # Check Surface Text (e.g. "Τεκνία" -> "Τεκνία")
            # T.text(w) usually includes trailing space/punctuation.
            # Convert to NFC and strip for comparison.
            t_raw = api.T.text(w)
            if t_raw:
                 # Remove punctuation if exact match fails?
                 # Often "Word " or "Word,"
                 # Let's strip whitespace and common punctuation
                 t_clean = t_raw.strip().rstrip(",.;·")
                 if unicodedata.normalize('NFC', t_clean) == target:
                     v_list = L.u(w, otype='verse')
                     if v_list:
                         verse_nodes.add(v_list[0])
        
        if not verse_nodes:
            # Fallback: Try searching without accents? (Strip accents)
            # For now, just return empty.
            return []
            
        sorted_nodes = sorted(list(verse_nodes))
        
        results = []
        for v_node in sorted_nodes:
            section = api.T.sectionFromNode(v_node) # (Book, Chapter, Verse)
            book_name, chapter, verse_num = section
            
            # Map N1904 book name to code
            book_code = self.normalizer.n1904_to_code.get(book_name.replace(" ", "_"))
            if not book_code:
                 book_code = self.normalizer.n1904_to_code.get(book_name)
            if not book_code:
                 book_code = book_name
            
            text = api.T.text(v_node)
            
            # Identify matching surface forms for highlighting
            highlights = []
            verse_word_nodes = L.d(v_node, otype='word')
            for w in verse_word_nodes:
                # Check Lemma
                l_raw = F.lemma.v(w)
                is_match = False
                if l_raw and unicodedata.normalize('NFC', l_raw) == target:
                    is_match = True
                
                # Check Surface
                if not is_match:
                    t_raw = api.T.text(w)
                    if t_raw:
                        t_clean = t_raw.strip().rstrip(",.;·")
                        if unicodedata.normalize('NFC', t_clean) == target:
                            is_match = True
                            
                if is_match:
                    highlights.append(api.T.text(w).strip())

            results.append(Verse(
                book_code=book_code,
                chapter=int(chapter),
                verse=int(verse_num),
                text=text,
                language=Language.GREEK,
                version="N1904",
                node=v_node,
                metadata={"highlight_words": list(set(highlights))}
            ))
            
        return results

    def build_stripped_index(self):
        """
        Builds two indices:
        1. stripped_form -> set(lemmas) (Direct fuzzy lookup)
        2. stripped_form -> set(polytonic_surfaces) (For OdyCy restoration)
        """
        if hasattr(self, '_stripped_index') and self._stripped_index:
            return

        api = self.n1904.api
        F = api.F
        T = api.T
        
        from src.utils.greek_normalizer import GreekNormalizer
        
        index = {} # stripped_form -> set(lemmas)
        surface_index = {} # stripped_form -> set(polytonic_surface)
        
        for w in F.otype.s('word'):
            lemma = F.lemma.v(w)
            if not lemma: continue
            
            # --- Index Lemma ---
            stripped_lemma = GreekNormalizer.strip_accents(lemma)
            if stripped_lemma not in index: index[stripped_lemma] = set()
            index[stripped_lemma].add(lemma)
            
            # --- Index Surface Text ---
            # Use raw text but stripped of punctuation
            raw_text = T.text(w).strip()
            # Remove trailing punctuation often found in TF text
            clean_text = raw_text.rstrip(",.;·")
            
            stripped_text = GreekNormalizer.strip_accents(clean_text)
            
            # 1. Map to Lemma
            if stripped_text not in index: index[stripped_text] = set()
            index[stripped_text].add(lemma)
            
            # 2. Map to Polytonic Surface
            if stripped_text not in surface_index: surface_index[stripped_text] = set()
            surface_index[stripped_text].add(clean_text)
            
        self._stripped_index = index
        self._surface_index = surface_index

        # --- Index LXX (Optional Augmentation) ---
        # Scan LXX for additional polytonic surface forms not in N1904
        # This helps with restoration of forms like 'ειλημμένων'
        lxx_app = self.lxx
        if lxx_app:
            try:
                LXX_F = lxx_app.api.F
                LXX_T = lxx_app.api.T
                
                for w in LXX_F.otype.s('word'):
                    # Get Surface
                    raw_text = LXX_T.text(w).strip()
                    clean_text = raw_text.rstrip(",.;·")
                    stripped_text = GreekNormalizer.strip_accents(clean_text)
                    
                    # 2. Map to Polytonic Surface (Add to existing set)
                    if stripped_text not in surface_index: surface_index[stripped_text] = set()
                    surface_index[stripped_text].add(clean_text)
                    
                    # 1. Map to Lemma (If valid lemma exists)
                    # LXX might use 'lex' or 'lemma'
                    lxx_lemma = ""
                    if hasattr(LXX_F, 'lemma'): lxx_lemma = LXX_F.lemma.v(w)
                    elif hasattr(LXX_F, 'lex'): lxx_lemma = LXX_F.lex.v(w)
                        
                    if lxx_lemma:
                         # Normalize lemma too?
                         stripped_lemma = GreekNormalizer.strip_accents(lxx_lemma)
                         
                         if stripped_text not in index: index[stripped_text] = set()
                         index[stripped_text].add(lxx_lemma)
                         
                         if stripped_lemma not in index: index[stripped_lemma] = set()
                         index[stripped_lemma].add(lxx_lemma)
            except Exception:
                # LXX loading is optional/fallible
                pass
        
        # --- Index Supplemental Lexicon (Optional) ---
        # Load manual dataset to cover gaps in N1904/LXX (based on user request for "compressed data")
        # E.g. Missing lemmas like 'εἰλημμένος' -> 'λαμβάνω'
        try:
            import json
            import os
            
            # Locate supplemental_lemmas.json relative to project root
            # adapter is in src/adapters -> src -> root
            # Assume file is in data/lexicons/supplemental_lemmas.json
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            lexicon_path = os.path.join(base_dir, "data", "lexicons", "supplemental_lemmas.json")
            
            # Supplemental Lexicon disabled per user request (focus on OdyCy+Vectors)
            # if os.path.exists(lexicon_path):
            #    print(f"Loading supplements from {lexicon_path}", file=sys.stderr)
            #    with open(lexicon_path, 'r') as f:
            #        supplements = json.load(f)
            #        print(f"Loaded {len(supplements)} supplemental lemmas.", file=sys.stderr)
            #        for surface, lemma in supplements.items():
            #             stripped_surface = GreekNormalizer.strip_accents(surface)
            #             stripped_lemma = GreekNormalizer.strip_accents(lemma)
            #             
            #             # Index Text -> Lemma
            #             if stripped_surface not in index: index[stripped_surface] = set()
            #             index[stripped_surface].add(lemma)
            #             
            #             # Index Lemma -> Lemma (for self-referential check)
            #             if stripped_lemma not in index: index[stripped_lemma] = set()
            #             index[stripped_lemma].add(lemma)
            #             
            #             # Index Polytonic Surface (if surface is polytonic)
            #             # Simple check: if surface not == stripped_surface
            #             if surface != stripped_surface:
            #                 if stripped_surface not in surface_index: surface_index[stripped_surface] = set()
            #                 surface_index[stripped_surface].add(surface)

        except Exception as e:
            # Silent fail for optional data
             pass
             
    def find_lemmas_by_stripped_surface(self, stripped_surface: str) -> set[str]:
        """
        Returns a set of polytonic lemmas that match the given stripped surface form.
        """
        if not hasattr(self, '_stripped_index') or not self._stripped_index:
            self.build_stripped_index()
            
        return self._stripped_index.get(stripped_surface, set())

    def find_polytonic_surfaces(self, stripped_surface: str) -> set:
        """
        Returns a set of actual polytonic surface forms appearing in the text
        that match the given stripped form.
        Useful for restoring accents before feeding to OdyCy.
        """
        if not hasattr(self, '_surface_index') or not self._surface_index:
            self.build_stripped_index()
            
        return self._surface_index.get(stripped_surface, set())

    def get_chapter(self, book_code: str, chapter: int, version: str) -> List[Verse]:
        version = version.upper()
        if version == "N1904":
            return self._get_n1904_chapter(book_code, chapter)
        elif version == "N1904_EN":
            return self._get_n1904_english_chapter(book_code, chapter)
        elif version == "LXX":
            return self._get_lxx_chapter(book_code, chapter)
        elif version == "BHSA":
            return self._get_bhsa_chapter(book_code, chapter)
        elif version == "TOB":
            return self._get_tob_chapter(book_code, chapter)
        elif version == "BJ":
            return self._get_bj_chapter(book_code, chapter)
        elif version == "NAV":
             return self._get_nav_chapter(book_code, chapter)
        return []

    def _get_n1904_chapter(self, book_code: str, chapter: int) -> List[Verse]:
        app = self.n1904
        if not app: return []
        
        if not self.normalizer.is_nt(book_code): return []
        book_name = self.normalizer.code_to_n1904.get(book_code)
        if not book_name: return []
        
        api = app.api
        node = api.T.nodeFromSection((book_name, chapter))
        
        if node and api.F.otype.v(node) == 'chapter':
             pass 
        else:
             book_node = api.T.nodeFromSection((book_name,))
             if not book_node: return []
             
             node = None
             for ch_node in api.L.d(book_node, otype='chapter'):
                 if api.F.chapter.v(ch_node) == int(chapter):
                     node = ch_node
                     break
        
        if not node: return []
        
        verses = []
        for v_node in api.L.d(node, otype='verse'):
            v_num = api.F.verse.v(v_node)
            text = api.T.text(v_node)
            verses.append(Verse(
                book_code=book_code,
                chapter=chapter,
                verse=v_num,
                text=text,
                language=Language.GREEK,
                version="N1904",
                node=v_node
            ))
        return verses

    def _get_n1904_english_chapter(self, book_code: str, chapter: int) -> List[Verse]:
        app = self.n1904
        if not app: return []
        
        if not self.normalizer.is_nt(book_code): return []
        book_name = self.normalizer.code_to_n1904.get(book_code)
        if not book_name: return []
        
        api = app.api
        node = api.T.nodeFromSection((book_name, chapter))
        
        if node and api.F.otype.v(node) == 'chapter':
             pass 
        else:
             book_node = api.T.nodeFromSection((book_name,))
             if not book_node: return []
             
             node = None
             for ch_node in api.L.d(book_node, otype='chapter'):
                 if api.F.chapter.v(ch_node) == int(chapter):
                     node = ch_node
                     break
        
        if not node: return []
        
        verses = []
        for v_node in api.L.d(node, otype='verse'):
            v_num = api.F.verse.v(v_node)
            
            # English Gloss extraction
            text_list = []
            words = api.L.d(v_node, otype='word')
            for w in words:
                trans = ""
                if hasattr(api.F, 'trans'):
                    trans = api.F.trans.v(w)
                if not trans and hasattr(api.F, 'gloss'):
                    trans = api.F.gloss.v(w)
                text_list.append(trans or "")
            
            verses.append(Verse(
                book_code=book_name, # Use full Name
                chapter=chapter,
                verse=v_num,
                text=" ".join(text_list),
                language=Language.ENGLISH,
                version="N1904_EN",
                node=v_node
            ))
        return verses

    def _get_lxx_chapter(self, book_code: str, chapter: int) -> List[Verse]:
        app = self.lxx
        if not app: return []
        
        node = None
        ref_str = f"{book_code} {chapter}"
        
        if hasattr(app, 'nodeFromSectionStr'):
             try:
                 node = app.nodeFromSectionStr(ref_str)
             except: pass
             
             if not node or not isinstance(node, int) or app.api.F.otype.v(node) != 'chapter':
                  # Invalid previous attempt, reset node
                  node = None
                  
                  name_en = self.normalizer.code_to_n1904.get(book_code)
                  if name_en:
                       try:
                           n = app.nodeFromSectionStr(f"{name_en} {chapter}")
                           if n and isinstance(n, int):
                               # Only assign if int, and check otype
                               if app.api.F.otype.v(n) == 'chapter':
                                   node = n
                       except: pass

        if not node:
             candidates = []
             abbreviations = self.normalizer.code_to_abbreviations.get(book_code, [])
             candidates.extend(abbreviations)
             candidates.append(book_code)
             name_en = self.normalizer.code_to_n1904.get(book_code)
             if name_en: candidates.append(name_en)
             
             for cand in candidates:
                 try:
                     n = app.api.T.nodeFromSection((cand, chapter))
                     if n and app.api.F.otype.v(n) == 'chapter':
                         node = n
                         break
                 except: continue
        
        if not node: return []
        
        verses = []
        for v_node in app.api.L.d(node, otype='verse'):
            v_num = app.api.F.verse.v(v_node)
            text = app.api.T.text(v_node)
            verses.append(Verse(
                book_code=book_code,
                chapter=chapter,
                verse=v_num,
                text=text,
                language=Language.GREEK,
                version="LXX",
                node=v_node
            ))
        return verses

    def _get_bhsa_chapter(self, book_code: str, chapter: int) -> List[Verse]:
        app = self.bhsa
        if not app: return []
        
        name_en = self.normalizer.code_to_bhsa.get(book_code, book_code)
        node = app.nodeFromSectionStr(f"{name_en} {chapter}")
        
        if not node or app.api.F.otype.v(node) != 'chapter':
             return []
             
        verses = []
        for v_node in app.api.L.d(node, otype='verse'):
            v_num = app.api.F.verse.v(v_node)
            words = app.api.L.d(v_node, otype='word')
            text_list = []
            for w in words:
                if hasattr(app.api.F, 'g_word_utf8'):
                     text_list.append(app.api.F.g_word_utf8.v(w))
            
            verses.append(Verse(
                book_code=book_code,
                chapter=chapter,
                verse=v_num,
                text=" ".join(text_list),
                language=Language.HEBREW,
                version="BHSA",
                node=v_node
            ))
        return verses

    def _get_nav_chapter(self, book_code: str, chapter: int) -> List[Verse]:
        api = self.nav_api
        if not api: return []
        
        # Try code_to_bhsa (e.g. 1_Samuel)
        name_en = self.normalizer.code_to_bhsa.get(book_code)
        if not name_en: 
             name_en = self.normalizer.code_to_n1904.get(book_code)
        
        if not name_en: return []
        
        node = api.T.nodeFromSection((name_en, str(chapter)))
        if not node:
               node = api.T.nodeFromSection((name_en.replace("_", " "), str(chapter)))
        
        if not node:
             # Fallback to N1904
             name_alt = self.normalizer.code_to_n1904.get(book_code)
             if name_alt and name_alt != name_en:
                  node = api.T.nodeFromSection((name_alt, str(chapter)))
                  if not node:
                       node = api.T.nodeFromSection((name_alt.replace("_", " "), str(chapter)))
        
        if not node or api.F.otype.v(node) != 'chapter':
             return []
             
        verses = []
        display_name = name_en.replace("_", " ") if name_en else book_code
        
        for v_node in api.L.d(node, otype='verse'):
             if hasattr(api.F, 'verse'):
                 v_val = api.F.verse.v(v_node)
             else:
                 v_val = api.T.sectionFromNode(v_node)[2]
             try:
                 v_num = int(v_val)
             except:
                 continue
                 
             text = api.T.text(v_node)
             verses.append(Verse(
                book_code=display_name,
                chapter=chapter,
                verse=v_num,
                text=text,
                language=Language.ARABIC,
                version="NAV",
                node=v_node
             ))
        return verses


    def _get_tob_chapter(self, book_code: str, chapter: int) -> List[Verse]:
        api = self.tob
        if not api: return []
        
        name_en = self.normalizer.code_to_n1904.get(book_code)
        book_fr = self.normalizer.n1904_to_tob.get(name_en) if name_en else None
        if not book_fr: return []

        # Find Chapter Node
        # T.nodeFromSection usually returns Verse if fully specified, 
        # or Chapter if (Book, Chapter) specified?
        # It depends on sectionFeatures config. 
        # If TOB sectionFeatures=book,chapter,verse, then (Book, Chapter) usually returns Chapter node.
        node = api.T.nodeFromSection((book_fr, int(chapter)))
        
        # Verify it is a chapter
        if not node or api.F.otype.v(node) != 'chapter':
             # Fallback to finding book then chapter?
             # Optimization: Assuming nodeFromSection works. 
             # If it returns None, maybe try finding book node first?
             # But let's assume standard behavior for now.
             
             # Fallback: Loop books (Linear scan 1 time is OK if nodeFromSection fails)
             book_node = None
             for n in api.F.otype.s('book'):
                 if api.F.book.v(n) == book_fr:
                     book_node = n
                     break
             if not book_node: return []
             
             for n in api.L.d(book_node, otype='chapter'):
                 if api.F.chapter.v(n) == int(chapter):
                     node = n
                     break
        
        if not node: return []

        verses = []
        for v_node in api.L.d(node, otype='verse'):
             v_num = api.F.verse.v(v_node)
             text = api.T.text(v_node)
             
             verses.append(Verse(
                book_code=book_code,
                chapter=chapter,
                verse=v_num,
                text=text,
                language=Language.FRENCH,
                version="TOB",
                node=v_node
            ))
        return verses

    def _get_bj_chapter(self, book_code: str, chapter: int) -> List[Verse]:
        api = self.bj_api
        if not api: return []
        
        node = api.T.nodeFromSection((book_code, int(chapter)))
        
        if not node or api.F.otype.v(node) != 'chapter':
             return []

        verses = []
        for v_node in api.L.d(node, otype='verse'):
             v_num = api.F.verse.v(v_node)
             text = api.T.text(v_node)
             
             verses.append(Verse(
                book_code=book_code,
                chapter=chapter,
                verse=v_num,
                text=text,
                language=Language.FRENCH,
                version="BJ",
                node=v_node
            ))
        return verses

    def search(self, query: str, version: str) -> List[Verse]:
        return []

    def get_cross_references(self, book_code: str, chapter: int, verse: int) -> VerseCrossReferences:
        # This requires access to the ReferenceDatabase logic.
        # Ideally ReferenceDatabase should be injected or its logic ported.
        # For now, let's assume we can inject a cross_ref_provider or ref_db.
        # But wait, ReferenceHandler has the database.
        # The Adapter is a Port.
        # If we stick to Clean Arch, CrossRef logic (which is data) should be in an Adapter?
        # Or is ReferenceDatabase itself an Adapter? Yes, it loads JSON.
        
        # We can implement a simple version if we have the JSON data.
        # But `ReferenceDatabase` class does complex parsing.
        # For this step, I will return an empty list or placeholder until we decide to migrate ReferenceDatabase fully.
        # See Implementation Plan: "Implement CrossReference fetching in Adapter".
        
        return VerseCrossReferences(notes=[], relations=[])
