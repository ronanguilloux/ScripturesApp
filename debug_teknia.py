from tf.app import use
import unicodedata

def debug_teknia():
    try:
        A = use("CenterBLC/N1904", version="1.0.0", silent=True)
        F = A.api.F
        T = A.api.T
        
        target = "Τεκνία"
        target_norm = unicodedata.normalize('NFC', target)
        
        print(f"Searching for word '{target}' (Norm: {target_norm})...")
        
        found = False
        for w in F.otype.s('word'):
            # Check Text (Surface)
            text = T.text(w)
            text_norm = unicodedata.normalize('NFC', text.strip())
            
            # Remove punctuation from text for comparison if needed
            # Simple check
            if target_norm in text_norm:
                 found = True
                 lemma = F.lemma.v(w)
                 print(f"Match found!")
                 print(f"  Word Node: {w}")
                 print(f"  Surface (T.text): '{text}'")
                 print(f"  Lemma (F.lemma): '{lemma}'")
                 print(f"  Context: {T.text(w)}")
                 break
        
        if not found:
             print("Not found via exact surface match.")
             
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_teknia()
