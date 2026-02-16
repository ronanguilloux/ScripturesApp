# Lemmatization Strategy Comparison

## Overview

This document compares two approaches for handling Greek lemmatization in the presence of monotonic/unaccented input when using a polytonic-trained model (OdyCy).

## Current Implementation: OdyCy-First with Alignment

### Architecture

**Three-Layer Strategy:**
1. **OdyCy Primary** → Check alignment map → Return if corrected
2. **Polytonic Restoration** → Strip accents → Find polytonic variant in N1904 → Feed to OdyCy → Validate
3. **Text-Fabric Fallback** → Direct accent-insensitive TF lookup

### Key Features
- Uses OdyCy as primary lemmatizer
- Leverages `odycy_alignment.json` (9,677 corpus-wide corrections)
- Polytonic restoration attempts to "fix" monotonic input for OdyCy
- Fuzzy matching (movable nu, ending swaps like -αν → -ον)
- Text-Fabric is fallback validator, not primary source

### Performance
- **Accuracy:** ~90% on actual NT forms
- **Speed:** ~150-200ms per query
- **Coverage:** Handles unknown forms via OdyCy's ML capabilities

## Proposed Approach: TF-First Direct Lookup

### Philosophy

**"Text-Fabric is ground truth"** - Since the N1904 corpus in TF already contains all forms with their lemmas, use it directly.

### Architecture

**Simplified Flow:**
1. **Strip accents** from both input and TF index
2. **Direct match** → Return lemma from TF
3. **Optional OdyCy** only for unknown forms (OT/LXX or rare cases)

### Example
```
Input: είληφα (monotonic)
→ Strip: ειληφα
→ TF: εἴληφα (polytonic) → Strip: ειληφα
→ Match! Return: λαμβάνω
```

### Expected Benefits
- **Simpler:** 1-2 layers instead of 3
- **Faster:** ~50-100ms (direct lookup)
- **More accurate:** 100% on known NT forms (authoritative source)
- **Clearer semantics:** "If in corpus, use corpus lemma"

## Comparison Matrix

| Aspect | Current (OdyCy-First) | Proposed (TF-First) |
|--------|---------------------|-------------------|
| **Primary Strategy** | OdyCy + Alignment corrections | Direct TF accent-insensitive lookup |
| **OdyCy Role** | Primary lemmatizer | Optional/secondary |
| **TF Role** | Fallback validator | Ground truth source |
| **Accent Handling** | Restore polytonic → Feed OdyCy | Strip from both sides → Match |
| **Complexity** | 3 layers | 1-2 layers |
| **NT Accuracy** | ~90% measured | ~100% expected (TF is authoritative) |
| **Speed** | 150-200ms | 50-100ms expected |
| **Unknown Forms** | Handles via OdyCy ML | Requires fallback to OdyCy |
| **LXX Support** | Works (via OdyCy) | Limited (TF lacks lemma features) |

## Similarities

Both approaches:
- ✅ Recognize the root problem: monotonic input vs polytonic-trained model
- ✅ Use accent-stripping (`GreekNormalizer.strip_accents`)
- ✅ Validate against Text-Fabric
- ✅ Achieve good real-world accuracy on NT forms

## Philosophical Divergence

### Current: "OdyCy is smart, TF is backup"
- OdyCy lemmatizes using ML (recognizes morphological patterns)
- Alignment map corrects systematic errors
- TF catches edge cases

### Proposed: "TF is truth, OdyCy is optional"
- TF has all NT forms already mapped to lemmas
- Direct lookup is simplest and fastest
- OdyCy only needed for unknown forms or LXX

## Evaluation

### Strengths of Current Approach
✅ **Proven:** ~90% accuracy measured on NT forms  
✅ **Sustainable:** Corpus-wide alignment (not word-specific patches)  
✅ **Robust:** Handles morphological variations via OdyCy's ML  
✅ **LXX Ready:** Can expand to Old Testament

### Strengths of Proposed Approach
✅ **Simpler:** Fewer fallback layers  
✅ **Faster:** Direct TF lookup is more efficient  
✅ **More Accurate:** 100% on known NT forms (authoritative)  
✅ **Architecturally Clean:** Aligns with "TF is ground truth" philosophy

### Weaknesses of Current Approach
⚠️ **Complex:** Three layers of fallbacks  
⚠️ **Slower:** OdyCy processing adds latency  
⚠️ **Indirect:** Goes through ML model even when TF has answer

### Weaknesses of Proposed Approach
⚠️ **Loses OdyCy's Intelligence:** No morphological analysis for unknowns  
⚠️ **LXX Challenge:** TF lacks lemma features for Septuagint  
⚠️ **Requires Completeness:** Assumes TF index is comprehensive

## Optimal Hybrid Strategy

Combine strengths of both:

```python
def hybrid_lemmatize(word, adapter):
    """
    1. TF direct lookup (accent-insensitive) → 95%+ coverage
    2. OdyCy + alignment → Handles unknowns
    3. Fuzzy matching → Edge cases (movable nu, etc.)
    """
    # Layer 1: TF First (Fast Path)
    stripped = strip_accents(word)
    tf_lemma = adapter.find_lemma_by_stripped_surface(stripped)
    if tf_lemma:
        return tf_lemma
    
    # Layer 2: OdyCy + Alignment (Unknown Forms)
    odycy_lemma = lemmatize(word)
    aligned = check_alignment(odycy_lemma)
    if aligned != odycy_lemma:
        return aligned
    
    # Layer 3: Polytonic Restoration + Fuzzy
    # (Current smart_lemmatize logic)
    ...
```

## Recommendation

**For NT-focused applications (this app):**

The proposed TF-first approach is **architecturally superior** because:
1. It aligns with the corpus-based design philosophy
2. Simplifies logic while improving accuracy
3. Maintains OdyCy as fallback for robustness

**Implementation Path:**
1. Invert current logic: Try TF direct lookup first
2. Keep OdyCy + alignment as fallback (don't remove it)
3. Retain fuzzy matching for edge cases
4. Measure accuracy improvement (expect 90% → 95%+)

This preserves the robustness of the current system while optimizing the common case (corpus words).

## References

- Current implementation: `src/application/workers/find_worker.py::smart_lemmatize`
- Alignment map: `data/odycy_alignment.json` (9,677 corrections)
- Accuracy analysis: `docs/lemmatization/accuracy_report.md`
- OdyCy model: `grc_odycy_joint_sm` (Ancient Greek NLP)
