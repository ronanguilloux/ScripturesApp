Direct Lookup Bypass: If OdyCy fails (returns the word itself or unknown), try to find the word in Text-Fabric by stripping accents from both the query and the TF index.
Normalization Utility: Create a GreekNormalizer class that can strip all diacritics (accents, breathings, iota subscripts) to produce a "naked" Greek string (e.g., εἴληφα -> ειληφα, είληφα -> ειληφα).
Convert είληφα -> ειληφα (unaccented).
Convert TF words: εἴληφα -> ειληφα.
Match! We found εἴληφα.
Look up lemma of εἴληφα in TF -> λαμβάνω.
This completely bypasses OdyCy for this case, OR we can feed εἴληφα to OdyCy if we really want to use it. But TF is the ground truth for this app.
Requires to Create a utility to strip all diacritics using unicodedata decomposition and filtering.
oot Cause: Mismatch between user input (monotonic/unaccented) and index/model expectation (polytonic).
Fix Strategy: "Accent-Insensitive Lookup".
Feasibility: High. Python's unicodedata handles this well.
Performance: Acceptable for CLI/Worker (~100-200ms overhead to scan index).
Implementation:
Add strip_accents helper.
OdyCy & Polytonic Greek: External Validation
Findings
Designed for Ancient Greek: OdyCy is explicitly built for Ancient Greek NLP [1][2].
Polytonic vs. Monotonic: Ancient Greek uses the polytonic system (multi-accent). Modern Greek uses the monotonic system (single accent) introduced in 1982 [5][6].
Diacritic Importance: In Ancient Greek, diacritics (accents/breathings) are semantically and morphologically significant. A model trained on this data expects these features for accurate disambiguation.
No "Normalization" Feature: Documentation lists lemmatization, POS tagging, and parsing, but does not list "monotonic-to-polytonic normalization" as a feature [1][3].
Conclusion
The search results validate the empirical findings: OdyCy expects polytonic input because it is an Ancient Greek model. It treats monotonic or unaccented input as "out of distribution" or incorrect orthography, leading to lemmatization failures.