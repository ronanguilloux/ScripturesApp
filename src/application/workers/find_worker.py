#!/usr/bin/env python3
"""
find_worker.py — OdyCy-powered Greek lemma search worker.

Runs in the .venv-spacy (Python 3.13) environment.
Called by the main CLI via subprocess.

Usage:
    .venv-spacy/bin/python3.13 src/application/workers/find_worker.py <word> [--limit N]

Output: JSON array of results to stdout.
"""
import sys
import os
import json
import argparse
import unicodedata
import warnings

warnings.filterwarnings("ignore")

# Add project root to path for imports
# Add project root to path for imports
# __file__ is src/application/workers/find_worker.py
# project_root is 3 levels up from src: src/application/workers -> src/application -> src -> (project_root)
# wait, os.path.dirname(__file__) = workers
# dirname -> application
# dirname -> src
# dirname -> project_root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.utils.greek_normalizer import GreekNormalizer


# Global NLP model
_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        # Suppress warnings
        import warnings
        warnings.filterwarnings("ignore")
        _nlp = spacy.load("grc_odycy_joint_sm")
    return _nlp

def lemmatize(word: str) -> str:
    """Use OdyCy to find the lemma of a Greek word."""
    nlp = get_nlp()
    doc = nlp(word)
    if doc and len(doc) > 0:
        return doc[0].lemma_
    return word


# Global state for OdyCy alignment
_alignment_map = None

def load_alignment_map():
    """Lazy load the OdyCy alignment map."""
    global _alignment_map
    if _alignment_map is not None:
        return _alignment_map
        
    try:
        import json
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        map_path = os.path.join(base_dir, "data", "odycy_alignment.json")
        
        _alignment_map = {}
        
        # Load main alignment (9,677 corpus-wide N1904 corrections)
        if os.path.exists(map_path):
            with open(map_path, "r") as f:
                _alignment_map = json.load(f)
        
        # overrides removed as per user request
        # _alignment_map.update(overrides)
                 
        return _alignment_map
    except Exception as e:
        print(f"Alignment map load failed: {e}", file=sys.stderr)
    
    return {}

def smart_lemmatize(word: str, adapter) -> str:
    """
    TF-First Hybrid Lemmatization Strategy:
    1. TF Direct (accent-insensitive) → Fast path for known NT words
    2. OdyCy + Alignment → Fallback for unknown forms
    3. Polytonic Restoration → Edge cases
    """
    import logging
    import time
    
    start = time.time()
    
    # Load alignment map once
    alignment = load_alignment_map()
    
    def check_alignment(lemma):
        """Helper to check alignment corrections"""
        if alignment and lemma in alignment:
            return alignment[lemma]
        return lemma
    
    # Ensure indices are built
    adapter.build_stripped_index()
    stripped_input = GreekNormalizer.strip_accents(word)
    
    # ==========================================
    # LAYER 1: TF DIRECT LOOKUP (Fast Path)
    # ==========================================
    tf_lemma = adapter.find_lemma_by_stripped_surface(stripped_input)
    if tf_lemma:
        elapsed = (time.time() - start) * 1000
        logging.debug(f"Lemmatized '{word}' → '{tf_lemma}' in {elapsed:.1f}ms (layer: TF-direct)")
        return tf_lemma
    
    # ==========================================
    # LAYER 2: ODYCY + ALIGNMENT (Fallback)
    # ==========================================
    odycy_lemma = lemmatize(word)
    aligned_lemma = check_alignment(odycy_lemma)
    
    if aligned_lemma != odycy_lemma:
        # Alignment corrected it
        elapsed = (time.time() - start) * 1000
        logging.debug(f"Lemmatized '{word}' → '{aligned_lemma}' in {elapsed:.1f}ms (layer: OdyCy+alignment)")
        return aligned_lemma
    
    # ==========================================
    # LAYER 3: POLYTONIC RESTORATION (Edge Cases)
    # ==========================================
    # Try to restore polytonic forms and feed to OdyCy
    candidates = adapter.find_polytonic_surfaces(stripped_input)
    
    # Fuzzy matching variations
    if not candidates:
        # Try movable nu
        if not stripped_input.endswith("ν"):
            candidates = adapter.find_polytonic_surfaces(stripped_input + "ν")
        
        # Try modern/ancient ending swap (-αν → -ον)
        if not candidates and stripped_input.endswith("αν"):
            variation = stripped_input[:-2] + "ον"
            candidates = adapter.find_polytonic_surfaces(variation)
    
    if candidates:
        # Pick best candidate (alphabetically first for stability)
        best_candidate = sorted(list(candidates))[0]
        
        # Feed RESTORED form to OdyCy
        restored_lemma = lemmatize(best_candidate)
        
        # Check alignment for restored lemma
        aligned_restored = check_alignment(restored_lemma)
        if aligned_restored != restored_lemma:
            elapsed = (time.time() - start) * 1000
            logging.debug(f"Lemmatized '{word}' → '{aligned_restored}' in {elapsed:.1f}ms (layer: Restored+alignment)")
            return aligned_restored
        
        # Validate restored lemma exists in TF
        stripped_restored = GreekNormalizer.strip_accents(restored_lemma)
        if stripped_restored in adapter._stripped_index:
            elapsed = (time.time() - start) * 1000
            logging.debug(f"Lemmatized '{word}' → '{restored_lemma}' in {elapsed:.1f}ms (layer: Restored)")
            return restored_lemma
    
    # ==========================================
    # LAST RESORT: Return OdyCy result
    # ========================================== 
    elapsed = (time.time() - start) * 1000
    logging.debug(f"Lemmatized '{word}' → '{odycy_lemma}' in {elapsed:.1f}ms (layer: OdyCy-only, TF miss)")
    return odycy_lemma




