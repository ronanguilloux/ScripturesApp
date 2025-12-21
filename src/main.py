import sys
import argparse
from tf.app import use
from tf.fabric import Fabric

# TOB Configuration
BIBLECLI_DIR="/Users/ronan/Documents/Gemini/antigravity/biblecli"
TOB_DIR = BIBLECLI_DIR+'/tob_tf/TOB/TraductionOecumenique/1.0'
try:
    import os
    import contextlib
    with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
        TF_TOB = Fabric(locations=[TOB_DIR], silent=True)
        API_TOB = TF_TOB.load('text book chapter verse', silent=True)
except Exception as e:
    API_TOB = None

# Mappings populated from data/cross_booknames_fr.json
N1904_TO_TOB = {}
N1904_TO_CODE = {}
CODE_TO_FR_ABBR = {}
CODE_TO_N1904 = {}
ABBREVIATIONS = {}
BOOK_ORDER = {} # Maps book code (e.g. "GEN") to its index in TOB order

def load_book_mappings():
    global N1904_TO_TOB, N1904_TO_CODE, ABBREVIATIONS, CODE_TO_FR_ABBR, CODE_TO_N1904, BOOK_ORDER
    import json
    import os
    path = os.path.join(BIBLECLI_DIR, "data", "cross_booknames_fr.json")
    if not os.path.exists(path):
        return
    try:
        with open(path, "r") as f:
            data = json.load(f)
        books = data.get("books", {})
        for i, (code, info) in enumerate(books.items()):
            BOOK_ORDER[code] = i
            en_info = info.get("en", {})
            en_label = en_info.get("label")
            en_abbr = en_info.get("abbr")
            
            # Internal N1904 key (uses Roman numerals for numbered books)
            en_key = en_label if en_label else ""
            if en_key.startswith("1 "): en_key = "I_" + en_key[2:]
            elif en_key.startswith("2 "): en_key = "II_" + en_key[2:]
            elif en_key.startswith("3 "): en_key = "III_" + en_key[2:]
            en_key = en_key.replace(" ", "_")
            
            fr = info.get("fr", {})
            fr_label = fr.get("label")
            fr_abbr = fr.get("abbr")
            
            if en_key:
                N1904_TO_TOB[en_key] = fr_label
                N1904_TO_CODE[en_key] = code
                CODE_TO_FR_ABBR[code] = fr_abbr
                CODE_TO_N1904[code] = en_key
                
                # Register English variations
                ABBREVIATIONS[en_key] = en_key
                ABBREVIATIONS[code] = en_key # e.g. JHN -> John
                if en_label: ABBREVIATIONS[en_label] = en_key
                if en_abbr: 
                    ABBREVIATIONS[en_abbr] = en_key
                    # Also register without space for numbered books (e.g. 1Cor)
                    if " " in en_abbr:
                        ABBREVIATIONS[en_abbr.replace(" ", "")] = en_key
                
            # Register French variations
            if fr_abbr: 
                ABBREVIATIONS[fr_abbr] = en_key
                if " " in fr_abbr:
                    ABBREVIATIONS[fr_abbr.replace(" ", "")] = en_key
            if fr_label: ABBREVIATIONS[fr_label] = en_key
            
        # Common English extras (fallbacks)
        for k, v in {"Mk": "Mark", "Lk": "Luke", "Jn": "John"}.items():
            if k not in ABBREVIATIONS: ABBREVIATIONS[k] = v
    except Exception as e:
        print(f"Warning: Could not load book mappings: {e}")

load_book_mappings()

OT_BOOKS_CODE = [
    "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA",
    "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO",
    "ECC", "SNG", "ISA", "JER", "LAM", "EZE", "DAN", "HOS", "JOE", "AMO",
    "OBA", "JON", "MIC", "NAH", "HAB", "ZEP", "HAG", "ZEC", "MAL"
]

