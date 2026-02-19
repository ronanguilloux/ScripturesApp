I have explored the capabilities of SpaCy and OdyCy for Ancient Greek. Here is my Prescription for enhancing the greek command. Please review and validate which features you would like me to implement.

1. Semantic Similarity ("Related Words")
Concept: Find words that are used in similar contexts (e.g., "speak" → "say", "shout"). Feasibility: High. The model has word vectors (has_vector: True). I verified that ἀφέντες (leaving) has measurable similarity to ἀφίημι (to send away) and εἰπόντες (speaking - likely due to participle usage context). Usage: biblecli greek "logos" --similar -> Returns top 5 related words.

2. Named Entity Recognition (NER)
Concept: Identify if the word is a Person, Location, Group, etc. Feasibility: Medium. OdyCy has entity recognition, but it is sparse for common words. It is powerful for proper nouns (e.g., "Jesus", "Jerusalem"). Usage: Automatically tag entities in the output (e.g., Entity: PERSON).

3. Syntax Visualization (ASCII Tree)
Concept: Instead of just Dep: nsubj → verb, visualize the tree structure of the phrase. Feasibility: High. We can use spacy.displacy (or a text-based equivalent) to render a small tree in the CLI. Usage: Better visualization of how words connect in the input phrase.

4. Declension/Conjugation Hints
Concept: Based on the morphology (e.g., Case=Nom, Gender=Masc), we can infer the "paradigm" it belongs to. Feasibility: Medium. OdyCy gives the tags, but not the full table. I can, however, provide a "Paradigm Hint" summary (e.g., "Nominative Plural Masculine Participle").

5. Vocabulary Usage Stats (Corpus Frequency)
Concept: Show how often this Lexeme appears in the New Testament (requires access to the full text/frequencies). Feasibility: High (if we use our existing Text-Fabric or a frequency list). OdyCy itself doesn't "know" the Bible frequency, but we have the data.

Recommendation
I suggest we prioritize #1 (Semantic Similarity) and #3 (Syntax Tree) as they add unique value not easily visible in a dictionary.
