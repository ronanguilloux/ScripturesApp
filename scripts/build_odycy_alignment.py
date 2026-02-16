
import sys
import os
import json
import spacy
from collections import Counter

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.adapters.text_fabric_adapter import TextFabricAdapter
from src.utils.greek_normalizer import GreekNormalizer

def main():
    print("Initialize TextFabricAdapter...")
    adapter = TextFabricAdapter(data_dir=os.path.expanduser("~/text-fabric-data"))
    adapter.build_stripped_index()
    
    print("Loading OdyCy...")
    nlp = spacy.load("grc_odycy_joint_sm")
    
    # 1. Extract Unique N1904 Word Forms -> Lemmas
    form_lemma_map = {} # surface -> true_lemma
    
    print("Scanning N1904...")
    api = adapter.n1904.api
    F = api.F
    
    unique_forms = set()
    
    for w in F.otype.s('word'):
        surface = api.T.text(w).strip().rstrip(",.;·")
        lemma = F.lemma.v(w)
        if surface and lemma:
            unique_forms.add(surface)
            form_lemma_map[surface] = lemma
    
    print(f"Found {len(unique_forms)} unique forms in N1904.")
    
    # Scan LXX if available
    print("Scanning LXX...")
    try:
        lxx_api = adapter.lxx.api
        lxx_F = lxx_api.F
        
        for w in lxx_F.otype.s('word'):
            surface = lxx_api.T.text(w).strip().rstrip(",.;·")
            lemma = lxx_F.lemma.v(w)
            if surface and lemma:
                unique_forms.add(surface)
                # LXX lemma overrides N1904 if different (or adds new)
                if surface not in form_lemma_map:
                    form_lemma_map[surface] = lemma
        
        print(f"Total {len(unique_forms)} unique forms after LXX.")
    except Exception as e:
        print(f"LXX scan skipped: {e}", file=sys.stderr)

    sorted_forms = sorted(list(unique_forms))
    print(f"Found {len(sorted_forms)} unique surface forms.")
    
    # 2. Run OdyCy on all forms
    print("Running OdyCy alignment...")
    
    correction_map = {}
    
    # Batch process for speed? 
    # nlp.pipe yields docs
    batch_size = 1000
    
    for i in range(0, len(sorted_forms), batch_size):
        batch = sorted_forms[i:i+batch_size]
        docs = list(nlp.pipe(batch))
        
        for form, doc in zip(batch, docs):
            odycy_lemma = doc[0].lemma_
            true_lemma = form_lemma_map[form]
            
            # Normalization check
            # strict comparison might mismatch accents
            # but we want to map OdyCy's output EXACTLY to TF's lemma
            
            if odycy_lemma != true_lemma:
                # Potential correction candidate
                # e.g. odycy="ειλημμένος", true="λαμβάνω"
                
                # Check if it's just accent difference?
                if GreekNormalizer.strip_accents(odycy_lemma) == GreekNormalizer.strip_accents(true_lemma):
                    continue
                    
                # It's a real difference (suppletion, participle, error)
                correction_map[odycy_lemma] = true_lemma
                
                # Also map the stripped version of OdyCy lemma?
                # No, let's keep it exact for now.
                
        if i % 5000 == 0:
            print(f"Processed {i}...")
            
    # 3. Save
    print(f"Index built. Found {len(correction_map)} corrections.")
    output_path = os.path.join(project_root, "data", "odycy_alignment.json")
    
    with open(output_path, "w") as f:
        json.dump(correction_map, f, indent=2, ensure_ascii=False)
        
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()
