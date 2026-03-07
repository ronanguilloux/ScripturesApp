
import spacy
import warnings
import inspect

warnings.filterwarnings("ignore")

try:
    nlp = spacy.load("grc_odycy_joint_sm")
except OSError:
    print("Error: Model not found")
    exit(1)

text = "ἀφέντες"
doc = nlp(text)

print(f"Analyzing: {text}")

for token in doc:
    print(f"Token: {token.text}")
    print("-" * 20)
    
    # Standard attributes
    print("Standard Attributes:")
    attributes = [
        "lemma_", "pos_", "tag_", "dep_", "shape_", "is_alpha", "is_stop", 
        "is_punct", "like_num", "ent_type_", "ent_iob_"
    ]
    for attr in attributes:
        val = getattr(token, attr, "N/A")
        print(f"  {attr}: {val}")

    # Morphology
    print("\nMorphology (Full):")
    print(f"  {token.morph}")

    # Custom extensions (underscore)
    print("\nCustom Extensions (_):")
    for name, _ in inspect.getmembers(token._):
        if not name.startswith("__"):
            try:
                val = getattr(token._, name)
                print(f"  {name}: {val}")
            except:
                pass

    # All dir()
    print("\nAll Attributes (dir):")
    # Filter for interesting public attributes
    for d in dir(token):
        if not d.startswith("_") and d not in attributes:
            # Try to get value if simple type
            try:
                val = getattr(token, d)
                if isinstance(val, (str, int, float, bool, list, dict)):
                    # print(f"  {d}: {val}") # Too noisy, maybe just list them?
                    pass
            except:
                pass
                
    # Vector Check
    print(f"\nHas Vector: {token.has_vector}")
    if token.has_vector:
        print(f"Vector Norm: {token.vector_norm}")

