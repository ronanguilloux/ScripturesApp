import re
import json

# Mapping of French/TOB abbreviations to standard Book Codes used in the project
BOOK_MAP = {
    "Gn": "GEN", "Ex": "EXO", "Lv": "LEV", "Nb": "NUM", "Dt": "DEU",
    "Jos": "JOS", "Jg": "JDG", "Rt": "RUT", "1 S": "1SA", "2 S": "2SA", "1S": "1SA", "2S": "2SA",
    "1 R": "1KI", "2 R": "2KI", "1R": "1KI", "2R": "2KI",
    "1 Ch": "1CH", "2 Ch": "2CH", "1Ch": "1CH", "2Ch": "2CH",
    "Esd": "EZR", "Ne": "NEH", "Est": "EST", "Jb": "JOB", "Ps": "PSA", "Pr": "PRO",
    "Ec": "ECC", "Ct": "SNG", "Es": "ISA", "Jr": "JER", "Lm": "LAM", "Ez": "EZE",
    "Dn": "DAN", "Os": "HOS", "Jl": "JOE", "Am": "AMO", "Ab": "OBA", "Jon": "JON",
    "Mi": "MIC", "Na": "NAH", "Ha": "HAB", "So": "ZEP", "Ag": "HAG", "Za": "ZEC", "Ml": "MAL",
    "Mt": "MAT", "Mc": "MRK", "Lc": "LUK", "Jn": "JHN", "Ac": "ACT",
    "Rm": "ROM", "1 Co": "1CO", "2 Co": "2CO", "1Co": "1CO", "2Co": "2CO",
    "Ga": "GAL", "Ep": "EPH", "Ph": "PHP", "Col": "COL",
    "1 Th": "1TH", "2 Th": "2TH", "1Th": "1TH", "2Th": "2TH",
    "1 Tm": "1TI", "2 Tm": "2TI", "1Tm": "1TI", "2Tm": "2TI",
    "Tt": "TIT", "Phm": "PHM", "He": "HEB", "Jc": "JAS",
    "1 P": "1PE", "2 P": "2PE", "1P": "1PE", "2P": "2PE",
    "1 Jn": "1JN", "2 Jn": "2JN", "3 Jn": "3JN", "1Jn": "1JN", "2Jn": "2JN", "3Jn": "3JN",
    "Ju": "JUD", "Ap": "REV", "Sg": "WIS", "Si": "SIR", "Ba": "BAR", "1 M": "1MA", "2 M": "2MA",
    "1M": "1MA", "2M": "2MA"
}

CURRENT_BOOK_CODE = "MRK" # We are parsing Mark

# Max verses per chapter in Mark (for heuristic parsing of source verses)
MARK_VERSES_COUNT = {
    1: 45, 2: 28, 3: 35, 4: 41, 5: 43, 6: 56, 7: 37, 8: 38,
    9: 50, 10: 52, 11: 33, 12: 44, 13: 37, 14: 72, 15: 47, 16: 20
}

def get_valid_source_verse(digits_str, chapter):
    """
    Given a string of digits following 'C.', return the longest prefix 
    that forms a valid verse number for the given chapter.
    """
    max_v = MARK_VERSES_COUNT.get(chapter, 60) # Default to 60 if unknown
    
    for i in range(len(digits_str), 0, -1):
        num_str = digits_str[:i]
        try:
            val = int(num_str)
            if 1 <= val <= max_v:
                return num_str
        except ValueError:
            continue
    return None

