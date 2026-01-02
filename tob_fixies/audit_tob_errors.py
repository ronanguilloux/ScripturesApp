import json
import re

def main():
    with open("data/references_nt_tob.json", "r") as f:
        data = json.load(f)
        
    entries = data.get("cross_references", [])
    
    # We want to find entries where:
    # 1. The note text mentions a book abbreviation (e.g. "2 Co", "2 R", "Mt", etc.)
    # 2. But the corresponding relation has target book "MRK" (the default) instead of the referenced book.
    # 3. And the referenced verse digits match the target verse digits.
    
    # Let's define the book tokens we expect to find.
    # We can reuse the keys from parse_tob_notes.py, but we need to watch out for spaces.
    # The issue might be non-breaking spaces.
    
    # Books that are NOT Mark
    # We'll rely on the text scan.
    
    errors = []
    
    for entry in entries:
        source = entry["source"]
        notes = entry["notes"]
        relations = entry["relations"]
        
        # Check each relation
        for rel in relations:
            target = rel["target"]
            target_book = target.split('.')[0]
            
            if target_book == "MRK":
                # If target is Mark, check if the "Note" text implying this relation
                # actually mentioned another book.
                
                # Extract verse part from target: "MRK.8.12" -> "8.12"
                parts = target.split('.')
                if len(parts) < 3: continue
                target_ref_digits = f"{parts[1]}.{parts[2]}" # "8.12"
                
                # Now look for "8.12" in the notes
                # And look at what precedes it.
                # If we see "2 Co 8.12" or "2 Co 8.12" (nbs)
                
                # Find all occurrences of the ref digits in the note
                # We need to be careful of partial matches.
                
                # Simple heuristic:
                # If note contains " [BookAbbr] [digits]"
                # And we used MRK.
                
                # Regex to find context around the digits
                escaped_digits = re.escape(target_ref_digits)
                # Look for some chars before the digits
                # e.g. "2 Co 8.12"
                
                # Use a wider window
                matches = list(re.finditer(f"(.{{0,10}}){escaped_digits}", notes))
                
                for m in matches:
                    prefix = m.group(1)
                    # Check if prefix contains a known book abbr that is NOT Mc/Mark
                    # e.g. "2 Co ", "2 R ", "Mt "
                    
                    # Common problematic prefixes from user input: "2 Co", "2 R"
                    # Also common books: "Mt", "Lc", "Jn", "Ac", "Rm", "1 Co"...
                    
                    suspicious = False
                    found_abbr = ""
                    
                    # Manual check for common abbreviations that might be missed due to space issues
                    # "2 Co", "2 R", "1 R", "1 Co", "1 Th", "1 Tm", "1 Pi", "1 Jn" ...
                    # And also single letter ones if preceded by space? "Mt", "Lc"...
                    
                    # List of abbrs that imply a book change
                    # Taken from our extensive list but focusing on those with potential space issues or common misses
                    check_list = [
                         "Mt", "Lc", "Jn", "Ac", "Rm", "1 Co", "2 Co", "Ga", "Ep", "Ph", "Col",
                         "1 Th", "2 Th", "1 Tm", "2 Tm", "Tt", "Phm", "He", "Jc", "1 P", "2 P",
                         "1 Jn", "2 Jn", "3 Jn", "Ju", "Ap",
                         "Gn", "Ex", "Lv", "Nb", "Dt", "Jos", "Jg", "Rt", "1 S", "2 S", "1 R", "2 R",
                         "1 Ch", "2 Ch", "Esd", "Ne", "Est", "Jb", "Ps", "Pr", "Ec", "Ct", "Es", "Jr",
                         "Lm", "Ez", "Dn", "Os", "Jl", "Am", "Ab", "Jon", "Mi", "Na", "Ha", "So", "Ag",
                         "Za", "Ml"
                    ]
                    
                    cleaned_prefix = prefix.replace('\u00a0', ' ') # Normalize NBSP
                    
                    for abbr in check_list:
                        # logical check: matches "Abbr " ending the prefix
                        # e.g. "2 Co " ends "2 Co "
                        # "voir 2 R "
                        
                        if cleaned_prefix.strip().endswith(abbr) or cleaned_prefix.endswith(abbr + " "):
                             # Verify it's not "Mc" (Mark) - though Mc is distinct.
                             # If we found "Mt 8.12" and mapped to "MRK.8.12", that's an error.
                             
                             suspicious = True
                             found_abbr = abbr
                             break
                             
                    if suspicious:
                         errors.append(f"{source}: Target {target} but text says '{found_abbr} {target_ref_digits}' (Note segment: '...{prefix}{target_ref_digits}...')")
                         break # One error per relation is enough to report

    # Print results
    print(f"Found {len(errors)} potential errors.")
    for e in errors:
        print(e)
        
if __name__ == "__main__":
    main()
