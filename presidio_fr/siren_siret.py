from presidio_analyzer import Pattern, PatternRecognizer

from ._validators import luhn_ok


class FrSirenRecognizer(PatternRecognizer):
    """SIREN: 9 digits, Luhn."""

    PATTERNS = [Pattern("FR_SIREN", r"\b\d{3}\s?\d{3}\s?\d{3}\b", 0.3)]
    CONTEXT = ["siren", "rcs", "entreprise", "société", "kbis", "immatriculation", "greffe"]

    def __init__(self, supported_language: str = "fr"):
        super().__init__(
            supported_entity="FR_SIREN",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )

    def validate_result(self, pattern_text: str):
        return luhn_ok(pattern_text.replace(" ", ""))


class FrSiretRecognizer(PatternRecognizer):
    """SIRET: SIREN + 5-digit NIC = 14 digits, Luhn over 14."""

    PATTERNS = [Pattern("FR_SIRET", r"\b\d{3}\s?\d{3}\s?\d{3}\s?\d{5}\b", 0.4)]
    CONTEXT = ["siret", "établissement", "siège", "kbis", "facture", "fournisseur", "client"]

    def __init__(self, supported_language: str = "fr"):
        super().__init__(
            supported_entity="FR_SIRET",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )

    def validate_result(self, pattern_text: str):
        return luhn_ok(pattern_text.replace(" ", ""))
