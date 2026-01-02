import sys
import argparse
from tf.app import use
from tf.fabric import Fabric
import os
import contextlib

# Import new DB module
from book_normalizer import BookNormalizer
from references_db import ReferenceDatabase
from verse_printer import VersePrinter
from reference_handler import ReferenceHandler
from cli_help import CLIHelp

# Configuration
# Determine project root relative to this script (src/main.py -> ..)
BIBLECLI_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOB_DIR = os.path.expanduser("~/text-fabric-data/TOB/1.0/")

# Initialize Managers
DATA_DIR = os.path.join(BIBLECLI_DIR, "data")
normalizer = BookNormalizer(DATA_DIR)
ref_db = ReferenceDatabase(DATA_DIR, normalizer)

# TOB Lazy Load
_tob_api_instance = None
_tob_loaded = False

def get_tob_app():
    global _tob_api_instance, _tob_loaded
    if _tob_loaded:
         return _tob_api_instance
    
    _tob_loaded = True
    try:
        with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
            TF_TOB = Fabric(locations=[TOB_DIR], silent=True)
            _tob_api_instance = TF_TOB.load('text book chapter verse', silent=True)
    except Exception as e:
        _tob_api_instance = None
    return _tob_api_instance

# Global Printer (initialized in main or dynamically)
printer = None

class OfflineLXXApp:
    def __init__(self, api, normalizer):
        self.api = api
        self.normalizer = normalizer
        # LXX app expects specific book names (e.g. "2Kgs")
        # These are now handled via aliases in bible_books.json
        # The normalizer's `get_lxx_abbr` method is used to retrieve the correct abbreviation.
        
    def nodeFromSectionStr(self, ref_str):
        # We need to parse ref_str -> Book, Chapter, Verse
        # ReferenceHandler typically passes things like "Genesis 1:1"
        try:
            # Use normalizer to get code
            norm = self.normalizer.normalize_reference(ref_str)
            if not norm:
                return None
            
            code, ch, vs, _ = norm
            
            # LXX uses strict book names. We need to find the one that works.
            # We try all candidates from the abbreviations list.
            candidates = []
            
            # Get all abbreviations (canonical is first)
            abbreviations = self.normalizer.code_to_abbreviations.get(code, [])
            candidates.extend(abbreviations)
            
            # Also try spacerless versions of abbreviations (e.g. "2 Sam" -> "2Sam")
            # This is important because we removed redundant spacerless aliases from JSON
            # but TF might require the spacerless version (e.g. "2Sam").
            spacerless = [abbr.replace(" ", "") for abbr in abbreviations if " " in abbr]
            candidates.extend(spacerless)
            
            # Code itself (fallback)
            candidates.append(code)

            # Try candidates until one returns a node.
            for abbr in candidates:
                # API expects string for book name in section tuple
                if vs > 0:
                     node = self.api.T.nodeFromSection((abbr, ch, vs))
                elif ch > 0:
                     node = self.api.T.nodeFromSection((abbr, ch))
                else:
                     node = self.api.T.nodeFromSection((abbr,))
                
                # Check if valid node returned (TF returns None or sometimes 0 if not found?)
                # nodeFromSection usually returns None if not found, or a node int.
                if node:
                    return node
            
            return None
            
        except Exception as e:
            # print(f"OfflineLXX lookup error: {e}")
            return None


class OfflineBHSAApp:
    def __init__(self, api, normalizer):
        self.api = api
        self.normalizer = normalizer

    def nodeFromSectionStr(self, ref_str):
        # Similar to LXX, we need to map normalize reference to BHSA book format
        try:
            norm = self.normalizer.normalize_reference(ref_str)
            if not norm: return None
            
            code, ch, vs, _ = norm
            
            # Get BHSA book label
            bhsa_book = self.normalizer.code_to_bhsa.get(code)
            if not bhsa_book: return None
            
            if vs > 0:
                 node = self.api.T.nodeFromSection((bhsa_book, ch, vs))
            elif ch > 0:
                 node = self.api.T.nodeFromSection((bhsa_book, ch))
            else:
                 node = self.api.T.nodeFromSection((bhsa_book,))
            return node
            
        except Exception:
            return None