def load_cross_references(book_code):
    import json
    import os
    
    filename = "references_nt_openbible.json"
    if book_code in OT_BOOKS_CODE:
        filename = "references_ot_openbible.json"
        
    path = os.path.join(BIBLECLI_DIR, "data", filename)
    if not os.path.exists(path):
        # Fallback to the monolithic file if it still exists (for transition)
        path = os.path.join(BIBLECLI_DIR, "data", "references_openbible.json")
        if not os.path.exists(path):
            return {}
            
    try:
        with open(path, "r") as f:
            data = json.load(f)
        indexed = {}
        for entry in data.get("cross_references", []):
            indexed[entry["source"]] = entry["relations"]
        return indexed
    except Exception as e:
        print(f"Warning: Could not load cross-references: {e}")
        return {}

def get_french_text(book_en, chapter_num, verse_num):
    if not API_TOB:
        return ""
        
    F = API_TOB.F
    L = API_TOB.L
    
    book_fr = N1904_TO_TOB.get(book_en)
    if not book_fr:
        # Try direct mapping if not found (e.g. if N1904 uses spaces instead of underscores)
        book_fr = N1904_TO_TOB.get(book_en.replace(" ", "_"))
        
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

def format_ref_fr(target_str):
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
            fr_abbr = CODE_TO_FR_ABBR.get(book_code, book_code)
            return fr_abbr, chapter, verse
        return None, None, None

    if "-" in target_str:
        ranges = target_str.split("-")
        if len(ranges) == 2:
            start_ref = ranges[0]
            end_ref = ranges[1]
            
            s_abbr, s_ch, s_vs = parse_one(start_ref)
            e_abbr, e_ch, e_vs = parse_one(end_ref)
            
            if s_abbr:
                if s_abbr == e_abbr and s_ch == e_ch:
                    return f"{s_abbr} {s_ch}:{s_vs}-{e_vs}"
                elif s_abbr == e_abbr:
                    return f"{s_abbr} {s_ch}:{s_vs}-{e_ch}:{e_vs}"
                else:
                    return f"{s_abbr} {s_ch}:{s_vs}-{e_abbr} {e_ch}:{e_vs}"
    
    abbr, ch, vs = parse_one(target_str)
    if abbr:
        return f"{abbr} {ch}:{vs}"
        
    return target_str

    
