"""French PII recognizers for Microsoft Presidio."""

from presidio_analyzer import RecognizerRegistry

from .nir import FrNirRecognizer
from .numero_fiscal import FrNumeroFiscalRecognizer
from .passeport import FrPasseportRecognizer
from .plaque import FrPlaqueRecognizer
from .siren_siret import FrSirenRecognizer, FrSiretRecognizer

__all__ = [
    "FrNirRecognizer",
    "FrSirenRecognizer",
    "FrSiretRecognizer",
    "FrNumeroFiscalRecognizer",
    "FrPlaqueRecognizer",
    "FrPasseportRecognizer",
    "FR_ENTITIES",
    "fr_recognizers",
    "add_fr_recognizers",
]

FR_ENTITIES = ["FR_NIR", "FR_SIREN", "FR_SIRET", "FR_NUMERO_FISCAL", "FR_PLAQUE", "FR_PASSEPORT"]


def fr_recognizers(supported_language: str = "fr"):
    return [
        FrNirRecognizer(supported_language),
        FrSirenRecognizer(supported_language),
        FrSiretRecognizer(supported_language),
        FrNumeroFiscalRecognizer(supported_language),
        FrPlaqueRecognizer(supported_language),
        FrPasseportRecognizer(supported_language),
    ]


def add_fr_recognizers(registry: RecognizerRegistry, supported_language: str = "fr") -> RecognizerRegistry:
    for r in fr_recognizers(supported_language):
        registry.add_recognizer(r)
    return registry