def handle_list(A, args):
    api = A.api
    F = api.F
    N = api.N
    
    if not args:
        print("Error: Missing argument for 'list'. Available: 'books'")
        return

    subcommand = args[0]
    
    if subcommand == "books":
        print("Available books:")
        for node in N.walk():
            if F.otype.v(node) == 'book':
                print(F.book.v(node))
    else:
        print(f"Unknown list command: {subcommand}")

def handle_add(args):
    # args matches the structure added in main: collection, source, target, type, note
    try:
        ref_db.add_relation(
            collection_name=args.collection,
            source_ref=args.source,
            target_ref=args.target,
            rel_type=args.type,
            note=args.note
        )
        print(f"Successfully added reference to {args.collection}:")
        print(f"  Source: {args.source}")
        print(f"  Target: {args.target}")
        print(f"  Type:   {args.type}")
        print(f"  Note:   {args.note}")
    except ValueError as e:
        print(f"Error adding reference: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

# Lazy Load N1904
_n1904_app_instance = None
_n1904_loaded = False

def get_n1904_app():
    global _n1904_app_instance, _n1904_loaded
    if _n1904_loaded:
         return _n1904_app_instance
    
    _n1904_loaded = True
    try:
         with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
              # use returns an App instance
              _n1904_app_instance = use("CenterBLC/N1904", version="1.0.0", silent=True)
    except Exception as e:
         _n1904_app_instance = None
    return _n1904_app_instance

# Lazy Load LXX
_lxx_app_instance = None
_lxx_loaded = False

def get_lxx_app():
    global _lxx_app_instance, _lxx_loaded
    if _lxx_loaded:
        return _lxx_app_instance
        
    _lxx_loaded = True
    try:
        with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
             # Load LXX (Manual Offline Priority)
            lxx_path = os.path.expanduser("~/text-fabric-data/github/CenterBLC/LXX/tf/1935")
            if os.path.exists(lxx_path):
                 try:
                     # We need to manually construct the API similar to 'use' but offline
                     # 'use' returns an app object which wraps the API.
                     # Our OfflineLXXApp wraps the API.
                     # So we just need the API.
                     TF_LXX = Fabric(locations=[lxx_path])
                     API_LXX = TF_LXX.load("", silent=True) # Load default features
                     # Previous code used load("", silent=True).
                     # But let's follow safety.
                     _lxx_app_instance = OfflineLXXApp(API_LXX, normalizer)
                 except Exception:
                     _lxx_app_instance = None
            else:
                 # Try online as fallback (unlikely to work if rate limited)
                 try:
                     # 'use' returns the App object directly. BUT our OfflineLXXApp expects an API object?
                     # Wait, 'use' returns an App. 
                     # Our specific logic uses 'OfflineLXXApp' to override nodeFromSectionStr.
                     # If we get a standard App from 'use', we might need to wrap its API?
                     # Or just use the App if it works. 
                     # But for consistency, let's just stick to our Offline wrapper if possible,
                     # or wrap the app.api.
                     LXX_tf_app = use("CenterBLC/LXX", version="1935", check=False, silent=True)
                     if LXX_tf_app:
                         _lxx_app_instance = OfflineLXXApp(LXX_tf_app.api, normalizer)
                 except Exception:
                     _lxx_app_instance = None
    except Exception as e:
        # print(f"Error lazy loading LXX: {e}")
        _lxx_app_instance = None
        
    return _lxx_app_instance

# Lazy Load BHSA
_bhsa_app_instance = None
_bhsa_loaded = False

def get_bhsa_app():
    global _bhsa_app_instance, _bhsa_loaded
    if _bhsa_loaded:
         return _bhsa_app_instance
    
    _bhsa_loaded = True
    try:
         with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
              # use 'ETCBC/bhsa'
              # We might want to use offline path if possible, but 'use' is robust.
              # Let's try 'use' first.
              bhsa = use("ETCBC/bhsa", version="2021", silent=True)
              if bhsa:
                  _bhsa_app_instance = OfflineBHSAApp(bhsa.api, normalizer)
    except Exception as e:
         _bhsa_app_instance = None
         
    return _bhsa_app_instance

def main():
    parser = argparse.ArgumentParser(description="N1904 CLI Tool", add_help=False)
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message and exit")
    
    # We use a subparser strategy or manual parse to handle "add" vs valid refs
    # Beacuse "add" has specific required args, let's peek at argv[1]
    
    if len(sys.argv) > 1 and sys.argv[1] == "add":
        # Sub-parser for add command
        add_parser = argparse.ArgumentParser(description="Add reference")
        add_parser.add_argument("command", choices=["add"])
        add_parser.add_argument("-c", "--collection", required=True, help="Collection name (e.g. nt_ronan)")
        add_parser.add_argument("-s", "--source", required=True, help="Source reference (e.g. 'Mc 1:1')")
        add_parser.add_argument("-t", "--target", required=True, help="Target reference (e.g. 'Lc 1:1')")
        add_parser.add_argument("--type", default="other", help="Relation type (parallel, allusion, quotation, other)")
        add_parser.add_argument("-n", "--note", default="", help="Note for the relation")
        
        args = add_parser.parse_args(sys.argv[1:])
        handle_add(args)
        return

    # Standard parser for other commands
    parser.add_argument("command_or_ref", nargs="?", help="Command or Bible reference")
    parser.add_argument("args", nargs="*", help="Arguments for the command")
    parser.add_argument("-t", "--tr", nargs="+", choices=["en", "fr", "gr", "hb"], help="Translations")
    parser.add_argument("-c", "--crossref", action="store_true", help="Display cross-references")
    parser.add_argument("-f", "--crossref-full", action="store_true", help="Display cross-references with text")
    parser.add_argument("-s", "--source", help="Filter cross-references by source")
    
    args = parser.parse_args()

    if args.help or not args.command_or_ref:
        CLIHelp().print_usage()
        return

    first_arg = args.command_or_ref
    
    if first_arg == "search":
        print("done.")
        return
    
    if first_arg == "list":
        app = get_n1904_app()
        if not app:
            print("Error: Could not load N1904 for listing commands.")
            sys.exit(1)
        
        handle_list(app, args.args)
        return



    show_english = False
    show_greek = True
    show_hebrew = True # Default enabled (controlled by handler)
    show_french = True
    
    # Initialize global printer
    global printer
    printer = VersePrinter(get_tob_app, get_n1904_app, normalizer, ref_db, get_bhsa_app)
    
    # Initialize Handler with Lazy Provider
    handler = ReferenceHandler(get_n1904_app, get_lxx_app, get_bhsa_app, normalizer, printer)
    
    if args.tr:
        # Reset provided defaults if explicit flags used
        show_english = False
        show_french = False
        show_greek = False
        show_hebrew = False
        
        if "en" in args.tr: show_english = True
        if "fr" in args.tr: show_french = True
        if "gr" in args.tr: show_greek = True
        if "hb" in args.tr: show_hebrew = True
        
    cross_refs = None
    show_crossref = args.crossref or args.crossref_full
    if show_crossref:
        book_key = first_arg.split()[0]
        if book_key in ["1", "2", "3", "I", "II", "III"]:
             parts = first_arg.split()
             if len(parts) > 1:
                 book_key = f"{parts[0]} {parts[1]}"
        
        resolved = normalizer.abbreviations.get(book_key, book_key)
        book_code = normalizer.n1904_to_code.get(resolved) or normalizer.n1904_to_code.get(resolved.replace(" ", "_"))
        
        ref_db.load_all(source_filter=args.source)
        cross_refs = ref_db.in_memory_refs

    handler.handle_reference(first_arg, show_english, show_greek, show_french, show_crossref, cross_refs, args.crossref_full, show_hebrew)

if __name__ == "__main__":
    main()
