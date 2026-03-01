#!/usr/bin/env python3
"""
septantism_worker.py — OdyCy-powered NLP worker for detecting Septantisms.

Runs in the .venv-spacy environment.
Takes JSON from stdin: [{"id": "...", "source_text": "...", "target_text": "...", ...}, ...]
Outputs JSON to stdout: [{"id": "...", "matches": ["lemma1", "lemma2"], "score": 2}, ...]
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
    # This aligns with scientific measurement of text reuse
    TARGET_POS = {"NOUN", "VERB", "ADJ"}

    for pair in pairs:
        pair_id = pair.get("id")
        source_text = pair.get("source_text", "")
        target_text = pair.get("target_text", "")

        if not source_text or not target_text:
            results.append({"id": pair_id, "matches": [], "score": 0, "similarity": 0.0})
            continue

        source_text = unicodedata.normalize("NFC", source_text)
        target_text = unicodedata.normalize("NFC", target_text)

        doc_source = nlp(source_text)
        doc_target = nlp(target_text)

        source_lemmas = set()
        source_lemma_to_word = {}
        for token in doc_source:
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

        results.append({
            "id": pair_id,
            "matches": matches,
            "score": len(common_lemmas),
            "similarity": similarity
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
