#!/usr/bin/env python3
"""
build_french_index.py

Generates a JSON index of French Bible verses (BJ, TOB) for fast search.
Output: data/french_index.json

Structure:
{
  "BJ": [
    { "ref": "Gn 1:1", "text": "Au commencement...", "norm": "au commencement..." },
    ...
  ],
  "TOB": [ ... ]
}
"""
import sys
import os
import json
import unicodedata
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.text_fabric_adapter import TextFabricAdapter

def normalize_text(text: str) -> str:
    """
    Normalize French text for search:
    1. Lowercase
    2. NFD decomposition to separate accents
    3. Remove non-spacing marks (accents)
    4. Normalize whitespace
    """
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    # Handle ligatures
    text = text.replace("œ", "oe").replace("æ", "ae")
    
    # Decompose
    text = unicodedata.normalize('NFD', text)
    
    # Filter out accents
    text = "".join(c for c in text if unicodedata.category(c) != 'Mn')
    
    return text.strip()

def main():
    print("Building French Search Index...")
    
    # Initialize Adapter
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    adapter = TextFabricAdapter(data_dir=data_dir)
    
    output_data = {
        "BJ": [],
        "TOB": []
    }
    
    # 1. Process TOB
    print("Processing TOB (Traduction Œcumenique de la Bible)...")
    if adapter.tob:
        count = 0
        api = adapter.tob
        F, T = api.F, api.T
        
        # Iterate all verses
        for v_node in F.otype.s('verse'):
            text = T.text(v_node)
            if not text:
                continue
                
            # Get Book, Chapter, Verse
            section = T.sectionFromNode(v_node)
            book_fr, chapter, verse = section
            
            # Convert to standard ref format used in app (e.g. "Gn 1:1")
            # Problem: TOB uses French names "Genèse" etc.
            # We want to store the "Display Ref" that the user sees? 
            # OR we store the raw params to reconstruct it.
            # Let's store a display ref using the French book name as is, 
            # or try to map it to standard code if possible.
            # Creating a "ref" string like "Genèse 1:1" is good for display.
            
            ref = f"{book_fr} {chapter}:{verse}"
            
            norm_text = normalize_text(text)
            
            output_data["TOB"].append({
                "r": ref,       # specific key to save space? "ref" is fine
                "b": book_fr,   # book
                "c": int(chapter),
                "v": int(verse),
                "t": text,      # original text
                "n": norm_text  # normalized for search
            })
            count += 1
            if count % 5000 == 0:
                print(f"  Processed {count} verses...")
        print(f"TOB: {count} verses indexed.")
    else:
        print("TOB data not found or failed to load.")

    # 2. Process BJ
    print("Processing BJ (Bible de Jérusalem)...")
    if adapter.bj_api:
        count = 0
        api = adapter.bj_api
        F, T = api.F, api.T
        
        for v_node in F.otype.s('verse'):
            text = T.text(v_node)
            if not text:
                continue
            
            section = T.sectionFromNode(v_node)
            book_code, chapter, verse = section # BJ uses codes like "GEN"
            
            # Map code to French Name? 
            # For BJ, T.sectionFromNode returns CODES.
            # We can use adapter.normalizer later to format it, but let's store the code for now
            # or try to get a display name.
            # Let's stick to the code for BJ indexing, the worker can formatting it if needed,
            # OR we formate it here. 
            # "Gen 1:1" is fine.
            
            ref = f"{book_code} {chapter}:{verse}"
            norm_text = normalize_text(text)
            
            output_data["BJ"].append({
                "r": ref,
                "b": book_code,
                "c": int(chapter),
                "v": int(verse),
                "t": text,
                "n": norm_text
            })
            count += 1
            if count % 5000 == 0:
                print(f"  Processed {count} verses...")
        print(f"BJ: {count} verses indexed.")
    else:
        print("BJ data not found or failed to load.")
        
    # Save to file
    output_path = os.path.join(data_dir, "french_index.json")
    print(f"Saving index to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False) # separators=(',', ':') to minify? No need for now.
        
    print("Done!")

if __name__ == "__main__":
    main()
