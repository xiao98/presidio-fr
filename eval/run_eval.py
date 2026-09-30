"""Recall/precision of presidio-fr on synthetic French documents.

No spaCy model needed: recognizers are pattern-based and run standalone.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faker import Faker

from presidio_fr import fr_recognizers
from presidio_fr._validators import luhn_ok

fake = Faker("fr_FR")
Faker.seed(0)
random.seed(0)

N_DOCS = int(sys.argv[1]) if len(sys.argv) > 1 else 200


def gen_nir():
    s = fake.ssn().replace(" ", "")          # faker fr_FR ssn is a valid NIR with key
    if random.random() < 0.5:
        s = f"{s[0]} {s[1:3]} {s[3:5]} {s[5:7]} {s[7:10]} {s[10:13]} {s[13:]}"
    return s


def gen_siren():
    s = fake.siren().replace(" ", "")
    assert luhn_ok(s)
    return f"{s[:3]} {s[3:6]} {s[6:]}" if random.random() < 0.5 else s


def gen_siret():
    s = fake.siret().replace(" ", "")
    assert luhn_ok(s)
    return f"{s[:3]} {s[3:6]} {s[6:9]} {s[9:]}" if random.random() < 0.5 else s


def gen_fiscal():
    s = str(random.randint(0, 3)) + "".join(random.choices("0123456789", k=12))
    return f"{s[:2]} {s[2:4]} {s[4:7]} {s[7:10]} {s[10:]}" if random.random() < 0.5 else s


LETTERS = "ABCDEFGHJKLMNPQRSTVWXYZ"


def gen_plaque():
    while True:
        a, b = "".join(random.choices(LETTERS, k=2)), "".join(random.choices(LETTERS, k=2))
        if a != "SS" and b != "SS":
            return f"{a}-{random.randint(0, 999):03d}-{b}"


def gen_passeport():
    return f"{random.randint(0, 99):02d}{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))}{random.randint(0, 99999):05d}"


TEMPLATES = {
    "FR_NIR": (gen_nir, ["Le salarié {name}, n° de sécurité sociale {v}, est en arrêt maladie.",
                          "Assuré : {name} — NIR {v}.",
                          "Carte vitale n° {v} au nom de {name}."]),
    "FR_SIREN": (gen_siren, ["La société {company}, SIREN {v}, est immatriculée au RCS de Paris.",
                              "Client : {company} (SIREN : {v})."]),
    "FR_SIRET": (gen_siret, ["Facture émise par {company}, SIRET {v}.",
                              "Établissement {company} — SIRET {v} — siège social."]),
    "FR_NUMERO_FISCAL": (gen_fiscal, ["Déclarant {name}, numéro fiscal {v}, avis d'imposition 2025.",
                                       "SPI : {v} (impôt sur le revenu de {name})."]),
    "FR_PLAQUE": (gen_plaque, ["Véhicule immatriculé {v}, carte grise au nom de {name}.",
                                "PV pour la plaque {v} le 12 mars."]),
    "FR_PASSEPORT": (gen_passeport, ["Passeport n° {v} délivré à {name}.",
                                      "Titre de voyage : passeport {v}."]),
}

recs = {r.supported_entities[0]: r for r in fr_recognizers()}
tp = {k: 0 for k in TEMPLATES}
fn = {k: 0 for k in TEMPLATES}
fp = {k: 0 for k in TEMPLATES}
# Negative control: documents with plain numbers that are not identifiers.
NEG = ["Le montant total est de 123 456 789 euros hors taxes.",
       "Commande n° 1234567890123 expédiée le 3 juin.",
       "Rendez-vous le 12 05 2024 à 14h, bureau 2B.",
       "Tél. 01 45 67 89 12, poste 336."]

for _ in range(N_DOCS):
    ent = random.choice(list(TEMPLATES))
    gen, tmpls = TEMPLATES[ent]
    v = gen()
    text = random.choice(tmpls).format(v=v, name=fake.name(), company=fake.company())
    found = [text[r.start:r.end] for r in recs[ent].analyze(text, [ent])]
    if v in found:
        tp[ent] += 1
    else:
        fn[ent] += 1

for ent, rec in recs.items():
    for t in NEG:
        fp[ent] += len(rec.analyze(t, [ent]))

print(f"{'entity':18}{'recall':>8}{'n':>6}{'neg_fp':>8}")
worst = 1.0
for ent in TEMPLATES:
    n = tp[ent] + fn[ent]
    r = tp[ent] / n if n else float("nan")
    worst = min(worst, r)
    print(f"{ent:18}{r:8.3f}{n:6d}{fp[ent]:8d}")
print("\nPASS" if worst >= 0.9 else "\nFAIL: recall < 0.9")
sys.exit(0 if worst >= 0.9 else 1)
