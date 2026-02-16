from contextlib import asynccontextmanager
import os
import pickle
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sentence_transformers import SentenceTransformer
import uvicorn

# Global state
model = None
embeddings = None
metadata = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, embeddings, metadata
    
    # Load Model
    print("Loading model...")
    # Use same model as indexer
    model_name = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    model = SentenceTransformer(model_name)
    
    # Load Index
    print("Loading index...")
    # Determine path relative to this file
    # src/api/semantic_search.py -> src/api -> src -> root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    if os.path.basename(project_root) == "src": # Safety check if resolving symlinks weirdly or structure changed
         project_root = os.path.dirname(project_root)
    
    # Actually simpler: just go up 3 levels
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    data_path = os.path.join(project_root, "data", "bible_vectors.pkl")
    
    import gzip
    gz_path = data_path + ".gz"
    
    if os.path.exists(gz_path):
        print(f"Loading compressed index from {gz_path}...")
        with gzip.open(gz_path, "rb") as f:
            data = pickle.load(f)
    elif os.path.exists(data_path):
        print(f"Loading index from {data_path}...")
        with open(data_path, "rb") as f:
            data = pickle.load(f)
    else:
        print(f"Index not found at {data_path} or .gz. Please run indexer.")
        model = None
        return
            
    embeddings = data["embeddings"]
    metadata = data["metadata"]
    print(f"Loaded {len(metadata)} verses.")
    
    yield
    # Cleanup code if needed

app = FastAPI(title="ScripturesApp Search Service", lifespan=lifespan)

class SearchQuery(BaseModel):
    query: str
    limit: int = 10
    translation: Optional[str] = None # Filter by translation (e.g. TOB)
    book: Optional[str] = None # Filter by book

class SearchResult(BaseModel):
    ref: str
    text: str
    translation: str
    score: float
    book: str
    chapter: int
    verse: int

@app.post("/search", response_model=List[SearchResult])
async def search(query: SearchQuery):
    if model is None or embeddings is None:
        raise HTTPException(status_code=503, detail="Search service not ready (index not loaded)")
        
    # Encode query
    q_vec = model.encode([query.query], convert_to_numpy=True)
    
    # Cosine Similarity
    
    # Using sentence_transformers util
    from sentence_transformers import util
    scores = util.cos_sim(q_vec, embeddings)[0] # Shape (N_verses,)
    
    # Top K
    top_results_idx = np.argsort(-scores.cpu().numpy())[:query.limit * 5] # Fetch more for filtering
    
    results = []
    for idx in top_results_idx:
        meta = metadata[idx]
        score = float(scores[idx])
        
        # Filtering
        if query.translation and meta["translation"].upper() != query.translation.upper():
            continue
        if query.book and meta["book"] != query.book:
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
        
        if len(results) >= query.limit:
            break
            
    return results

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
