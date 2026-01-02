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

# TOB Configuration
BIBLECLI_DIR="/Users/ronan/Documents/Gemini/antigravity/biblecli"
TOB_DIR = BIBLECLI_DIR+'/tob_tf/TOB/TraductionOecumenique/1.0'

# Initialize Managers
DATA_DIR = os.path.join(BIBLECLI_DIR, "data")
normalizer = BookNormalizer(DATA_DIR)
ref_db = ReferenceDatabase(DATA_DIR, normalizer)

try:
    with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
        TF_TOB = Fabric(locations=[TOB_DIR], silent=True)
        API_TOB = TF_TOB.load('text book chapter verse', silent=True)
except Exception as e:
    API_TOB = None

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
    parser.add_argument("-t", "--tr", nargs="+", choices=["en", "fr", "gr"], help="Translations")
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
        try:
            A = use("CenterBLC/N1904", version="1.0.0", silent=True)
        except Exception as e:
            print(f"Error loading N1904: {e}")
            sys.exit(1)
        
        handle_list(A, args.args)
        return

    # Load TF
    try:
        with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
            A = use("CenterBLC/N1904", version="1.0.0", silent=True)
            
            # Load LXX (Manual Offline Priority)
            lxx_path = os.path.expanduser("~/text-fabric-data/github/CenterBLC/LXX/tf/1935")
            if os.path.exists(lxx_path):
                 try:
                     TF_LXX = Fabric(locations=[lxx_path])
                     API_LXX = TF_LXX.load("", silent=True)
                     LXX = OfflineLXXApp(API_LXX, normalizer)
                 except Exception:
                     LXX = None
            else:
                 # Try online as fallback (unlikely to work if rate limited)
                 try:
                     LXX = use("CenterBLC/LXX", version="1935", check=False, silent=True)
                 except Exception:
                     LXX = None

    except Exception as e:
        print(f"Error loading apps (N1904/LXX): {e}")
        sys.exit(1)

    show_english = False
    show_greek = True
    show_french = True
    
    # Initialize global printer
    # Initialize global printer
    global printer
    printer = VersePrinter(API_TOB, A, LXX, normalizer, ref_db)
    
    # Initialize Handler
    handler = ReferenceHandler(A, LXX, normalizer, printer)
    
    if args.tr:
        if "en" in args.tr: show_english = True
        if "fr" in args.tr: show_greek = False; show_french = True
        if "gr" in args.tr: show_greek = True; show_french = False

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

    handler.handle_reference(first_arg, show_english, show_greek, show_french, show_crossref, cross_refs, args.crossref_full)

if __name__ == "__main__":
    main()
