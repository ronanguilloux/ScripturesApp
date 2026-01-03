import os
import zipfile
import re
import json
from html.parser import HTMLParser
import sys

# Configuration
EPUB_DIR = 'tmp/BJ-EPUB-to-Text-Fabric/OEBPS' # Relative to workspace root
OUTPUT_DIR = 'output/brand_new_bj/1.0'
BIBLE_BOOKS_JSON = 'data/bible_books.json'

# Load Bible Books Mapping
def load_book_mapping():
    with open(BIBLE_BOOKS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    mapping = {}
    for code, info in data.get('books', {}).items():
        # Map BJ French label to Code
        if 'fr' in info and 'bj' in info['fr']:
            mapping[info['fr']['bj']] = code
        # Also map standard French label just in case
        if 'fr' in info and 'label' in info['fr']:
             mapping[info['fr']['label']] = code
    return mapping

BOOK_NAME_TO_CODE = load_book_mapping()

# HTML Parser
class SpineParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.spine = []
        self.manifest = {}
        self.in_manifest = False
        self.in_spine = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'manifest':
            self.in_manifest = True
        elif tag == 'spine':
            self.in_spine = True
        
        if self.in_manifest and tag == 'item':
            self.manifest[attrs_dict.get('id')] = attrs_dict.get('href')
        
        if self.in_spine and tag == 'itemref':
            idref = attrs_dict.get('idref')
            if idref in self.manifest:
                self.spine.append(self.manifest[idref])

class BibleParser(HTMLParser):
    def __init__(self, book_mapping):
        super().__init__()
        self.book_mapping = book_mapping
        
        # State
        self.tag_stack = []
        self.current_book_code = None 
        self.current_chapter = 0
        self.current_verse = 0
        self.valid_book_section = False # Only true if under a recognized H3 book header

        # Data collection
        self.words = [] # list of (text, book, chapter, verse) tuples
        
        # Verse heuristic state
        self.last_verse_num = 0

    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)

    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return

        # Header detection
        # Check if 'h3' is in stack (anywhere, or usually parent)
        # In <h3 ...><a></a>Text</h3>, stack when seeing Text is ['html', 'body', 'h3']
        
        if 'h3' in self.tag_stack:
            # Potential Book Title
            # Note: We might see multiple data chunks.
            # "La Genèse"
            
            code = self.get_book_code(text)
            if code:
                print(f"  [Parser] Found Book: {text} -> {code}")
                self.current_book_code = code
                self.valid_book_section = True
                self.current_chapter = 0
                self.current_verse = 0
                self.last_verse_num = 0
            else:
                # If H3 is encountered but NOT a recognized book (e.g. "Notes", "Collection Title")
                # we must invalidate the section to prevent phantom verses.
                if self.valid_book_section:
                     print(f"  [Parser] Closing Section: {text} (Not a book)")
                self.valid_book_section = False
                self.current_book_code = None
                self.current_chapter = 0
                self.current_verse = 0
                self.last_verse_num = 0
            
        elif 'h4' in self.tag_stack:
            # Chapter
            if self.valid_book_section:
                # "Genèse 1"
                # Regex for "1"
                # Be careful of "Genèse 1, 1" if it appears in H4? No, usually just title.
                m = re.search(r'(\d+)$', text)
                if m:
                    new_ch = int(m.group(1))
                    # Only update if meaningful change? 
                    self.current_chapter = new_ch
                    self.current_verse = 0
                    self.last_verse_num = 0
                    # print(f"    [Chapter] {self.current_chapter}")
        
        elif 'p' in self.tag_stack or 'span' in self.tag_stack:
            # Text content
            # Ensure we are not in 'a' tag (footnotes?)?
            # BJ EPUB has footnotes in 'a' tags or separate?
            # If 'a' is in stack, maybe ignore ref markers like "a", "b"?
            # Let's inspect content later. For now, capture all.
            if self.valid_book_section and self.current_chapter > 0:
                self.process_paragraph_text(text)

    def get_book_code(self, text):
        # Normalize text: remove NBSP and multiple spaces
        norm_text = ' '.join(text.replace('\xa0', ' ').split())
        
        if norm_text in self.book_mapping:
            return self.book_mapping[norm_text]
        return None

    def process_paragraph_text(self, text):
        # Fix: Trailing headers like "Marc 1, 2" being included as text.
        # Check against current Book Name.
        # We need the Book Name string... but we only have code self.current_book_code.
        # But we can try to match the pattern generically or using a lookup if needed.
        # Actually, the pattern is fairly consistent: BookName Chapter, VerseNum Text...
        # The "BookName" part matches what was in the H3 or H4 header usually.
        
        # Regex to strip navigation prefix:
        # Pattern: ^ [Non-digits]+ [Digit]+ , [Digit]+
        prefix_pattern = r'^\s*([^\d]+?)\s+(\d+)\s*,\s*(\d+)'
        match = re.match(prefix_pattern, text)
        if match:
             # Logic to verify it matches current context?
             # ch = int(match.group(2))
             # vs = int(match.group(3))
             # if ch == self.current_chapter: ...
             # For safety, let's just strip it if it looks like a navigation header.
             # In BJ EPUB, these are navigation crumbs.
             text = re.sub(r'^\s*[^\d]+?\s+\d+\s*,\s*', '', text, count=1)
             
             # Additional fix: Split joined verse number (e.g. "2les" -> "2 les")
             # Only if it starts with the verse number we expect (digits followed by non-digit/non-space)
             if re.match(r'^\d+[^\d\s]', text):
                  text = re.sub(r'^(\d+)([^\d\s])', r'\1 \2', text, count=1)

        # Split by space, preserve some punctuation for "words"?
        # TF "word" usually includes punctuation or is just the alphanumeric?
        # Standard: Words are alphanumeric (+), punctuation is separate or attached as feature.
        # Simple approach: Split by whitespace. Stick tokens as "words". 
        
        # Verse detection logic
        # We scan tokens. If token is number matching sequence, update verse.
        
        tokens = text.replace('’', "'").split()
        
        for token in tokens:
            # Check if token is a verse number
            # Heuristic: must be digit
            if token.isdigit():
                val = int(token)
                # Sequential check
                # Accept 1 if last was 0.
                # Accept val if val == last + 1.
                if val == self.last_verse_num + 1:
                    self.last_verse_num = val
                    self.current_verse = val
                    continue # Do not emit verse number as word
                elif val == 1 and self.last_verse_num == 0:
                    self.last_verse_num = 1
                    self.current_verse = 1
                    continue
            
            # Emit word
            # Only if we are inside a verse
            if self.current_verse > 0:
                self.words.append({
                    'text': token,
                    'book': self.current_book_code,
                    'chapter': self.current_chapter,
                    'verse': self.current_verse
                })


