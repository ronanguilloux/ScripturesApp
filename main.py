import sys
import argparse
from tf.app import use
from tf.fabric import Fabric

# TOB Configuration
TOB_DIR = 'tob_tf/TOB/TraductionOecumenique/1.0'
try:
    TF_TOB = Fabric(locations=[TOB_DIR], silent=True)
    API_TOB = TF_TOB.load('text book chapter verse')
except Exception as e:
    print(f"Warning: Could not load TOB corpus: {e}")
    API_TOB = None

# Mapping from N1904 (English) to TOB (French) book names
N1904_TO_TOB = {
    "Matthew": "Matthieu",
    "Mark": "Marc",
    "Luke": "Luc",
    "John": "Jean",
    "Acts": "Actes des Apôtres",
    "Romans": "Romains",
    "1_Corinthians": "1 Corinthiens",
    "2_Corinthians": "2 Corinthiens",
    "Galatians": "Galates",
    "Ephesians": "Éphésiens",
    "Philippians": "Philippiens",
    "Colossians": "Colossiens",
    "1_Thessalonians": "1 Thessaloniciens",
    "2_Thessalonians": "2 Thessaloniciens",
    "1_Timothy": "1 Timothée",
    "2_Timothy": "2 Timothée",
    "Titus": "Tite",
    "Philemon": "Philémon",
    "Hebrews": "Hébreux",
    "James": "Jacques",
    "1_Peter": "1 Pierre",
    "2_Peter": "2 Pierre",
    "1_John": "1 Jean",
    "2_John": "2 Jean",
    "3_John": "3 Jean",
    "Jude": "Jude",
    "Revelation": "Apocalypse"
}

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

    
def handle_reference(A, ref_str, show_english=False):
    api = A.api
    T = api.T
    F = api.F
    L = api.L

    # Normalize reference
    ref_str = ref_str.replace(',', ':')
    
    # Book abbreviations
    ABBREVIATIONS = {
        "Mt": "Matthew",
        "Matthieu": "Matthew",
        "Mc": "Mark",
        "Mk": "Mark",
        "Marc": "Mark",
        "Lk": "Luke",
        "Lc": "Luke",
        "Luc": "Luke",
        "Jn": "John",
        "Jean": "John"
    }
    
    # Check if reference starts with any abbreviation
    parts = ref_str.split()
    if parts:
        book_abbr = parts[0]
        if book_abbr in ABBREVIATIONS:
            # Replace abbreviation with full book name
            ref_str = f"{ABBREVIATIONS[book_abbr]} {' '.join(parts[1:])}"
    
    # print(f"Searching for: {ref_str}")

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
                        print(f"\n{book_fr} {chapter}:{start_v}-{end_v}")
                    else:
                        print(f"\n{book_chapter}:{start_v}-{end_v}")
                    
                    for v_num in range(start_v, end_v + 1):
                        single_ref = f"{book_chapter}:{v_num}"
                        node = A.nodeFromSectionStr(single_ref)
                        
                        if node:
                            print_verse(A, node, show_english)
                        else:
                            print(f"Could not find verse: {single_ref}")
                    return

        # Fallback to single reference lookup
        node = A.nodeFromSectionStr(ref_str)
        
        if node:
            print_verse(A, node, show_english)
        else:
            print(f"Could not find reference: {ref_str}")
            
    except Exception as e:
        print(f"Error processing reference: {e}")

def print_verse(A, node, show_english=False):
    api = A.api
    T = api.T
    F = api.F
    L = api.L
    
    # Print reference
    section = T.sectionFromNode(node)
    book_en = section[0]
    chapter = section[1]
    verse = section[2]
    book_fr= N1904_TO_TOB.get(book_en)
    
    print(f"\n{book_fr} {chapter}:{verse}")

    # Greek text
    greek_text = T.text(node)
    print(f"{greek_text}")
    
    # English translation
    if show_english:
        words = L.d(node, otype='word')
        english_text = []
        for w in words:
            trans = F.trans.v(w) if hasattr(F, 'trans') else ""
            if not trans and hasattr(F, 'gloss'):
                trans = F.gloss.v(w)
            english_text.append(trans)
        print(f"{' '.join(english_text)}")
    
    # French translation (TOB)
    french_text = get_french_text(book_en, chapter, verse)
    if french_text:
        print(f"{french_text}")

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

def main():
    parser = argparse.ArgumentParser(description="N1904 CLI Tool")
    parser.add_argument("command_or_ref", help="Command (e.g., 'search', 'list') or Bible reference (e.g., 'Mk 1,1')")
    parser.add_argument("args", nargs="*", help="Arguments for the command")
    parser.add_argument("--tr", nargs="+", choices=["en"], help="Translations to display (e.g., 'en')")
    args = parser.parse_args()

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
    print(f"Loading N1904 data... (this may take a while on first run)")
    try:
        A = use("CenterBLC/N1904", version="1.0.0", silent=True)
    except Exception as e:
        print(f"Error loading N1904: {e}")
        sys.exit(1)

    show_english = False
    if args.tr and "en" in args.tr:
        show_english = True

    handle_reference(A, first_arg, show_english)


if __name__ == "__main__":
    main()