def handle_reference(A, ref_str, show_english=False, show_greek=True, show_french=True, show_crossref=False, cross_refs=None, show_crossref_text=False):
    api = A.api
    T = api.T
    F = api.F
    L = api.L

    # Normalize reference
    ref_str = ref_str.replace(',', ':')
    
    # Book abbreviations are now global
    global ABBREVIATIONS
    
    # Check if reference starts with any abbreviation
    # Check for abbreviation (can be 1 or 2 words, e.g. "Jn" or "1 Cor")
    parts = ref_str.split()
    if len(parts) >= 2:
        two_word_abbr = f"{parts[0]} {parts[1]}"
        if two_word_abbr in ABBREVIATIONS:
            ref_str = f"{ABBREVIATIONS[two_word_abbr]} {' '.join(parts[2:])}"
            parts = ref_str.split() # refresh parts
        elif parts[0] in ABBREVIATIONS:
            ref_str = f"{ABBREVIATIONS[parts[0]]} {' '.join(parts[1:])}"
            parts = ref_str.split() # refresh parts
    elif len(parts) == 1:
        if parts[0] in ABBREVIATIONS:
            ref_str = ABBREVIATIONS[parts[0]]
            parts = [ref_str]

    try:
        # Check if it's a range (e.g., "Luke 1:4-7")
        if "-" in ref_str and ":" in ref_str:
            # Assume format "Book Chapter:Start-End"
            last_colon_idx = ref_str.rfind(":")
            if last_colon_idx != -1:
                book_chapter = ref_str[:last_colon_idx]
                verses_part = ref_str[last_colon_idx+1:]
                
                if "-" in verses_part:
                    start_v, end_v = verses_part.split("-")
                    start_v = int(start_v)
                    end_v = int(end_v)
                    
                    # Try to separate book and chapter for clearer output
                    if ' ' in book_chapter:
                        book, chapter = book_chapter.rsplit(' ', 1)
                        book_fr= N1904_TO_TOB.get(book)
                        if not book_fr: book_fr = book
                        print(f"\n{book_fr} {chapter}:{start_v}-{end_v}")
                    else:
                        book = book_chapter
                        chapter = ""
                        print(f"\n{book_chapter}:{start_v}-{end_v}")
                    
                    for v_num in range(start_v, end_v + 1):
                        single_ref = f"{book_chapter}:{v_num}"
                        node = A.nodeFromSectionStr(single_ref)
                        if node and isinstance(node, int):
                            print_verse(A, node=node, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text)
                        else:
                            # Fallback for OT or missing verses
                            if ' ' in book_chapter:
                                b, c = book_chapter.rsplit(' ', 1)
                                print_verse(A, book_en=b, chapter=c, verse=v_num, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text)
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
                    
                    # Find all verses in this chapter
                    book_fr = N1904_TO_TOB.get(book_name)
                    if not book_fr: book_fr = book_name
                    print(f"\n{book_fr} {chapter_num}")
                    
                    # Find the chapter node
                    chapter_nodes = [n for n in F.otype.s('chapter') 
                                    if F.book.v(n) == book_name and F.chapter.v(n) == chapter_num]
                    
                    if chapter_nodes:
                        chapter_node = chapter_nodes[0]
                        # Get all verse nodes in this chapter
                        verse_nodes = L.d(chapter_node, otype='verse')
                        
                        for verse_node in verse_nodes:
                            print_verse(A, node=verse_node, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text)
                        return
                    else:
                        # Fallback for OT: we don't know number of verses, so we look them up until failure
                        if API_TOB:
                            v = 1
                            found_any = False
                            while True:
                                txt = get_french_text(book_name, chapter_num, v)
                                if (not txt or txt.startswith("[TOB:")) and v > 1:
                                    break
                                if txt and not txt.startswith("[TOB:"):
                                    print_verse(A, book_en=book_name, chapter=chapter_num, verse=v, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text)
                                    found_any = True
                                v += 1
                            if found_any: return
                        
                        print(f"Could not find chapter: {ref_str}")
                        return
                except ValueError:
                    pass  # Not a valid chapter number, continue to fallback
        
        # Fallback to single reference lookup
        node = A.nodeFromSectionStr(ref_str)
        
        if node and isinstance(node, int):
            print_verse(A, node=node, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text)
        else:
            # Final attempt: manual parse for single verse (e.g. "Is 40:3")
            if ":" in ref_str and " " in ref_str:
                parts = ref_str.rsplit(' ', 1)
                book_name = parts[0]
                if ":" in parts[1]:
                    ch_v = parts[1].split(":")
                    if len(ch_v) == 2:
                        try:
                            ch = int(ch_v[0])
                            vs = int(ch_v[1])
                            print_verse(A, book_en=book_name, chapter=ch, verse=vs, show_english=show_english, show_greek=show_greek, show_french=show_french, show_crossref=show_crossref, cross_refs=cross_refs, show_crossref_text=show_crossref_text)
                            return
                        except ValueError:
                            pass

            print(f"Could not find reference: {ref_str}")
            
    except Exception as e:
        import traceback
        # print(f"DEBUG: ref_str='{ref_str}'")
        print(f"Error processing reference: {e}")
        # traceback.print_exc()

