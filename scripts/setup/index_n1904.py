import numpy as np
from tf.app import use
from sentence_transformers import SentenceTransformer
import os
import pickle

def run_indexing():
    print("Loading Text-Fabric N1904...")
    # Load TF app
    A = use('CenterBLC/N1904', version='1.0.0', hoist=False)
    F, T, L = A.api.F, A.api.T, A.api.L
    
    print("Loading Ancient Greek SBERT (Embedder)...")
    # Using 'Paulanerus/AncientGreekVariantSBERT' which is fine-tuned for similarity
    model = SentenceTransformer('Paulanerus/AncientGreekVariantSBERT')

    print("Extracting verses and lemmas...")
    verses = F.otype.s('verse')
    data = []
    lemmatized_texts = []
    
    print(f"Processing {len(verses)} verses...")
    
    for v in verses:
        # 1. Get Metadata
        raw_text = T.text(v)
        section = T.sectionFromNode(v) # ('Matthew', 1, 1)
        ref = f"{section[0]} {section[1]}:{section[2]}"
        
        # 2. Extract Lemmas from TF
        # Iterate words in verse
        words = L.d(v, otype='word')
        verse_lemmas = []
        for w in words:
            # Check for punctuation? TF usually separates punct.
            # We want meaningful lemmas.
            # Filter out punctuation if possible? 
            # In N1904, punctuation are distinct nodes or features?
            # Let's trust F.lemma.v(w). If it's punctuation, lemma might be empty or the punct itself.
            lemma = F.lemma.v(w)
            if lemma:
                verse_lemmas.append(lemma)
                
        lemma_string = " ".join(verse_lemmas)
        
        data.append({
            "node": v,
            "text": raw_text,
            "ref": ref,
            "lemmas": lemma_string
        })
        lemmatized_texts.append(lemma_string)

    # 3. Generate Embeddings
    print("Generating Semantic Vectors (Logion)...")
    # Batch encoding
    embeddings = model.encode(lemmatized_texts, show_progress_bar=True, convert_to_numpy=True)

    # 4. Save
    output_dir = "data"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"Saving to {output_dir}...")
    np.save(os.path.join(output_dir, "n1904_vectors.npy"), embeddings)
    np.save(os.path.join(output_dir, "n1904_nodes.npy"), np.array([d["node"] for d in data]))
    
    # Save metadata for the service
    with open(os.path.join(output_dir, "n1904_metadata.pkl"), "wb") as f:
         pickle.dump(data, f)
         
    print(f"Indexing complete. {len(embeddings)} vectors saved.")

if __name__ == "__main__":
    run_indexing()
