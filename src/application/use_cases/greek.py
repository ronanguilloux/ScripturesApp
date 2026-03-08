from typing import List, Dict, Any
from src.ports.nlp_provider import NLPProvider

class AnalyzeGreekWordUseCase:
    def __init__(self, nlp_provider: NLPProvider):
        self.nlp_provider = nlp_provider

    def execute(self, text: str) -> List[Dict[str, Any]]:
        """
        Perform deep NLP analysis on Greek text using OdyCy via the NLP port.
        """
        return self.nlp_provider.analyze_greek_word(text)