# Global cache for indices
_loaded_indices = {}

def load_index(corpus: str):
    """Load compressed index for corpus."""
    if corpus in _loaded_indices:
        return _loaded_indices[corpus]
        
    filename = f"greek_index_{corpus.lower()}.pkl.gz"
    path = os.path.join(project_root, "data", filename)
    
    if not os.path.exists(path):
        return None
        
    import gzip
    import pickle
    import time
    
    start = time.time()
    try:
        with gzip.open(path, "rb") as f:
            data = pickle.load(f)
            _loaded_indices[corpus] = data
            return data
    except Exception as e:
        sys.stderr.write(f"Failed to load index {corpus}: {e}\n")
        return None

def find_in_index(lemma: str, original_word: str, corpus: str, limit: int):
    """Search using pre-built indices."""
    
    # Instantiate Normalizer for sorting and localization
    from src.book_normalizer import BookNormalizer
    normalizer = BookNormalizer(os.path.join(project_root, "data"))
    
    # Identify corpora to search
    corpora = []
    if corpus == "all":
        corpora = ["NT", "LXX"]
    elif corpus == "lxx":
        corpora = ["LXX"]
    else:
        corpora = ["NT"]
        
    results = []
    seen = set()
    
    # Normalize inputs
    lemma_norm = unicodedata.normalize('NFC', lemma)
    original_norm = unicodedata.normalize('NFC', original_word)
    
    # Terms to lookup
    # 1. The Lemma (OdyCy result)
    # 2. The Original Word (if different, for exact surface matching)
    search_terms = {lemma_norm}
    if original_norm != lemma_norm:
        search_terms.add(original_norm)
        
    # Normalized terms for highlighting (accent-insensitive)
    stripped_search_terms = {GreekNormalizer.strip_accents(t) for t in search_terms}
        
    for c_name in corpora:
        index = load_index(c_name)
        if not index:
            continue
            
        lemmas_map = index["lemmas"]
        verses_map = index["verses"]
        
        # Find matches
        refs = set()
        for term in search_terms:
            if term in lemmas_map:
                refs.update(lemmas_map[term])
        
        # Convert to results
        for book_code, chapter, verse in refs:
            key = (book_code, chapter, verse)
            if key in seen: continue
            seen.add(key)
            
            text = verses_map.get(key, "")
            
            # Simple highlighting logic
            highlights = []
            # Check if term exists in text (naive check, but sufficient for now)
            # Better: split text and checking normalized forms
            # OdyCy worker previously did more complex highlighting, let's replicate basic behavior
            # We already have the text.
            
            # Use regex for highlighting to be safe
            import re
            
            # Construct highlight patterns from search terms
            # This is a bit rough, but matches `french_worker` strategy
            for term in search_terms:
                 # normalized term might not match raw text if raw has accents/diacritics distinct from NFC
                 # but text in index IS standard Text-Fabric text.
                 # Let's try to find it.
                 pass
            
            # Reuse existing highlight logic logic from previous implementation if possible?
            # Actually, let's just use the `find_in_text_fabric` logic adapted.
            # But we don't have word nodes anymore.
            # We only have the full text string.
            # So highlighting must be text-based.
            
            # Highlight robustly:
            # Normalize text words and check against search terms
            words = text.split()
            for w in words:
                w_clean = w.strip().rstrip(",.;·")
                w_stripped = GreekNormalizer.strip_accents(w_clean)
                if w_stripped in stripped_search_terms:
                    highlights.append(w)
            
            # Get localized book name if possible
            # We already have a normalizer instance available from the outer scope if we move it up, 
            # or we can pass it in. 
            # Better to pass it or move instantiation up. 
            # Let's assume we move normalizer instantiation to `main` or `find_in_index` start.
            
            book_label = book_code
            if normalizer:
                # Try to get French label
                # Code -> French Label
                # The normalizer has: code_to_n1904 (English Key), n1904_to_tob (French Label)
                en_key = normalizer.code_to_n1904.get(book_code)
                if en_key and en_key in normalizer.n1904_to_tob:
                    book_label = normalizer.n1904_to_tob[en_key]
            
            results.append({
                "ref": f"{book_label} {chapter}:{verse}",
                "book_code": book_code,
                "chapter": chapter,
                "verse": verse,
                "greek": text,
                "french": "", # Greek search, usually no French unless requested separate
                "highlights": [], # Will be populated after slicing for performance
                "corpus": c_name
            })
            
    # Sort
    # We need a book order.
    
    def sort_key(r):
        bn = r["book_code"]
        # Handle LXX books if not in book_order
        bo = normalizer.book_order.get(bn, 999)
        return (bo, r["chapter"], r["verse"])
        
    results.sort(key=sort_key)
    
    # Slice to limit
    final_results = results[:limit]
    
    # Post-process highlighting using OdyCy (Robust morphological matching)
    # This is slower but accurate for cases like Βασιλεῦ (voc) matching βασιλεύς (nom)
    try:
        nlp = get_nlp()
        
        # We need to match against:
        # 1. The Lemma (βασιλεύς)
        # 2. The Original Search Term (βασιλέα) - usually covered by lemma, but good fallback
        # 3. Stripped versions?
        
        # OdyCy tokens have .lemma_ property.
        # We just check if token.lemma_ == lemma OR token.text == original_word
        
        # Normalize everything to NFC to handle Oxia/Tonos differences
        target_lemmas = {unicodedata.normalize('NFC', lemma)}
        # Also check for exact surface match (normalized)
        target_surfaces = {unicodedata.normalize('NFC', original_word), unicodedata.normalize('NFC', lemma)}
        
        for res in final_results:
            text = res["greek"]
            doc = nlp(text)
            
            highlights = set()
            for token in doc:
                # Normalize token lemma
                token_lemma_norm = unicodedata.normalize('NFC', token.lemma_)
                
                # Check lemma match
                if token_lemma_norm in target_lemmas:
                    highlights.add(token.text)
                    continue
                
                # Check surface match (fallback)
                if token.text in target_surfaces:
                    highlights.add(token.text)
                    continue
            
            # Fallback: Simple accent-insensitive highlighting if OdyCy misses it
            # This handles cases where OdyCy lemma might differ slightly or normalization/tokenization issues
            if not highlights:
                words = text.split()
                # Create stripped set of targets for comparison
                stripped_targets = {GreekNormalizer.strip_accents(t) for t in target_lemmas | target_surfaces}
                # Also add the stripped search term itself just in case
                stripped_targets.add(GreekNormalizer.strip_accents(original_word))
                
                for w in words:
                    w_clean = w.strip().rstrip(",.;·")
                    w_stripped = GreekNormalizer.strip_accents(w_clean)
                    if w_stripped in stripped_targets:
                        highlights.add(w_clean)
                
            res["highlights"] = list(highlights)
            
    except Exception as e:
        # Fallback to simple accent-insensitive highlighting if OdyCy execution fails
        sys.stderr.write(f"Highlighting error: {e}\n")
        # Reuse previous logic
        stripped_search_terms = {GreekNormalizer.strip_accents(t) for t in search_terms}
        for res in final_results:
            if not res["highlights"]:
                h = []
                words = res["greek"].split()
                for w in words:
                    w_clean = w.strip().rstrip(",.;·")
                    w_stripped = GreekNormalizer.strip_accents(w_clean)
                    if w_stripped in stripped_search_terms:
                        h.append(w)
                res["highlights"] = list(set(h))

    return {
        "lemma": lemma,
        "original": original_word,
        "lemma_gloss": "", # Gloss not in index yet
        "total": len(results),
        "results": final_results
    }

