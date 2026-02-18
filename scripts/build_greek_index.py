#!/usr/bin/env python3
import sys
import os
import pickle
import gzip
import unicodedata
import time
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.application.services import AdapterFactory
from src.book_normalizer import BookNormalizer

def normalize_text(text: str) -> str:
    """Normalize text to NFC."""
    if not text: return ""
    return unicodedata.normalize('NFC', text)

def build_index(adapter, books: Set[str], corpus_name: str, output_path: str):
    print(f"Building index for {corpus_name} ({len(books)} books)...")
    start_time = time.time()
    
    # Data structures
    # verses: { (book_code, ch, v): "text" }
    verses_store = {}
    # lemmas: { "lemma_nfc": [ (book_code, ch, v), ... ] }
    # Using set to avoid duplicates within same verse, then list for storage
    lemmas_store = defaultdict(set)
    
    count_verses = 0
    count_words = 0
    
    # Determine which app/api to use based on corpus
    # NT -> n1904, LXX -> lxx
    if corpus_name == "NT":
        app = adapter.n1904
    else: # LXX
        app = adapter.lxx
        
    if not app:
        print(f"Error: Could not load Text-Fabric app for {corpus_name}")
        return

    api = app.api
    F = api.F
    L = api.L
    T = api.T
    
    # Iterate over all books in the corpus
    for book_node in F.otype.s('book'):
        # Get book name from TF
        if corpus_name == "NT":
             # N1904 uses English names usually
             tf_book_name = T.sectionFromNode(book_node)[0]
             # Map to our internal code
             book_code = adapter.normalizer.n1904_to_code.get(tf_book_name)
             if not book_code:
                 book_code = adapter.normalizer.n1904_to_code.get(tf_book_name.replace(" ", "_"))
        else:
             # LXX
             tf_book_name = T.sectionFromNode(book_node)[0]
             # LXX names might differ, try to find matching code
             # Try direct lookup in normalizer maps or scan abbreviations
             book_code = None
             if tf_book_name in books: 
                 book_code = tf_book_name
             else:
                 # Try to find mapped code
                 for code in books:
                     if adapter.normalizer.code_to_n1904.get(code) == tf_book_name:
                         book_code = code
                         break
                     # Check abbreviations
                     if not book_code:
                         abbrs = adapter.normalizer.code_to_abbreviations.get(code, [])
                         if tf_book_name in abbrs:
                             book_code = code
                             break
        
        if not book_code or book_code not in books:
            # print(f"Skipping book: {tf_book_name} (mapped: {book_code})")
            continue
            
        print(f"  Processing {book_code}...")
        
        # Iterate Chapters
        for ch_node in L.d(book_node, otype='chapter'):
            ch_num = F.chapter.v(ch_node)
            
            # Iterate Verses
            for v_node in L.d(ch_node, otype='verse'):
                v_num = F.verse.v(v_node)
                
                # Get Text
                text = T.text(v_node)
                ref_key = (book_code, int(ch_num), int(v_num))
                verses_store[ref_key] = text
                count_verses += 1
                
                # Get Words / Lemmas
                for w_node in L.d(v_node, otype='word'):
                    # Get lemma features
                    # N1904 uses 'lemma', LXX uses 'lex' (usually) or 'lemma'
                    lemma = None
                    if hasattr(F, 'lemma'):
                        lemma = F.lemma.v(w_node)
                    if not lemma and hasattr(F, 'lex'):
                        lemma = F.lex.v(w_node)
                        
                    if lemma:
                        lemma_norm = normalize_text(lemma)
                        lemmas_store[lemma_norm].add(ref_key)
                        
                        # Also index surface form (normalized) for exact word search
                        surface = T.text(w_node).strip().rstrip(",.;·")
                        surface_norm = normalize_text(surface)
                        if surface_norm != lemma_norm:
                            lemmas_store[surface_norm].add(ref_key)
                            
                    count_words += 1

    # Convert sets to sorted lists for storage efficiency and determinism
    final_lemmas = {k: sorted(list(v)) for k, v in lemmas_store.items()}
    
    print(f"  Indexed {count_verses} verses, {len(final_lemmas)} unique terms.")
    print(f"  Saving to {output_path}...")
    
    payload = {
        "corpus": corpus_name,
        "verses": verses_store,
        "lemmas": final_lemmas
    }
    
    with gzip.open(output_path, "wb") as f:
        pickle.dump(payload, f)
        
    print(f"Done in {time.time() - start_time:.2f}s")


def main():
    print("Initializing Adapter...")
    adapter = AdapterFactory.get()
    
    data_dir = os.path.join(project_root, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # 1. Build NT Index
    nt_books = adapter.normalizer.NT_BOOKS
    build_index(
        adapter, 
        nt_books, 
        "NT", 
        os.path.join(data_dir, "greek_index_nt.pkl.gz")
    )
    
    # 2. Build LXX Index (OT + Apocrypha)
    lxx_books = adapter.normalizer.OT_BOOKS.union(adapter.normalizer.APOCRYPHA_BOOKS)
    build_index(
        adapter, 
        lxx_books, 
        "LXX", 
        os.path.join(data_dir, "greek_index_lxx.pkl.gz")
    )

if __name__ == "__main__":
    main()
