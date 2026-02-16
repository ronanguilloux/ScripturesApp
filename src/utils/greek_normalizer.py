import unicodedata

class GreekNormalizer:
    @staticmethod
    def strip_accents(text: str) -> str:
        """
        Strips all diacritics (accents, breathings, iota subscripts) from Greek text.
        Returns the lowercase, unaccented base form.
        Example: "εἴληφα" -> "ειληφα"
        """
        if not text:
            return ""
            
        # NFD decompose
        normalized = unicodedata.normalize('NFD', text)
        
        # Filter out non-spacing marks (Mn)
        stripped = "".join(c for c in normalized if unicodedata.category(c) != 'Mn')
        
        # NFC compose and lowercase
        return unicodedata.normalize('NFC', stripped).lower()