def find_lemma(word: str) -> str:
    """
    Find lemma using OdyCy, Alignment Map, and Heuristics.
    Does NOT use TF indices for fallback (that happens in main/search phase).
    """
    # Load alignment
    alignment = load_alignment_map()
    
    # OdyCy
    lemma = lemmatize(word)
    
    # Alignment fallback
    # 1. Check if the original word is directly mapped (manual override)
    if alignment and word in alignment:
        lemma = alignment[word]
    # 2. Check stripped word (handles monotonic input λαμβανω -> λαμβάνω if mapped)
    elif alignment and GreekNormalizer.strip_accents(word) in alignment:
        lemma = alignment[GreekNormalizer.strip_accents(word)]
    # 3. Check if the OdyCy lemma is mapped
    elif alignment and lemma in alignment:
        lemma = alignment[lemma]
        
    # Heuristic: Classical vs Koine Spelling (ψ vs μψ) for unaligned words
    # If lemma is still same as word (likely failure) OR we want to be robust
    if alignment and lemma == word:
         if "ψ" in word or "Ψ" in word:
             var = word.replace("ψ", "μψ").replace("Ψ", "Μψ")
             # Check if variation is in alignment
             if var in alignment:
                 lemma = alignment[var]
             else:
                 # Try lemmatizing variation
                 var_lemma = lemmatize(var)
                 if var_lemma != var: # If variation lemmatized to something else
                      lemma = var_lemma
                      if alignment and lemma in alignment:
                          lemma = alignment[lemma]
    return lemma

