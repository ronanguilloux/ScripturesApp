import re
import os

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
    max_v = MARK_VERSES_COUNT.get(chapter, 60)
    
    for i in range(len(digits_str), 0, -1):
        num_str = digits_str[:i]
        try:
            val = int(num_str)
            if 1 <= val <= max_v:
                return num_str
        except ValueError:
            continue
    return None

def fix_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    fixed_lines = []
    
    current_chapter = None
    chapter_header_re = re.compile(r"MARC\s+(\d+)\s*:", re.IGNORECASE)
    
    for line in lines:
        original_line = line
        line_stripped = line.strip()
        
        if not line_stripped:
            fixed_lines.append(line)
            continue
            
        m_chap = chapter_header_re.match(line_stripped)
        if m_chap:
            current_chapter = int(m_chap.group(1))
            fixed_lines.append(line)
            continue
            
        # If we haven't seen a chapter header yet, just preserve
        if not current_chapter:
            fixed_lines.append(line)
            continue

        # Check for NOTE line pattern: "letter Space Chapter.digitsContent"
        # Regex: ^([a-z]\s+)(C\.(\d+))(.*)$
        # We need to construct the regex with the literal current chapter to handle "1.xxx" vs "10.xxx" safely
        # E.g. for Chap 1: "^([a-z]\s+)(1\.(\d+))(.*)"
        
        # Capture:
        # 1: Prefix (e.g. "y ")
        # 2: Full Ref Start (e.g. "1.315") - wait, we just want to match the start
        
        # Let's match the prefix first
        m_prefix = re.match(r'^([a-z](?:\s+|$))', line) # Careful not to strip leading whitespace if any? Usually notes start at char 0
        
        if not m_prefix:
            # Maybe a continuation line or weird format? Preserve.
            fixed_lines.append(line)
            continue
            
        prefix = m_prefix.group(1)
        # The rest of the line (excluding newline)
        rest = line[len(prefix):].rstrip('\n')
        
        # Now we expect "Chapter.digits..."
        # e.g. "1.315.41..."
        
        if not rest.startswith(f"{current_chapter}."):
            # Unexpected format
            fixed_lines.append(line)
            continue
            
        # Digits start after "C."
        digits_start_idx = len(str(current_chapter)) + 1
        relevant_part = rest[digits_start_idx:] # "315.41..."
        
        # Find just the digits
        m_digits = re.match(r'^(\d+)', relevant_part)
        if not m_digits:
            fixed_lines.append(line)
            continue
            
        all_digits = m_digits.group(1)
        
        valid_verse = get_valid_source_verse(all_digits, current_chapter)
        
        if valid_verse:
            # We found the cut point.
            # Reconstruct.
            # "y " + "1.31" + "\t" + "5.41..."
            
            # Length of verse part in 'rest': len(str(current_chapter)) + 1 + len(valid_verse)
            verse_part_len = len(str(current_chapter)) + 1 + len(valid_verse)
            
            source_part = rest[:verse_part_len] # "1.31"
            content_part = rest[verse_part_len:] # "5.41..."
            
            # Only add tab if it looks like it needs one? 
            # The prompt says just put a tab chars.
            # BUT check if there is already a space?
            # "y 1.315.41" -> "y 1.31\t5.41"
            # "y 1.31 5.41" -> "y 1.31\t 5.41" ? 
            # The prompt example: "y 1.315.41" -> "y 1.31[tab]5.41"
            
            # Construct new line
            new_line = f"{prefix}{source_part}\t{content_part}\n"
            fixed_lines.append(new_line)
        else:
            fixed_lines.append(line)
            
    with open(filepath, 'w') as f:
        f.writelines(fixed_lines)

if __name__ == "__main__":
    fix_file("data/tob.txt")
    print("Fixed data/tob.txt")
