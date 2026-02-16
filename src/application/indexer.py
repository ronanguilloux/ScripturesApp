import os
import pickle
import time
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from application.services import AdapterFactory

class SemanticIndexer:
    def __init__(self, model_name: str = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', data_dir: Optional[str] = None):
        self.model_name = model_name
        # Default to project root/data if not provided
        if not data_dir:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # src/application -> src -> root -> data
            project_root = os.path.dirname(os.path.dirname(current_dir))
            self.data_dir = os.path.join(project_root, "data")
        else:
            self.data_dir = data_dir
            
    def run(self, translations: List[str] = ["TOB", "BJ"]):
        print("Initializing Adapter...")
        adapter = AdapterFactory.get()
        normalizer = adapter.normalizer
        
        print(f"Loading Model: {self.model_name}...")
        model = SentenceTransformer(self.model_name)
        
        all_verses: List[Dict] = []
        texts_to_encode: List[str] = []
        
        print(f"Fetching verses for translations: {translations}...")
        
        # Sort by book_order
        sorted_codes = sorted(normalizer.book_order.keys(), key=lambda k: normalizer.book_order[k])
        
        count = 0
        for code in sorted_codes:
            # We assume TOB/BJ cover standard books.
            
            # Helper to find chapter limit?
            # We'll use the safe discovery loop as before.
            
            print(f"Processing {code}...")
            
            for tr in translations:
                current_ch = 1
                while True:
                    # Get chapter verses
                    verses = adapter.get_chapter(code, current_ch, tr)
                    if not verses:
                        if current_ch > 150: # Safe guard
                             break
                        if current_ch > 1: # End of book likely
                            break
                        if current_ch == 1: # Book might not allow ch 1? or missing.
                             break
                    
                    for v in verses:
                        raw_text = v.text.strip()
                        if not raw_text: continue
                        
                        # Filter out garbage (e.g. brackets, single chars)
                        if len(raw_text) < 5 and not any(c.isalpha() for c in raw_text):
                             continue
                        if raw_text == "]" or raw_text == "[": continue
                        
                        text = raw_text
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
                        count += 1
                    
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
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        output_path = os.path.join(self.data_dir, "bible_vectors.pkl")
        
        payload = {
            "metadata": all_verses,
            "embeddings": embeddings,
            "model": self.model_name
        }
        
        with open(output_path, "wb") as f:
            pickle.dump(payload, f)
            
        print(f"Saved index to {output_path}")
