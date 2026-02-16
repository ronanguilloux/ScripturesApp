import os
import pickle
import numpy as np
import time
from typing import List, Optional, Dict
from sentence_transformers import SentenceTransformer
from domain.models import SearchResult

class GreekSearchService:
    def __init__(self, model_name: str = 'Paulanerus/AncientGreekVariantSBERT', data_dir: Optional[str] = None):
        self.model_name = model_name
        self.model = None
        self.vector_index = None # numpy array
        self.node_index = None   # numpy array
        self.metadata_map = {}   # dict mapping node -> metadata
        
        # Determine path
        if not data_dir:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            self.data_dir = os.path.join(project_root, "data")
        else:
            self.data_dir = data_dir
            
    def load(self):
        print(f"Loading Greek Search Model: {self.model_name}...")
        self.model = SentenceTransformer(self.model_name)
        
        vector_path = os.path.join(self.data_dir, "n1904_vectors.npy")
        node_path = os.path.join(self.data_dir, "n1904_nodes.npy")
        meta_path = os.path.join(self.data_dir, "n1904_metadata.pkl")
        
        if not os.path.exists(vector_path) or not os.path.exists(node_path):
            print(f"Greek Index not found at {self.data_dir}. Greek semantic search will be unavailable.")
            return

        print(f"Loading Greek Index from {self.data_dir}...")
        try:
            self.vector_index = np.load(vector_path)
            self.node_index = np.load(node_path)
            
            with open(meta_path, "rb") as f:
                # List of dicts
                raw_meta = pickle.load(f)
                # Map node -> dict for fast lookup
                self.metadata_map = {item["node"]: item for item in raw_meta}
                
            print(f"Loaded {len(self.vector_index)} Greek vectors.")
        except Exception as e:
            print(f"Error loading Greek index: {e}")

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        if self.model is None or self.vector_index is None:
            return []
            
        # Encode query (Raw text query, since we don't have OdyCy)
        # Ideally user provides lemmatized query or we rely on BERT to handle it.
        start_time = time.time()
        q_vec = self.model.encode([query], convert_to_numpy=True)
        
        # Cosine Similarity
        from sentence_transformers import util
        # q_vec shape (1, 768), vector_index shape (N, 768)
        scores = util.cos_sim(q_vec, self.vector_index)[0] 
        
        # Top K
        # -scores for descending sort
        top_results_idx = np.argsort(-scores.cpu().numpy())[:limit]
        
        results = []
        for idx in top_results_idx:
            node_id = self.node_index[idx]
            score = float(scores[idx])
            
            meta = self.metadata_map.get(node_id)
            if not meta: continue
            
            # Parse ref "Matthew 1:1" to parts
            # This is a bit hacky, strict ref parsing would be better but simple string split works for N1904 refs
            parts = meta["ref"].split(" ")
            book = parts[0]
            chapter_verse = parts[1].split(":")
            chapter = int(chapter_verse[0])
            verse = int(chapter_verse[1])
            
            results.append(SearchResult(
                ref=meta["ref"],
                text=meta["text"],
                translation="N1904",
                score=score,
                book=book,
                chapter=chapter,
                verse=verse
            ))
            
        print(f"Greek Search '{query}' took {time.time() - start_time:.4f}s")
        return results
