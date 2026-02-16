Add OT searching capability to the find command
The current search is limited to the New Testament (N1904) only. The LXX (Septuagint/Old Testament) corpus is loaded by the adapter but not queried during find operations.
We want to search both OT and NT, but NT should be the default and arguments/options should allow the user to search OT only, or both: 'nt', 'ot', 'both'.

- Update find_lemma() to also query self.lxx
- Merge results from both corpora
- Handle book code mapping for LXX books (Genesis, Exodus, etc.)
