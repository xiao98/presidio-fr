from presidio_analyzer import Pattern, PatternRecognizer


class FrNumeroFiscalRecognizer(PatternRecognizer):
    """Numéro fiscal de référence (SPI): 13 digits, first digit 0-3. No public checksum,
    so the pattern score is low and context words carry the decision."""

    PATTERNS = [Pattern("FR_NUMERO_FISCAL", r"\b[0-3](?:\d\s?){11}\d\b", 0.2)]
    CONTEXT = ["fiscal", "spi", "impôt", "impôts", "imposition", "déclaration", "contribuable", "dgfip", "finances"]

    def __init__(self, supported_language: str = "fr"):
        super().__init__(
            supported_entity="FR_NUMERO_FISCAL",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )
