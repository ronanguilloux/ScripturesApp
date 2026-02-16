from enum import Enum
import unicodedata

class CrossReferenceType(str, Enum):
    # Standard Parallel
    PARALLEL = "parallel" # Same event/teaching
    # Quotation
    QUOTATION = "quotation" # Explicit quote "As it is written..."
    ALLUSION = "allusion" # Indirect reference
    # Thematic
    THEMATIC = "thematic" # Shared theme (e.g. "Light")
    # Prophecy
    PROPHECY_FULFILLMENT = "fulfillment" 
    PROPHECY_PREDICTION = "prediction"
    # Structural
    CONTRAST = "contrast" # "You heard X, but I say Y"

class GreekNormalizer:
    """
    Utility for normalizing Greek text for search and comparison.
    Handles accent removal, case normalization, and various Greek unicode equivalences.
    """
    
    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalize Greek text:
        1. NFD decomposition
        2. Strip accents/diacritics
        3. Lowercase
        4. NFC composition
        """
        if not text: return ""
        
        # 1. NFD to separate combining chars
        d = unicodedata.normalize('NFD', text)
        
        # 2. Filter non-spacing marks (Mn)
        filtered = "".join([c for c in d if unicodedata.category(c) != 'Mn'])
        
        # 3. Lowercase
        lower = filtered.lower()
        
        # 4. NFC
        return unicodedata.normalize('NFC', lower)
        
    @staticmethod
    def strip_accents(text: str) -> str:
        """Removes accents but keeps case."""
        if not text: return ""
        d = unicodedata.normalize('NFD', text)
        filtered = "".join([c for c in d if unicodedata.category(c) != 'Mn'])
        return unicodedata.normalize('NFC', filtered)