def print_verse(A, node=None, book_en=None, chapter=None, verse=None, show_english=False, show_greek=True, show_french=True, show_crossref=False, cross_refs=None, show_crossref_text=False):
    api = A.api
    T = api.T
    F = api.F
    L = api.L
    
    if node:
        section = T.sectionFromNode(node)
        book_en = section[0]
        chapter = int(section[1])
        verse = int(section[2])
    else:
        # manual values provided
        chapter = int(chapter)
        verse = int(verse)

    book_fr = N1904_TO_TOB.get(book_en)
    if not book_fr:
        book_fr = N1904_TO_TOB.get(book_en.replace(" ", "_"))
    if not book_fr:
        book_fr = book_en
    
    # Header
    if node:
        print(f"\n{book_fr} {chapter}:{verse}")
    else:
        # Only print header if manual (loop handles chapter header elsewhere)
        # But for consistency, let's print it here too if not already printed.
        # Actually handle_reference prints headers for ranges.
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
        french_text = get_french_text(book_en, chapter, verse)
        if french_text and not french_text.startswith("[TOB:"):
            print(f"{french_text}")
        elif french_text and node: # Only print if it was expected (node exists)
             print(f"{french_text}")

    # Cross-references
    if show_crossref:
        print("––––––––––––––––––––––––––––––––––")
        groups = {"Parallel": [], "Allusion": [], "Quotation": [], "Other": []}
        
        if cross_refs:
            book_code = N1904_TO_CODE.get(book_en) or N1904_TO_CODE.get(book_en.replace(" ", "_"))
            if book_code:
                source_key = f"{book_code}.{chapter}.{verse}"
                relations = cross_refs.get(source_key, [])
                
                def sort_key(rel):
                    target = rel.get("target", "")
                    t_book = target.split(".")[0] if "." in target else ""
                    order = BOOK_ORDER.get(t_book, 999)
                    try:
                        parts = target.split(".")
                        ch = int(parts[1]) if len(parts) > 1 else 0
                        vs = int(parts[2].split("-")[0]) if len(parts) > 2 else 0
                        return (order, ch, vs)
                    except (ValueError, IndexError):
                        return (order, 0, 0)

                relations.sort(key=sort_key)
                for rel in relations:
                    rel_type = rel.get("type", "other")
                    target = rel.get("target", "")
                    target_fr = format_ref_fr(target)
                    if rel_type == "parallel": groups["Parallel"].append((target, target_fr))
                    elif rel_type == "allusion": groups["Allusion"].append((target, target_fr))
                    elif rel_type == "quotation": groups["Quotation"].append((target, target_fr))
                    else: groups["Other"].append((target, target_fr))

        for label, items in groups.items():
            if items:
                print(f"    {label}: ")
                for target_raw, target_fr in items:
                    print(f"        {target_fr}")
                    if show_crossref_text:
                        refs_to_fetch = []
                        if "-" in target_raw:
                            parts = target_raw.split("-")
                            if len(parts) == 2:
                                start_p = parts[0].split(".")
                                end_p = parts[1].split(".")
                                if len(start_p) == 3 and len(end_p) == 3:
                                    b_code = start_p[0]
                                    ch = int(start_p[1])
                                    s_v = int(start_p[2])
                                    e_v = int(end_p[2])
                                    for v in range(s_v, e_v + 1):
                                        refs_to_fetch.append((b_code, ch, v))
                        else:
                            parts = target_raw.split(".")
                            if len(parts) == 3:
                                refs_to_fetch.append((parts[0], int(parts[1]), int(parts[2])))
                        
                        for b_code, ch, vs in refs_to_fetch:
                            b_en = CODE_TO_N1904.get(b_code)
                            if b_en:
                                txt = get_french_text(b_en, ch, vs)
                                if txt: print(f"            {txt}")
            else:
                print(f"    {label}: ")

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

