from presidio_analyzer import Pattern, PatternRecognizer

from ._validators import nir_ok


class FrNirRecognizer(PatternRecognizer):
    """Numéro d'inscription au répertoire (sécurité sociale).

    Format: S AA MM DD CCC OOO KK  (15 chars, dept may be 2A/2B), optional spaces.
    Validated with the mod-97 key.
    """

    PATTERNS = [
        Pattern(
            "FR_NIR",
            r"\b[12]\s?\d{2}\s?(?:0[1-9]|1[0-2]|[2-9]\d)\s?(?:\d{2}|2[AB])\s?\d{3}\s?\d{3}\s?\d{2}\b",
            0.5,
        ),
    ]
    CONTEXT = ["nir", "sécu", "sécurité", "sociale", "vitale", "assuré", "assurance", "cpam", "ameli", "salarié", "paie", "bulletin"]

    def __init__(self, supported_language: str = "fr"):
        super().__init__(
            supported_entity="FR_NIR",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )

    def validate_result(self, pattern_text: str):
        compact = pattern_text.replace(" ", "")
        return nir_ok(compact)