def main():
    parser = argparse.ArgumentParser(description="OdyCy-powered Greek lemma search")
    parser.add_argument("word", help="Greek word to search for")
    parser.add_argument("--limit", type=int, default=20, help="Max results")
    parser.add_argument("--corpus", choices=["nt", "lxx", "all"], default="nt", help="Search corpus")
    args = parser.parse_args()
    
    word = args.word
    
    # 1. Find Lemma
    lemma = find_lemma(word)
        
    # Search
    # Fallback: if lemma not found in NT index, but original word IS a lemma in NT index, use original word
    # This covers cases where OdyCy fails on dictionary forms (e.g. λαμβάνω -> λαμβανω)
    nt_index = load_index("NT")
    if nt_index:
        lemmas_map = nt_index["lemmas"]
        word_norm = unicodedata.normalize('NFC', word)
        lemma_norm = unicodedata.normalize('NFC', lemma)
        
        if lemma_norm not in lemmas_map and word_norm in lemmas_map:
            lemma = word_norm
        
        # Fallback 2: Monotonic/Fuzzy Scan
        # If still not found, scan all lemmas for an accent-insensitive match
        # This handles λαμβανω -> λαμβάνω
        if lemma not in lemmas_map:
            stripped_word = GreekNormalizer.strip_accents(word)
            for db_lemma in lemmas_map:
                if GreekNormalizer.strip_accents(db_lemma) == stripped_word:
                    lemma = db_lemma
                    break

    output = find_in_index(lemma, word, args.corpus, args.limit)
    
    print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__":
    main()