def print_help():
    help_text = """
GNT(1)                       Bible CLI Manual                       GNT(1)

NAME
       biblecli - A command-line interface for the Greek New Testament (N1904)

SYNOPSIS
       biblecli [COMMAND | REFERENCE] [ARGS...] [OPTIONS]

DESCRIPTION
       biblecli is a tool for reading and searching the Greek New Testament (N1904)
       along with English and French (TOB) translations.

COMMANDS
       list books
              List all available books in the N1904 dataset.

       search [QUERY] (Coming soon)
              Search for specific terms in the New Testament.

REFERENCES
       References can be specified in various formats:
       - Single verse: "Jn 1:1" or "Jean 1:1"
       - Verse range: "Mt 5:1-10"
       - Whole chapter: "Mk 4"

       Abbreviations like Mt, Mc, Mk, Lk, Lc, Jn are supported.

OPTIONS
       -h, --help
              Show this help message and exit.

       -t, --tr [en|fr|gr]
              Specify which translations to display.
              en: English
              fr: French (TOB) - only
              gr: Greek (N1904) - only

       -c, --crossref
              Display cross-references at verse level.

       -f, --crossref-full
              Display cross-references with related verse text.

EXAMPLES
       Display John 1:1 in Greek and French:
               biblecli "Jn 1:1"

       Display Matthew 5:1-10:
               biblecli "Mt 5:1-10"

       Display Mark chapter 4 in Greek only:
               biblecli "Mk 4" -t gr

       Display John 1:1 with cross-references:
               biblecli "Jn 1:1" --crossref

       List all books:
               biblecli list books

AUTHOR
       Written by Ronan Guilloux and the Gemini Team.
"""
    print(help_text)

def main():
    parser = argparse.ArgumentParser(description="N1904 CLI Tool", add_help=False)
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message and exit")
    parser.add_argument("command_or_ref", nargs="?", help="Command (e.g., 'search', 'list') or Bible reference (e.g., 'Mk 1,1')")
    parser.add_argument("args", nargs="*", help="Arguments for the command")
    parser.add_argument("-t", "--tr", nargs="+", choices=["en", "fr", "gr"], help="Translations to display: 'en' (English), 'fr' (French only), 'gr' (Greek only)")
    parser.add_argument("-c", "--crossref", action="store_true", help="Display cross-references")
    parser.add_argument("-f", "--crossref-full", action="store_true", help="Display cross-references with verse text")
    args = parser.parse_args()

    if args.help or not args.command_or_ref:
        print_help()
        return

    # Determine if first argument is a command or a reference
    first_arg = args.command_or_ref
    
    if first_arg == "search":
        print("done.")
        return
    
    if first_arg == "list":
        # Load TF for list command
       #  print(f"Loading N1904 data... (this may take a while on first run)")
        try:
            A = use("CenterBLC/N1904", version="1.0.0", silent=True)
        except Exception as e:
            print(f"Error loading N1904: {e}")
            sys.exit(1)
        
        handle_list(A, args.args)
        return

    # If not a command, treat as reference (load TF)
    try:
        import os
        import contextlib
        with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
            A = use("CenterBLC/N1904", version="1.0.0", silent=True)
    except Exception as e:
        print(f"Error loading N1904: {e}")
        sys.exit(1)

    show_english = False
    show_greek = True
    show_french = True
    
    if args.tr:
        if "en" in args.tr:
            show_english = True
        if "fr" in args.tr:
            # Show only French
            show_greek = False
            show_french = True
        if "gr" in args.tr:
            # Show only Greek
            show_greek = True
            show_french = False

    cross_refs = None
    show_crossref = args.crossref or args.crossref_full
    if show_crossref:
        # Extract book from first_arg to determine OT/NT
        book_key = first_arg.split()[0]
        # Handle "1 Cor", "2 Sam", etc.
        if book_key in ["1", "2", "3", "I", "II", "III"]:
            parts = first_arg.split()
            if len(parts) > 1:
                book_key = f"{parts[0]} {parts[1]}"
        
        # Normalize/resolve abbreviation
        resolved = ABBREVIATIONS.get(book_key, book_key)
        book_code = N1904_TO_CODE.get(resolved) or N1904_TO_CODE.get(resolved.replace(" ", "_"))
        
        cross_refs = load_cross_references(book_code)

    handle_reference(A, first_arg, show_english, show_greek, show_french, show_crossref, cross_refs, args.crossref_full)


if __name__ == "__main__":
    main()

