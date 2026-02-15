ScripturesApp Feature Roadmap
Goal
To transform ScripturesApp from a powerful lookup tool into a comprehensive study platform by integrating AI, interactive interfaces, and deep analytical capabilities.

User Review Required
NOTE

Detailed specification files have been created for each major feature.

Semantic Search Plan
Interactive TUI Plan
Analytics Plan
Master Protocol
1. Semantic Search (AI Integration)
Goal: Offline, multilingual semantic search using local LLM embeddings.

Support: English <-> French <-> Biblical Languages (via translation matching).
Tech: Ollama (preferred) or local Python models.
2. Interactive TUI
Goal: A Textual-based persistent application with split views.

Priority: High. Transforms the user experience.
3. "Deep Dive" Analytics
Goal: Philological tools leveraging N1904 (Greek).

Status Update: TF N1904 data verified. 
lemma
 feature is ready for use.
Scope: Greek Only for Phase 1. Hebrew/Macula analysis is deprioritized.
See: 
plan_analytics.md
4. Reading Plans
Goal: Trackable reading schedules.

Implementation: Simple JSON tracking + CLI progress bar.
Proposed Priority Order
Semantic Search: High value, distinct from current regex search.
Analytics (Greek): Low complexity, high value for greek students/scholars.
TUI: High effort, but high reward for usability.