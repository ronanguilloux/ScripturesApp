#!/usr/bin/env python3
"""
intertext_worker.py — OdyCy-powered NLP worker for characterizing Intertextuality.

Runs in the .venv-spacy environment.
Takes JSON from stdin: [{"id": "...", "source_text": "...", "target_text": "...", ...}, ...]
Outputs JSON to stdout: [{"id": "...", "matches": ["lemma1", "lemma2"], "score": 2, "intertext_flags": ["E", "L"]}, ...]
"""
import sys
import os
import json
import warnings
import unicodedata

warnings.filterwarnings("ignore")

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

import spacy

_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("grc_odycy_joint_sm")
        except OSError:
            _nlp = spacy.load("grc_odycy_joint_sm")
    return _nlp

def analyze_pairs(pairs):
    nlp = get_nlp()
    results = []

    # Filter to only keep significant lexical words
    TARGET_POS = {"NOUN", "VERB", "ADJ"}
    
    # Lemmes marquant une citation explicite
    CITATION_LEMMAS = {"γράφω", "πληρόω", "λέγω", "εἶπον"}

    for pair in pairs:
        pair_id = pair.get("id")
        source_text = pair.get("source_text", "")
        target_text = pair.get("target_text", "")

        if not source_text or not target_text:
            results.append({"id": pair_id, "matches": [], "score": 0, "similarity": 0.0, "intertext_flags": ["NE", "NL"]})
            continue

        source_text = unicodedata.normalize("NFC", source_text)
        target_text = unicodedata.normalize("NFC", target_text)

        doc_source = nlp(source_text)
        doc_target = nlp(target_text)

        source_lemmas = set()
        source_lemma_to_word = {}
        has_citation_lemma = False
        
        for token in doc_source:
            # Check for explicit citation markers first
            if token.lemma_ in CITATION_LEMMAS:
                has_citation_lemma = True
                
            if token.pos_ in TARGET_POS and token.lemma_ != "-":
                source_lemmas.add(token.lemma_)
                if token.lemma_ not in source_lemma_to_word:
                    source_lemma_to_word[token.lemma_] = []
                source_lemma_to_word[token.lemma_].append(token.text)

        target_lemmas = set()
        target_lemma_to_word = {}
        for token in doc_target:
            if token.pos_ in TARGET_POS and token.lemma_ != "-":
                target_lemmas.add(token.lemma_)
                if token.lemma_ not in target_lemma_to_word:
                    target_lemma_to_word[token.lemma_] = []
                target_lemma_to_word[token.lemma_].append(token.text)
            
        common_lemmas = source_lemmas.intersection(target_lemmas)
        union_lemmas = source_lemmas.union(target_lemmas)
        
        similarity = 0.0
        if union_lemmas:
            similarity = len(common_lemmas) / len(union_lemmas)

        matches = []
        for lemma in common_lemmas:
            matches.append({
                "lemma": lemma,
                "source_words": list(set(source_lemma_to_word.get(lemma, []))),
                "target_words": list(set(target_lemma_to_word.get(lemma, [])))
            })

        # Qualification rules
        flag_e = "E" if has_citation_lemma else "NE"
        flag_l = "L" if similarity >= 0.8 else "NL"
        # Optional adjustment based on exact text matches or lower thresholds could be done here. Let's start with 0.8.

        results.append({
            "id": pair_id,
            "matches": matches,
            "score": len(common_lemmas),
            "similarity": similarity,
            "intertext_flags": [flag_e, flag_l]
        })

    return results

def main():
    try:
        input_data = sys.stdin.read()
        pairs = json.loads(input_data)
        
        results = analyze_pairs(pairs)
        
        print(json.dumps(results, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
