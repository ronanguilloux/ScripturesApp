import os
import re
import json
from html.parser import HTMLParser
import sys

# Configuration
TOB_INPUT_DIR = 'epubs/input/TOB/OPS' # Path to unzipped OPS folder
OUTPUT_DIR = 'epubs/output/TOB/1.0'
BIBLE_BOOKS_JSON = 'data/bible_books.json'

# Mapping of TOB file prefixes to Book Codes
# Based on ls -R output
TOB_PREFIX_TO_CODE = {
    'Gen': 'GEN', 'Exod': 'EXO', 'Lev': 'LEV', 'Num': 'NUM', 'Deut': 'DEU',
    'Josh': 'JOS', 'Judg': 'JDG', 'Ruth': 'RUT', '1Sam': '1SA', '2Sam': '2SA',
    '1Kgs': '1KI', '2Kgs': '2KI', '1Chr': '1CH', '2Chr': '2CH', 'Ezra': 'EZR',
    'Neh': 'NEH', 'Tob': 'TOB', 'Jdt': 'JDT', 'Esth': 'EST', '1Macc': '1MA',
    '2Macc': '2MA', 'Job': 'JOB', 'Ps': 'PSA', 'Prov': 'PRO', 'Eccl': 'ECC',
    'Song': 'SNG', 'Wis': 'WIS', 'Sir': 'SIR', 'Isa': 'ISA', 'Jer': 'JER',
    'Lam': 'LAM', 'Bar': 'BAR', 'Ezek': 'EZK', 'Dan': 'DAN', 'Hos': 'HOS',
    'Joel': 'JOL', 'Amos': 'AMO', 'Obad': 'OBA', 'Jonah': 'JON', 'Mic': 'MIC',
    'Nah': 'NAM', 'Hab': 'HAB', 'Zeph': 'ZEP', 'Hag': 'HAG', 'Zech': 'ZEC',
    'Mal': 'MAL',
    'Matt': 'MAT', 'Mark': 'MRK', 'Luke': 'LUK', 'John': 'JHN', 'Acts': 'ACT',
    'Rom': 'ROM', '1Cor': '1CO', '2Cor': '2CO', 'Gal': 'GAL', 'Eph': 'EPH',
    'Phil': 'PHP', 'Col': 'COL', '1Thess': '1TH', '2Thess': '2TH', '1Tim': '1TI',
    '2Tim': '2TI', 'Titus': 'TIT', 'Phlm': 'PHM', 'Heb': 'HEB', 'Jas': 'JAS',
    '1Pet': '1PE', '2Pet': '2PE', '1John': '1JN', '2John': '2JN', '3John': '3JN',
    'Jude': 'JUD', 'Rev': 'REV'
}

class TOBParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.words = []
        self.current_book = None
        self.current_chapter = 0
        self.current_verse = 0
        self.display_ref_depth = 0
        self.in_note_link = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag == 'span' and attrs_dict.get('class') == 'displayReference':
            self.display_ref_depth += 1
        elif self.display_ref_depth > 0 and tag == 'span':
            self.display_ref_depth += 1
        
        # Verse Detection: <a class="verse" id="vGen.1.1"></a>
        if tag == 'a' and attrs_dict.get('class') == 'verse':
            verse_id = attrs_dict.get('id', '')
            # Match vBook.Ch.Vs
            match = re.match(r'v([^.]+)\.(\d+)\.(\d+)', verse_id)
            if match:
                abbr = match.group(1)
                self.current_book = TOB_PREFIX_TO_CODE.get(abbr, abbr.upper())
                self.current_chapter = int(match.group(2))
                self.current_verse = int(match.group(3))
        
        if tag == 'a' and attrs_dict.get('class') == 'note-link-in-text':
            self.in_note_link = True

    def handle_endtag(self, tag):
        if tag == 'span' and self.display_ref_depth > 0:
            self.display_ref_depth -= 1
        if tag == 'a':
            self.in_note_link = False

    def handle_data(self, data):
        if self.display_ref_depth > 0 or self.in_note_link:
            return
            
        text = data.strip()
        if not text or not self.current_book or self.current_chapter == 0 or self.current_verse == 0:
            return
            
        # Split text into words
        tokens = text.replace('’', "'").split()
        for t in tokens:
            self.words.append({
                'text': t,
                'book': self.current_book,
                'chapter': self.current_chapter,
                'verse': self.current_verse
            })

