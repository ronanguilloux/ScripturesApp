import os
import pickle
import numpy as np
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
from domain.models import SearchResult

class SemanticSearchService:
    def __init__(self, model_name: str = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', data_dir: Optional[str] = None):
        self.model_name = model_name
        self.model = None
        self.embeddings = None
        self.metadata = []
        
        # Determine path
        if not data_dir:
            # src/application/semantic_search.py -> src/application -> src -> root -> data
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            self.data_dir = os.path.join(project_root, "data")
        else:
            self.data_dir = data_dir
            
    def load(self):
        print(f"Loading Semantic Search Model: {self.model_name}...")
        self.model = SentenceTransformer(self.model_name)
        
        data_path = os.path.join(self.data_dir, "bible_vectors.pkl")
        if not os.path.exists(data_path):
            print(f"Index not found at {data_path}. Semantic search will be unavailable.")
            return
            
        print(f"Loading Index from {data_path}...")
        with open(data_path, "rb") as f:
            data = pickle.load(f)
            
        self.embeddings = data["embeddings"]
        self.metadata = data["metadata"]
        print(f"Loaded {len(self.metadata)} verses for search.")

    def search(self, query: str, limit: int = 10, translation: Optional[str] = None) -> List[SearchResult]:
        if self.model is None or self.embeddings is None:
            return []
            
        # Encode query
        q_vec = self.model.encode([query], convert_to_numpy=True)
        
        # Cosine Similarity
        from sentence_transformers import util
        scores = util.cos_sim(q_vec, self.embeddings)[0] # Shape (N_verses,)
        
        # Top K
        # Get top indices
        top_results_idx = np.argsort(-scores.cpu().numpy())[:limit * 5] # Fetch more for filtering
        
        results = []
        for idx in top_results_idx:
            meta = self.metadata[idx]
            score = float(scores[idx])
            
            # Filtering
            if translation and meta["translation"].upper() != translation.upper():
                continue
                
            results.append(SearchResult(
                ref=meta["ref"],
                text=meta["text"],
                translation=meta["translation"],
                score=score,
                book=meta["book"],
                chapter=meta["chapter"],
                verse=meta["verse"]
            ))
            
            if len(results) >= limit:
                break
                
        return results