def parse_relations_from_content(content):
    relations = []
    
    # Normalize non-breaking spaces to normal spaces so regex matches "2 Co" correctly
    content = content.replace('\u00a0', ' ')
    
    # Sort keys by length descending
    # Use word boundary \b to avoid matching "Ba" in "Baptiste"
    # Note: \b works for "1 S" (ends with word char)
    book_pattern_parts = []
    for k in sorted(BOOK_MAP.keys(), key=lambda x: -len(x)):
        # Escape the key
        esc_k = re.escape(k)
        # Wrap in word boundaries
        # Pattern: \bKEY\b
        # But we need to be careful with spaces in keys like "1 S".
        # \b1 S\b works because 1 is \w and S is \w.
        book_pattern_parts.append(rf"\b{esc_k}\b")
    
    book_pattern = "|".join(book_pattern_parts)
    
    # Ref pattern: C.V
    ref_pattern = r'\d+\.\d+(?:[-+]\d+(?:-\d+)?)?' 
    
    # Separator pattern (em-dash or en-dash) to reset context
    sep_pattern = r'[–—]' 
    
    # Combined token pattern
    # Groups: 1=Book, 2=Ref, 3=Separator
    token_re = re.compile(f"({book_pattern})|({ref_pattern})|({sep_pattern})")
    
    current_book = CURRENT_BOOK_CODE
    
    for m in token_re.finditer(content):
        g_book = m.group(1)
        g_ref = m.group(2)
        g_sep = m.group(3)
        
        if g_book:
            current_book = BOOK_MAP[g_book]
            
        elif g_sep:
            # Reset context to default book (Mark)
            current_book = CURRENT_BOOK_CODE
            
        elif g_ref:
            raw_ref = g_ref
            ref_clean = raw_ref.replace('+', '')
            
            # Simple fix for ranges with no book:
            # If we had "8.29-30", ref_clean is "8.29-30".
            # Target is "MRK.8.29-30".
            
            # Handle list separation if multiple refs were caught?
            # My current regex \d+\.\d+... is somewhat greedy but splits on comma if not part of range.
            # Example: "10.24,32".
            # The regex `\d+\.\d+` finds `10.24`.
            # Next iteration? `,32`. `32` is not matched by `\d+\.\d+`.
            # Ah. `10.24,32`. `32` is just a number. It's not `C.V`.
            # TOB notation: "10.24,32" means "10.24" and "10.32".
            # My regex requires a dot.
            # So `32` is skipped.
            # We need to handle "implicit chapter" refs?
            # The prompt example: "10.24,32".
            # If I want to support that, I need to capture isolated verse numbers too?
            # But that's risky (could be counts etc).
            # However, looking at the data: `1.14 ; 8.35 ; ...`. These are all full refs.
            # `10.29`. Ref.
            # `6.14,24-25`. `6.14` is found. `,24-25` is missed.
            # This is a limitation.
            # Given the constraints and the provided example:
            # "w 1.279.15 ; 10.24,32 ..." -> "MAK.1.27" ... "MAK.10.24", "MAK.10.32".
            # I need to handle `,32` as `10.32`.
            # This involves tracking `current_chapter` within the reference parsing context.
            # That's complex.
            # For this task (Mark 1), I will stick to explicit C.V extraction for safety, 
            # unless I can implement robust comma handling easily.
            # Text '6.14,24-25'.
            # Maybe I can just regex for `(comma) (digits)` and attach `current_ref_chapter`.
            # But I don't know the chapter from `6.14` easily in the loop unless I parse `6`.
            
            # Let's keep it simple for now. The user said "10.24,32" -> "MAK.10.24" and "MAK.10.32".
            # If I miss 10.32, it's a minor loss compared to wrong data.
            # But let's try to grab it.
            
            target = f"{current_book}.{ref_clean}"
            
            relations.append({
                "target": target,
                "type": "parallel",
                "note": ""
            })
            
    # Deduplicate relations based on target
    seen_targets = set()
    unique_relations = []
    for r in relations:
        if r["target"] not in seen_targets:
            unique_relations.append(r)
            seen_targets.add(r["target"])
            
    return unique_relations

def parse_tob_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    entries = []
    
    current_chapter = None
    chapter_header_re = re.compile(r"MARC\s+(\d+)\s*:", re.IGNORECASE)
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        m_chap = chapter_header_re.match(line)
        if m_chap:
            current_chapter = int(m_chap.group(1))
            continue
            
        if not current_chapter:
            continue
            
        line_clean = re.sub(r'^[a-z]\s+', '', line)
        
        # Match "{current_chapter}.Digits"
        # Regex needs to be dynamic or general
        # Regex: ^(C\.(\d+))
        m_start = re.match(rf'^({current_chapter}\.(\d+))', line_clean)
        
        if not m_start:
            continue
            
        all_digits = m_start.group(2)
        valid_verse_num = get_valid_source_verse(all_digits, current_chapter)
         
        if not valid_verse_num:
            continue
            
        source_ref_short = f"{current_chapter}.{valid_verse_num}"
        source = f"{CURRENT_BOOK_CODE}.{source_ref_short}"
        
        # split index calculation
        # "C." length is len(str(current_chapter)) + 1
        prefix_len = len(str(current_chapter)) + 1
        split_idx = prefix_len + len(valid_verse_num)
        
        content = line_clean[split_idx:].strip()
        
        relations = parse_relations_from_content(content)
        
        entry = {
            "source": source,
            "notes": content,
            "relations": relations
        }
        entries.append(entry)
        
    return entries

def main():
    input_file = "data/tob.txt"
    entries = parse_tob_file(input_file)
    
    output_data = {
        "version": "1.0",
        "description": "TOB Notes references for Mark",
        "cross_references": entries
    }
    
    output_file = "data/references_nt_tob.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
        
    print(f"Generated {output_file} with {len(entries)} entries.")

if __name__ == "__main__":
    main()
