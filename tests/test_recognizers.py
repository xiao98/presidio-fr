import pytest

from presidio_fr import (
    FrNirRecognizer,
    FrNumeroFiscalRecognizer,
    FrPasseportRecognizer,
    FrPlaqueRecognizer,
    FrSirenRecognizer,
    FrSiretRecognizer,
)
from presidio_fr._validators import luhn_ok, nir_ok


def hits(rec, text):
    return [(text[r.start:r.end], r.score) for r in rec.analyze(text, [rec.supported_entities[0]])]


# --- validators -------------------------------------------------------------

def test_nir_key():
    assert nir_ok("185057800608491")          # body 1850578006084 -> key 97 - (body % 97) = 91
    assert not nir_ok("185057800608436")


def test_nir_key_corse():
    # 2A -> 19 substitution: build a valid key by hand
    body = "2 69 05 2A 001 012".replace(" ", "")
    key = 97 - (int(body.upper().replace("2A", "19")) % 97)
    assert nir_ok(body + f"{key:02d}")


def test_luhn():
    assert luhn_ok("552100554")        # SIREN Danone
    assert luhn_ok("55210055400013")   # SIRET Danone siège
    assert not luhn_ok("552100555")


# --- recognizers ------------------------------------------------------------

def test_nir_detect_spaced_and_compact():
    rec = FrNirRecognizer()
    assert hits(rec, "n° sécu 1 85 05 78 006 084 91 du salarié")[0][0] == "1 85 05 78 006 084 91"
    assert hits(rec, "NIR 185057800608491")[0][0] == "185057800608491"


def test_nir_rejects_bad_key():
    assert hits(FrNirRecognizer(), "NIR 185057800608436") == []


def test_siren_siret():
    assert hits(FrSirenRecognizer(), "SIREN 552 100 554")[0][0] == "552 100 554"
    assert hits(FrSirenRecognizer(), "SIREN 552 100 555") == []
    assert hits(FrSiretRecognizer(), "SIRET 55210055400013")[0][0] == "55210055400013"
    assert hits(FrSiretRecognizer(), "SIRET 55210055400014") == []


def test_numero_fiscal():
    assert hits(FrNumeroFiscalRecognizer(), "numéro fiscal 12 34 567 890 123")[0][0] == "12 34 567 890 123"
    assert hits(FrNumeroFiscalRecognizer(), "SPI 1234567890123")[0][0] == "1234567890123"
    assert hits(FrNumeroFiscalRecognizer(), "SPI 9234567890123") == []   # first digit must be 0-3


def test_plaque():
    rec = FrPlaqueRecognizer()
    assert hits(rec, "véhicule AB-123-CD")[0][0] == "AB-123-CD"
    assert hits(rec, "véhicule AB 123 CD")[0][0] == "AB 123 CD"
    assert hits(rec, "AI-123-CD") == []   # I forbidden
    assert hits(rec, "SS-123-CD") == []   # SS forbidden


def test_passeport():
    assert hits(FrPasseportRecognizer(), "passeport 12AB34567")[0][0] == "12AB34567"
    assert hits(FrPasseportRecognizer(), "ref 12AB3456") == []
