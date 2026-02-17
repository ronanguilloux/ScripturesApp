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


def lemmatize(word: str) -> str:
    """Use OdyCy to find the lemma of a Greek word."""
    import spacy
    nlp = spacy.load("grc_odycy_joint_sm")
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



def find_in_text_fabric(lemma: str, original_word: str, limit: int):
    """Search Text-Fabric N1904 for the lemma, return results as dicts."""
    import contextlib
    from tf.app import use
    from src.adapters.text_fabric_adapter import TextFabricAdapter
    
    data_dir = os.path.join(project_root, "data")
    
    def n1904_p():
        with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
            try: return use("CenterBLC/N1904", version="1.0.0", silent=True)
            except: return None
    
    adapter = TextFabricAdapter(
        data_dir=data_dir,
        n1904_provider=n1904_p,
    )
    
    # Use Smart Lemmatize to get the "Real" lemma if OdyCy failed
    # We pass the adapter which holds the TF reference
    smart_lemma = smart_lemmatize(original_word, adapter)
    
    # If smart_lemma differs from OdyCy lemma, use it
    if smart_lemma != lemma:
        lemma = smart_lemma

    # Search using the (possibly corrected) lemma
    results_lemma = adapter.find_lemma(lemma)
    
    # If the original word is different from the lemma, also search for it
    results_original = []
    norm_lemma = unicodedata.normalize('NFC', lemma)
    norm_original = unicodedata.normalize('NFC', original_word)
    if norm_original != norm_lemma:
        results_original = adapter.find_lemma(original_word)
    
    # Merge and deduplicate by (book, chapter, verse)
    seen = set()
    merged = []
    for v in results_lemma + results_original:
        key = (v.book_code, v.chapter, v.verse)
        if key not in seen:
            seen.add(key)
            merged.append(v)
    
    # Sort by canonical order (book_code, chapter, verse)
    merged.sort(key=lambda v: (v.book_code, v.chapter, v.verse))
    
    # Extract English gloss for the lemma from N1904 word features
    lemma_gloss = ""
    api = adapter.n1904.api if adapter.n1904 else None
    if api:
        # Normalize the lemma (strip accents for better matching)
        norm_lemma = unicodedata.normalize('NFC', lemma)
        
        # Try to find ANY word with this lemma to get the gloss
        for w in api.F.otype.s('word'):
            l_raw = api.F.lemma.v(w)
            if l_raw and unicodedata.normalize('NFC', l_raw) == norm_lemma:
                # Try 'gloss' first, then 'trans'
                if hasattr(api.F, 'gloss'):
                    lemma_gloss = api.F.gloss.v(w) or ""
                if not lemma_gloss and hasattr(api.F, 'trans'):
                    lemma_gloss = api.F.trans.v(w) or ""
                if lemma_gloss:
                    break
        
        # If first lemma didn't work, try the ORIGINAL word's lemma
        # (in case smart_lemmatize corrected it)
        if not lemma_gloss and original_word != lemma:
            for w in api.F.otype.s('word'):
                l_raw = api.F.lemma.v(w)
                if l_raw and unicodedata.normalize('NFC', l_raw) == unicodedata.normalize('NFC', original_word):
                    if hasattr(api.F, 'gloss'):
                        lemma_gloss = api.F.gloss.v(w) or ""
                    if not lemma_gloss and hasattr(api.F, 'trans'):
                        lemma_gloss = api.F.trans.v(w) or ""
                    if lemma_gloss:
                        break

    # Build output
    output = {
        "lemma": lemma,
        "original": original_word,
        "lemma_gloss": lemma_gloss,
        "total": len(merged),
        "results": []
    }
    
    # (Fallback logic removed from here as it is now in smart_lemmatize)
    
    normalizer = adapter.normalizer
    
    for verse in merged[:limit]:
        # Localize book name
        ref_display = f"{verse.book_code} {verse.chapter}:{verse.verse}"
        n1904_name = normalizer.code_to_n1904.get(verse.book_code, verse.book_code)
        tob_name = normalizer.n1904_to_tob.get(n1904_name)
        if tob_name:
            ref_display = f"{tob_name} {verse.chapter}:{verse.verse}"
        
        # Get French translation
        fr_text = ""
        try:
            fr_verse = adapter.get_verse(verse.book_code, verse.chapter, verse.verse, version="TOB")
            if fr_verse and fr_verse.text:
                fr_text = fr_verse.text
        except:
            pass
        
        output["results"].append({
            "ref": ref_display,
            "book_code": verse.book_code,
            "chapter": verse.chapter,
            "verse": verse.verse,
            "greek": verse.text,
            "french": fr_text,
            "highlights": verse.metadata.get("highlight_words", [])
        })
    
    return output


def main():
    parser = argparse.ArgumentParser(description="OdyCy-powered Greek lemma search")
    parser.add_argument("word", help="Greek word to search for")
    parser.add_argument("--limit", type=int, default=20, help="Max results")
    args = parser.parse_args()
    
    word = args.word
    
    # Step 1: Search Text-Fabric
    # We pass the original word as the 'lemma' initially.
    # find_in_text_fabric will call smart_lemmatize internally to find the real lemma.
    # This enables lazy-loading of OdyCy (only if TF lookup fails).
    output = find_in_text_fabric(word, word, args.limit)
    
    # Check if the search yielded results.
    # If not, and if the lemma is same as word (OdyCy failure) or just no results,
    # the find_in_text_fabric function ALREADY contains the fallback logic
    # to search for stripped forms.
    
    # Wait, find_in_text_fabric returns specific results.
    # But the external caller (CLI or test script) might only see the "lemma" field 
    # which we set to `lemmatize(word)` initially.
    # If find_in_text_fabric updated the lemma internally (which it does in my previous edit),
    # we should be fine IF the output dict is what is verified.
    
    # HOWEVER, test_lemmatization.py imports `lemmatize` directly!
    # "from find_worker import lemmatize"
    # So it bypasses find_in_text_fabric entirely.
    # We must move the fallback logic INTO `lemmatize` or create a `smart_lemmatize`.
    
    # Output as JSON
    print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__":
    main()