def write_tf_files(words):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    word_count = len(words)
    print(f"Total Words: {word_count}")
    
    books = {} 
    chapters = {} 
    verses = {} 
    
    curr_node = 0
    for i, w in enumerate(words):
        curr_node = i + 1
        b_code = w['book']
        ch_num = w['chapter']
        v_num = w['verse']
        
        if b_code not in books: books[b_code] = {'min': curr_node, 'max': curr_node}
        books[b_code]['max'] = curr_node
        
        ch_key = (b_code, ch_num)
        if ch_key not in chapters: chapters[ch_key] = {'min': curr_node, 'max': curr_node}
        chapters[ch_key]['max'] = curr_node
        
        v_key = (b_code, ch_num, v_num)
        if v_key not in verses: verses[v_key] = {'min': curr_node, 'max': curr_node}
        verses[v_key]['max'] = curr_node

    # Order preserved via dict insertion order
    book_node_start = word_count + 1
    book_nodes_data = [] 
    curr = book_node_start
    for b in books:
        book_nodes_data.append( {'id': curr, 'book': b, 'min': books[b]['min'], 'max': books[b]['max']} )
        curr += 1
    
    chapter_node_start = curr
    chapter_nodes_data = []
    for k in chapters:
        chapter_nodes_data.append( {'id': curr, 'book': k[0], 'chapter': k[1], 'min': chapters[k]['min'], 'max': chapters[k]['max'] } )
        curr += 1
        
    verse_node_start = curr
    verse_nodes_data = []
    for k in verses:
        verse_nodes_data.append( {'id': curr, 'book': k[0], 'chapter': k[1], 'verse': k[2], 'min': verses[k]['min'], 'max': verses[k]['max']} )
        curr += 1
        
    max_node = curr - 1
    
    # otype.tf
    with open(os.path.join(OUTPUT_DIR, 'otype.tf'), 'w', encoding='utf-8') as f:
        f.write("@node\n@valueType=str\n@writtenBy=Antigravity\n@date=2026\n@name=Traduction Oecumenique de la Bible\n\n")
        f.write(f"1-{word_count}\tword\n")
        f.write(f"{book_node_start}-{chapter_node_start-1}\tbook\n")
        f.write(f"{chapter_node_start}-{verse_node_start-1}\tchapter\n")
        f.write(f"{verse_node_start}-{max_node}\tverse\n")

    # oslots.tf
    with open(os.path.join(OUTPUT_DIR, 'oslots.tf'), 'w', encoding='utf-8') as f:
        f.write("@edge\n@valueType=str\n@edgeValues=false\n@writtenBy=Antigravity\n\n")
        for d in book_nodes_data: f.write(f"{d['id']}\t{d['min']}-{d['max']}\n")
        for d in chapter_nodes_data: f.write(f"{d['id']}\t{d['min']}-{d['max']}\n")
        for d in verse_nodes_data: f.write(f"{d['id']}\t{d['min']}-{d['max']}\n")

    # text.tf
    with open(os.path.join(OUTPUT_DIR, 'text.tf'), 'w', encoding='utf-8') as f:
         f.write("@node\n@valueType=str\n@writtenBy=Antigravity\n@language=fr\n@tier0\n\n")
         for w in words:
             f.write(f"{w['text']}\n")
             
    # book.tf
    with open(os.path.join(OUTPUT_DIR, 'book.tf'), 'w', encoding='utf-8') as f:
        f.write("@node\n@valueType=str\n@writtenBy=Antigravity\n\n")
        for d in book_nodes_data: f.write(f"{d['id']}\t{d['book']}\n")
        for d in chapter_nodes_data: f.write(f"{d['id']}\t{d['book']}\n")
        for d in verse_nodes_data: f.write(f"{d['id']}\t{d['book']}\n")
            
    # chapter.tf
    with open(os.path.join(OUTPUT_DIR, 'chapter.tf'), 'w', encoding='utf-8') as f:
        f.write("@node\n@valueType=int\n@writtenBy=Antigravity\n\n")
        for d in chapter_nodes_data: f.write(f"{d['id']}\t{d['chapter']}\n")
        for d in verse_nodes_data: f.write(f"{d['id']}\t{d['chapter']}\n")

    # verse.tf
    with open(os.path.join(OUTPUT_DIR, 'verse.tf'), 'w', encoding='utf-8') as f:
        f.write("@node\n@valueType=int\n@writtenBy=Antigravity\n\n")
        for d in verse_nodes_data: f.write(f"{d['id']}\t{d['verse']}\n")
            
    # otext.tf
    with open(os.path.join(OUTPUT_DIR, 'otext.tf'), 'w', encoding='utf-8') as f:
        f.write("@config\n@fmt:text-orig-full={text} \n@sectionTypes=book,chapter,verse\n@sectionFeatures=book,chapter,verse\n\n")

    print(f"TF Files generated in {OUTPUT_DIR}")

def convert_tob():
    parser = TOBParser()
    
    # List all Gen-1.xml etc files
    files = sorted([f for f in os.listdir(TOB_INPUT_DIR) if f.endswith('.xml') and '-' in f])
    
    # Custom sort for Book-Chapter.xml
    def sort_key(filename):
        # Gen-1.xml -> (Gen, 1)
        match = re.match(r'([^-]+)-(\d+)', filename)
        if match:
            return (match.group(1), int(match.group(2)))
        return (filename, 0)
    
    files.sort(key=sort_key)
    
    print(f"Processing {len(files)} files...")
    for filename in files:
        if 'notes' in filename: continue
        path = os.path.join(TOB_INPUT_DIR, filename)
        with open(path, 'r', encoding='utf-8') as f:
            parser.feed(f.read())
            
    write_tf_files(parser.words)

if __name__ == '__main__':
    convert_tob()