def write_tf_files(words):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 1. Nodes
    # Word nodes: 1 .. len(words)
    # Book, Chapter, Verse nodes follow.
    
    word_count = len(words)
    print(f"Total Words: {word_count}")
    
    # Structure: Collect ranges
    # Books: { "GEN": [start_node, end_node], ... }
    # Chapters: { ("GEN", 1): [start_node, end_node], ... }
    # Verses: { ("GEN", 1, 1): [start_node, end_node], ... }
    
    # Since we process sequentially, we can track boundaries.
    
    books = {} # (code) -> {slots: []} -- actually just min/max slot
    chapters = {} # (code, ch) -> {min, max}
    verses = {} # (code, ch, v) -> {min, max}
    
    # Single pass to determine ranges
    curr_node = 0
    
    for i, w in enumerate(words):
        curr_node = i + 1
        b_code = w['book']
        ch_num = w['chapter']
        v_num = w['verse']
        
        # Book
        if b_code not in books: books[b_code] = {'min': curr_node, 'max': curr_node}
        books[b_code]['max'] = curr_node
        
        # Chapter
        ch_key = (b_code, ch_num)
        if ch_key not in chapters: chapters[ch_key] = {'min': curr_node, 'max': curr_node}
        chapters[ch_key]['max'] = curr_node
        
        # Verse
        v_key = (b_code, ch_num, v_num)
        if v_key not in verses: verses[v_key] = {'min': curr_node, 'max': curr_node}
        verses[v_key]['max'] = curr_node

    # Calculate Node Offsets
    # Node 1..word_count : Word
    
    # Additional Nodes
    # Order: Books, Chapters, Verses (or any order, but let's be structured)
    
    # Let's assign IDs
    # Books
    book_node_start = word_count + 1
    book_nodes_data = [] # (node_id, book_code, min_w, max_w)
    sorted_books = sorted(books.keys(), key=lambda k: list(books.keys()).index(k)) # Keep insertion order
    
    curr = book_node_start
    for b in sorted_books:
        book_nodes_data.append( {'id': curr, 'book': b, 'min': books[b]['min'], 'max': books[b]['max']} )
        curr += 1
    
    # Chapters
    chapter_node_start = curr
    chapter_nodes_data = []
    # Sort keys
    # To keep document order, we can rely on python dict order if >= 3.7
    for k in chapters:
        chapter_nodes_data.append( {'id': curr, 'book': k[0], 'chapter': k[1], 'min': chapters[k]['min'], 'max': chapters[k]['max'] } )
        curr += 1
        
    # Verses
    verse_node_start = curr
    verse_nodes_data = []
    for k in verses:
        verse_nodes_data.append( {'id': curr, 'book': k[0], 'chapter': k[1], 'verse': k[2], 'min': verses[k]['min'], 'max': verses[k]['max']} )
        curr += 1
        
    max_node = curr - 1
    
    # Write Files
    
    # otype.tf
    with open(os.path.join(OUTPUT_DIR, 'otype.tf'), 'w', encoding='utf-8') as f:
        f.write("@node\n@valueType=str\n@writtenBy=Antigravity\n@date=2026\n@name=Bible de Jerusalem\n\n")
        f.write(f"1-{word_count}\tword\n")
        f.write(f"{book_node_start}-{chapter_node_start-1}\tbook\n")
        f.write(f"{chapter_node_start}-{verse_node_start-1}\tchapter\n")
        f.write(f"{verse_node_start}-{max_node}\tverse\n")

    # oslots.tf
    # Maps non-slot nodes to slots.
    # Note: TF edge files usually have values. If edgeValues=false, the value column IS the target node(s).
    # Since oslots maps to words (slots), the values are ints?
    # But oslots doesn't need valueType matching the target.
    # It seems 'str cannot be interpreted as int' might be due to a weird line.
    
    with open(os.path.join(OUTPUT_DIR, 'oslots.tf'), 'w', encoding='utf-8') as f:
        f.write("@edge\n@valueType=str\n@edgeValues=false\n@writtenBy=Antigravity\n\n")
        
        # Books
        for d in book_nodes_data:
            f.write(f"{d['id']}\t{d['min']}-{d['max']}\n")
        # Chapters
        for d in chapter_nodes_data:
             f.write(f"{d['id']}\t{d['min']}-{d['max']}\n")
        # Verses
        for d in verse_nodes_data:
             f.write(f"{d['id']}\t{d['min']}-{d['max']}\n")

    # Features: text, book, chapter, verse
    
    # text.tf (words)
    with open(os.path.join(OUTPUT_DIR, 'text.tf'), 'w', encoding='utf-8') as f:
         f.write("@node\n@valueType=str\n@writtenBy=Antigravity\n@language=fr\n@tier0\n\n")
         for w in words:
             safe_text = w['text'].replace('\n', ' ').replace('\t', ' ')
             f.write(f"{safe_text}\n")
             
    # book.tf
    with open(os.path.join(OUTPUT_DIR, 'book.tf'), 'w', encoding='utf-8') as f:
        f.write("@node\n@valueType=str\n@writtenBy=Antigravity\n\n")
        
        last_b = None
        start = 1
        for i, w in enumerate(words):
            curr_node = i + 1
            if w['book'] != last_b:
                if last_b is not None:
                     f.write(f"{start}-{curr_node-1}\t{last_b}\n")
                last_b = w['book']
                start = curr_node
        f.write(f"{start}-{word_count}\t{last_b}\n")
        
        for d in book_nodes_data:
            f.write(f"{d['id']}\t{d['book']}\n")
        for d in chapter_nodes_data:
            f.write(f"{d['id']}\t{d['book']}\n")
        for d in verse_nodes_data:
            f.write(f"{d['id']}\t{d['book']}\n")
            
    # chapter.tf
    with open(os.path.join(OUTPUT_DIR, 'chapter.tf'), 'w', encoding='utf-8') as f:
        f.write("@node\n@valueType=int\n@writtenBy=Antigravity\n\n")
        
        last_c = None
        start = 1
        for i, w in enumerate(words):
            curr_node = i + 1
            if w['chapter'] != last_c:
                if last_c is not None:
                     f.write(f"{start}-{curr_node-1}\t{last_c}\n")
                last_c = w['chapter']
                start = curr_node
        f.write(f"{start}-{word_count}\t{last_c}\n")
        
        for d in chapter_nodes_data:
            f.write(f"{d['id']}\t{d['chapter']}\n")
        for d in verse_nodes_data:
            f.write(f"{d['id']}\t{d['chapter']}\n")

    # verse.tf
    with open(os.path.join(OUTPUT_DIR, 'verse.tf'), 'w', encoding='utf-8') as f:
        f.write("@node\n@valueType=int\n@writtenBy=Antigravity\n\n")
        
        last_v = None
        start = 1
        for i, w in enumerate(words):
            curr_node = i + 1
            if w['verse'] != last_v:
                if last_v is not None:
                     f.write(f"{start}-{curr_node-1}\t{last_v}\n")
                last_v = w['verse']
                start = curr_node
        f.write(f"{start}-{word_count}\t{last_v}\n")
        
        for d in verse_nodes_data:
            f.write(f"{d['id']}\t{d['verse']}\n")
            
    # otext.tf (config)
    with open(os.path.join(OUTPUT_DIR, 'otext.tf'), 'w', encoding='utf-8') as f:
        # Standard config
        f.write("@config\n@fmt:text-orig-full={text} \n@sectionTypes=book,chapter,verse\n@sectionFeatures=book,chapter,verse\n\n")

    print(f"TF Files generated in {OUTPUT_DIR}")


def parse_bj_epub():
    # 1. Parse Spine
    spine_parser = SpineParser()
    opf_path = os.path.join(EPUB_DIR, 'content.opf')
    if not os.path.exists(opf_path):
        # Maybe it's not in OEBPS directly or named differently?
        # User file listing showed `OEBPS/content.opf`.
        pass
    
    with open(opf_path, 'r', encoding='utf-8') as f:
        spine_parser.feed(f.read())
        
    print(f"Detected {len(spine_parser.spine)} spine items.")
    
    # 2. Parse Content
    parser = BibleParser(BOOK_NAME_TO_CODE)
    
    for item_href in spine_parser.spine:
        # href is relative to content.opf usually.
        # Check standard EPUB structure.
        # "Text/PL1.xhtml".
        
        path = os.path.join(EPUB_DIR, item_href)
        # Handle cases where href is url encoded (%20)
        # Should be fine for BJ.
        if not os.path.exists(path):
            print(f"Skipping missing file: {path}")
            continue
            
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Feed parser
            # We must be careful that `feed` doesn't reset total state if we used a single parser instance?
            # Start tag handling works. 
            parser.feed(content)
            
    # 3. Write TF
    write_tf_files(parser.words)

if __name__ == '__main__':
    parse_bj_epub()
