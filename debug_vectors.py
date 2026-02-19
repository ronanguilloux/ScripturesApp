
import spacy
import warnings

warnings.filterwarnings("ignore")

try:
    nlp = spacy.load("grc_odycy_joint_sm")
except OSError:
    print("Error: Model not found")
    exit(1)

text = "ἀφέντες"
doc = nlp(text)
token = doc[0]

print(f"Token: {token.text}")
print(f"Has Vector: {token.has_vector}")

if token.has_vector:
    # Try finding similar words
    # Since we don't have the full vocab in memory easily accessible for similarity search without iterating,
    # we can try comparing against a known list of words to see if similarity works.
    
    comparisons = ["εἰπόντες", "λέγω", "θεός", "ἀνήρ", "ἀφίημι"]
    print("\nSimilarities:")
    for w in comparisons:
        doc2 = nlp(w)
        sim = token.similarity(doc2[0])
        print(f"  vs {w}: {sim:.4f}")

