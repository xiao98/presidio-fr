from presidio_analyzer import Pattern, PatternRecognizer


class FrPasseportRecognizer(PatternRecognizer):
    """Passeport français: 2 digits + 2 letters + 5 digits (e.g. 12AB34567)."""

    PATTERNS = [Pattern("FR_PASSEPORT", r"\b\d{2}[A-Z]{2}\d{5}\b", 0.3)]
    CONTEXT = ["passeport", "passport", "voyage", "identité", "délivré"]

    def __init__(self, supported_language: str = "fr"):
        super().__init__(
            supported_entity="FR_PASSEPORT",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )
