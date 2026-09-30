from presidio_analyzer import Pattern, PatternRecognizer


class FrPlaqueRecognizer(PatternRecognizer):
    """Plaque d'immatriculation SIV (2009+): AA-123-AA. Letters I, O, U excluded; SS excluded."""

    PATTERNS = [
        Pattern(
            "FR_PLAQUE",
            r"\b(?!SS)[A-HJ-NP-TV-Z]{2}[- ]?\d{3}[- ]?(?!SS)[A-HJ-NP-TV-Z]{2}\b",
            0.4,
        ),
    ]
    CONTEXT = ["immatriculation", "plaque", "véhicule", "voiture", "grise", "pv", "amende", "contravention", "stationnement"]

    def __init__(self, supported_language: str = "fr"):
        super().__init__(
            supported_entity="FR_PLAQUE",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )
