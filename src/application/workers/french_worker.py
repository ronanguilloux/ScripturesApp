#!/usr/bin/env python3
"""
french_worker.py

Performs search on French Bible index (BJ, TOB).
Called by CLI.

Usage:
    python3 src/application/workers/french_worker.py <query> --bible <version> [--limit N]

Output:
    JSON array of results.
"""
import sys
import os
import json
import argparse
import unicodedata
import re

def normalize_text(text: str) -> str:
    """
    Normalize French text for search:
    1. Lowercase
    2. NFD decomposition to separate accents
    3. Remove non-spacing marks (accents)
    """
    if not text:
        return ""
    text = text.lower()
    # Handle ligatures
    text = text.replace("œ", "oe").replace("æ", "ae")
    
    text = unicodedata.normalize('NFD', text)
    text = "".join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.strip()

def perform_search(verses, query, limit=20):
    """
    Search logic reusable for testing.
    """
    # Normalize query
    query_norm = normalize_text(query)
    
    try:
        # Escape query for regex but keep spaces
        escaped_query = re.escape(query_norm)
        # Handle "exact word or expression"
        # We wrap in \b
        pattern_str = r'\b' + escaped_query + r'\b'
        pattern = re.compile(pattern_str)
    except Exception as e:
         return {"error": f"Invalid query regex: {e}"}
         
    matches = []
    
    for v in verses:
        # v = {"r": ref, "b": book, "c": ch, "v": vs, "t": text, "n": norm}
        verse_norm = v.get("n", "")
        
        if pattern.search(verse_norm):
            matches.append(v)
            
    # Format results
    output_results = []
    for m in matches[:limit]:
        output_results.append({
            "ref": m.get("r"),
            "book_code": m.get("b"),
            "chapter": m.get("c"),
            "verse": m.get("v"),
            "greek": "", # No greek
            "french": m.get("t"),
            "highlights": [query] # Simple hint
        })
        
    output = {
        "lemma": query,
        "total": len(matches),
        "results": output_results
    }
    return output

def main():
    parser = argparse.ArgumentParser(description="French Bible Search")
    parser.add_argument("query", help="Search query (word or expression)")
    parser.add_argument("--bible", "-b", required=True, choices=["bj", "tob"], help="Bible version (bj or tob)")
    parser.add_argument("--limit", type=int, default=20, help="Max results")
    args = parser.parse_args()
    
    query = args.query
    version = args.bible.upper()
    limit = args.limit
    
    # Locate index
    # script is in src/application/workers -> src/application -> src -> root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    index_path = os.path.join(base_dir, "data", "french_index.json")
    
    if not os.path.exists(index_path):
        print(json.dumps({"error": f"Index not found at {index_path}"}))
        sys.exit(1)
        
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(json.dumps({"error": f"Failed to load index: {e}"}))
        sys.exit(1)
        
    verses = data.get(version, [])
    
    output = perform_search(verses, query, limit)
    print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__":
    main()
