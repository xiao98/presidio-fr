"""Checksum helpers for French identifiers."""


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def nir_ok(nir: str) -> bool:
    """NIR = 13 chars + 2-digit key. Key = 97 - (number mod 97). Corse: 2A->19, 2B->18."""
    body, key = nir[:13], nir[13:]
    if not key.isdigit():
        return False
    body = body.upper().replace("2A", "19").replace("2B", "18")
    if not body.isdigit():
        return False
    return int(key) == 97 - (int(body) % 97)
