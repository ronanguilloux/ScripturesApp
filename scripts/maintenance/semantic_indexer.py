import sys
import os
import pickle
import time
from typing import List, Dict
from sentence_transformers import SentenceTransformer

# Add src to path
# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if os.path.basename(project_root) == "scripts":
    project_root = os.path.dirname(project_root)
    
sys.path.append(project_root)

from src.application.services import AdapterFactory
from src.domain.models import Verse

def main():
    print("Initializing Adapter...")
    adapter = AdapterFactory.get()
    normalizer = adapter.normalizer
    
    print("Loading Model...")
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    
    # Translations to index
    translations = ["TOB", "BJ"]
    
    all_verses: List[Dict] = []
    texts_to_encode: List[str] = []
    
    print("Fetching verses...")
    # Iterate books
    # Sort by book_order
    sorted_codes = sorted(normalizer.book_order.keys(), key=lambda k: normalizer.book_order[k])
    
    for code in sorted_codes:
        # Determine strict book name for TOB
        n1904_name = normalizer.code_to_n1904.get(code)
        tob_book = normalizer.n1904_to_tob.get(n1904_name)
        
        if not tob_book:
            continue
            
        print(f"Processing {code}...")
        
        for tr in translations:
            # For each translation
            current_ch = 1
            while True:
                # Get chapter verses
                verses = adapter.get_chapter(code, current_ch, tr)
                if not verses:
                    if current_ch > 150: 
                         break
                    if current_ch > 1 and not verses:
                        break
                    if current_ch == 1:
                         break
                
                for v in verses:
                    if not v.text.strip(): continue
                    
                    text = v.text.strip()
                    ref = f"{code} {v.chapter}:{v.verse}"
                    
                    meta = {
                        "book": code,
                        "chapter": v.chapter,
                        "verse": v.verse,
                        "text": text,
                        "translation": tr,
                        "ref": ref
                    }
                    
                    all_verses.append(meta)
                    texts_to_encode.append(text)
                
                current_ch += 1
                
    print(f"Collected {len(all_verses)} verses.")
    
    if not all_verses:
        print("No verses found! Check data availability.")
        return

    print("Encoding...")
    start_time = time.time()
    embeddings = model.encode(texts_to_encode, batch_size=64, show_progress_bar=True, convert_to_numpy=True)
    end_time = time.time()
    print(f"Encoding took {end_time - start_time:.2f} seconds.")
    
    # Save
    data_dir = os.path.join(project_root, "data")
    if not os.path.exists(data_dir):
        # Fallback if running from weird location
        data_dir = os.path.join(os.getcwd(), "data")
        
    output_path = os.path.join(data_dir, "bible_vectors.pkl")
    
    payload = {
        "metadata": all_verses,
        "embeddings": embeddings,
        "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    }
    
    import gzip
    output_path_gz = output_path + ".gz"
    with gzip.open(output_path_gz, "wb") as f:
        pickle.dump(payload, f)
        
    print(f"Saved compressed index to {output_path_gz}")
    
    print(f"Saved index to {output_path}")

if __name__ == "__main__":
    main()
