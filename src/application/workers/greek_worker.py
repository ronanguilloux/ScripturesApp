#!/usr/bin/env python3
"""
greek_worker.py — OdyCy-powered Greek NLP analysis worker.

Runs in the .venv-spacy (Python 3.13) environment.
Called by the main CLI via subprocess.

Usage:
    .venv-spacy/bin/python3 src/application/workers/greek_worker.py <word>

Output: JSON object with analysis results to stdout.
"""
import sys
import os
import json
import argparse
import warnings

warnings.filterwarnings("ignore")

# Add project root to path for imports if needed (though we might not need project modules for pure spacy)
# Copied from find_worker.py to be safe
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

import spacy

# Global NLP model
_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        import warnings
        warnings.filterwarnings("ignore")
        try:
            _nlp = spacy.load("grc_odycy_joint_sm")
        except OSError:
            # Fallback if sm not found? or try trf?
            # find_worker uses joint_sm, assuming it exists.
            _nlp = spacy.load("grc_odycy_joint_sm")
    return _nlp

def analyze(text: str):
    nlp = get_nlp()
    doc = nlp(text)
    
    results = []
    
    for token in doc:
        # Extract interesting attributes
        # Filter out empty/irrelevant ones
        
        token_data = {
            "text": token.text,
            "lemma": token.lemma_,
            "norm": token.norm_, # Lexeme/Normalized form
            "pos": token.pos_,
            "pos_explain": spacy.explain(token.pos_),
            "tag": token.tag_,
            "tag_explain": spacy.explain(token.tag_),
            "dep": token.dep_,
            "dep_explain": spacy.explain(token.dep_),
            "head": token.head.text,
            "head_pos": token.head.pos_,
            "head_lemma": token.head.lemma_,
            "morph": token.morph.to_dict(),
            "is_alpha": token.is_alpha,
            "is_punct": token.is_punct,
            "is_digit": token.is_digit,
            "like_num": token.like_num,
            "ent_type": token.ent_type_,
        }
        
        # Clean up: Remove False booleans if "no value" means irrelevant? 
        # User said: "'is_punt' for verbs has no value... Pronoun Type has no value for verbs"
        # For booleans like is_punct, False is a value (it is NOT punct). 
        # But maybe user means specific morph attributes? 
        # "all attributes and morphology analysis... as long as it has a value"
        
        # Let's keep booleans if they are True? 
        # Or just keep everything and let CLI filter? 
        # CLI filtering is better for presentation.
        # But user specifically mentioned 'is_punct' for verbs has NO VALUE. 
        # Spacy returns False. 
        # I'll return everything and let CLI decide presentation.
        
        results.append(token_data)
        
    return results

def main():
    parser = argparse.ArgumentParser(description="OdyCy Greek Analysis")
    parser.add_argument("text", help="Greek text to analyze")
    args = parser.parse_args()
    
    try:
        data = analyze(args.text)
        print(json.dumps(data, ensure_ascii=False))
    except Exception as e:
        json.dump({"error": str(e)}, sys.stdout)
        sys.exit(1)

if __name__ == "__main__":
    main()
