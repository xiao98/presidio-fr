"""FR-PII-Bench v0: synthetic French administrative / accounting / legal documents with exact span labels.

Usage: python eval/benchmark/generate.py [N_DOCS] [SEED]  -> eval/benchmark/fr_pii_bench_v0.jsonl

Labels: PERSON, ADDRESS, EMAIL, PHONE, DOB, COMPANY, NIR, SIREN, SIRET, IBAN, FISCAL, PLAQUE, PASSEPORT.
Every document also contains distractors (amounts, order numbers, non-personal dates) that must NOT be masked.
"""
import json
import random
import sys
from pathlib import Path

from faker import Faker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from presidio_fr._validators import luhn_ok  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 0
fake = Faker("fr_FR")
Faker.seed(SEED)
random.seed(SEED)
OUT = Path(__file__).with_name("fr_pii_bench_v0.jsonl")

LETTERS = "ABCDEFGHJKLMNPQRSTVWXYZ"


# ---------------------------------------------------------------- value generators
def g_person():
    first, last = fake.first_name(), fake.last_name()
    style = random.random()
    if style < 0.35:
        return f"{first} {last}"
    if style < 0.6:   # honorific is NOT part of the gold span
        return (random.choice(['M.', 'Mme', 'Monsieur', 'Madame']) + " ", f"{first} {last}")
    if style < 0.8:
        return f"{last.upper()} {first}"            # administrative caps
    return ("Maître ", last)                       # lawyer style, surname only


def g_address():
    a = fake.address().replace("\n", ", ")
    return " ".join(a.split())


def g_dob():
    d = fake.date_of_birth(minimum_age=18, maximum_age=80)
    return d.strftime(random.choice(["%d/%m/%Y", "%d %B %Y", "%d.%m.%Y"]))


def g_phone():
    n = [random.choice("1234567")] + [str(random.randint(0, 9)) for _ in range(8)]
    d = "".join(n)
    style = random.random()
    if style < 0.4:
        return "0" + " ".join([d[0]] + [d[i:i + 2] for i in range(1, 9, 2)])
    if style < 0.7:
        return "+33 " + d[0] + " " + " ".join(d[i:i + 2] for i in range(1, 9, 2))
    if style < 0.85:
        return "0" + d[0] + "." + ".".join(d[i:i + 2] for i in range(1, 9, 2))
    return "0" + d


def g_email():
    return fake.email()


def g_company():
    return f"{fake.company()} {random.choice(['SARL', 'SAS', 'SA', 'EURL', ''])}".strip()


def g_nir():
    s = fake.ssn().replace(" ", "")
    if random.random() < 0.6:
        return f"{s[0]} {s[1:3]} {s[3:5]} {s[5:7]} {s[7:10]} {s[10:13]} {s[13:]}"
    return s


def g_siren():
    s = fake.siren().replace(" ", "")
    assert luhn_ok(s)
    return f"{s[:3]} {s[3:6]} {s[6:]}" if random.random() < 0.5 else s


def g_siret():
    s = fake.siret().replace(" ", "")
    assert luhn_ok(s)
    return f"{s[:3]} {s[3:6]} {s[6:9]} {s[9:]}" if random.random() < 0.5 else s


def g_iban():
    s = fake.iban()
    return " ".join(s[i:i + 4] for i in range(0, len(s), 4)) if random.random() < 0.6 else s


def g_fiscal():
    s = str(random.randint(0, 3)) + "".join(random.choices("0123456789", k=12))
    return f"{s[:2]} {s[2:4]} {s[4:7]} {s[7:10]} {s[10:]}" if random.random() < 0.5 else s


def g_plaque():
    while True:
        a, b = "".join(random.choices(LETTERS, k=2)), "".join(random.choices(LETTERS, k=2))
        if a != "SS" and b != "SS":
            return f"{a}-{random.randint(0, 999):03d}-{b}"


def g_passeport():
    return f"{random.randint(0, 99):02d}{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))}{random.randint(0, 99999):05d}"


GEN = {
    "PERSON": g_person, "ADDRESS": g_address, "EMAIL": g_email, "PHONE": g_phone, "DOB": g_dob,
    "COMPANY": g_company, "NIR": g_nir, "SIREN": g_siren, "SIRET": g_siret, "IBAN": g_iban,
    "FISCAL": g_fiscal, "PLAQUE": g_plaque, "PASSEPORT": g_passeport,
}


# distractors: must not be flagged
def d_amount():
    return f"{random.randint(100, 99999):,}".replace(",", " ") + f",{random.randint(0, 99):02d} €"


def d_order():
    return f"{random.choice(['CMD', 'FAC', 'DEV', 'REF'])}-{random.randint(2024, 2026)}-{random.randint(1000, 99999)}"


def d_date():
    return fake.date_between("-2y", "today").strftime("%d/%m/%Y")   # event date, not personal


def d_pct():
    return f"{random.choice([5.5, 10, 20])} %"


# ---------------------------------------------------------------- templates
# A template is a list of segments: plain string, or (LABEL,) placeholder, or ("~", distractor_fn).
T = {
    "bulletin_paie": [
        ["BULLETIN DE PAIE — ", ("~", d_date), "\nEmployeur : ", ("COMPANY",), ", SIRET ", ("SIRET",), ", ", ("ADDRESS",),
         "\nSalarié : ", ("PERSON",), ", né(e) le ", ("DOB",), ", n° de sécurité sociale ", ("NIR",),
         "\nAdresse : ", ("ADDRESS",), "\nSalaire brut : ", ("~", d_amount), " — Net à payer : ", ("~", d_amount),
         "\nVirement sur IBAN ", ("IBAN",), "."],
    ],
    "facture": [
        ["Facture n° ", ("~", d_order), " du ", ("~", d_date), "\nÉmetteur : ", ("COMPANY",), " — SIREN ", ("SIREN",), " — ", ("ADDRESS",),
         "\nClient : ", ("PERSON",), ", ", ("ADDRESS",), ", tél. ", ("PHONE",), ", ", ("EMAIL",),
         "\nTotal HT : ", ("~", d_amount), ", TVA ", ("~", d_pct), ", TTC : ", ("~", d_amount),
         "\nRèglement par virement : ", ("IBAN",), "."],
    ],
    "contrat_travail": [
        ["CONTRAT DE TRAVAIL À DURÉE INDÉTERMINÉE\nEntre la société ", ("COMPANY",), ", immatriculée au RCS sous le numéro ", ("SIREN",),
         ", dont le siège est situé ", ("ADDRESS",), ", représentée par ", ("PERSON",), ",\net ", ("PERSON",), ", né(e) le ", ("DOB",),
         ", demeurant ", ("ADDRESS",), ", immatriculé(e) à la sécurité sociale sous le n° ", ("NIR",),
         ".\nRémunération brute mensuelle : ", ("~", d_amount), ". Date d'entrée : ", ("~", d_date), "."],
    ],
    "courrier_avocat": [
        [("PERSON",), "\nAvocat au Barreau de Paris\n", ("ADDRESS",), "\n\nAffaire : ", ("PERSON",), " c/ ", ("COMPANY",),
         "\nRéférence : ", ("~", d_order), "\n\nCher confrère,\nMon client, ", ("PERSON",), ", demeurant ", ("ADDRESS",),
         ", joignable au ", ("PHONE",), " ou par courriel à ", ("EMAIL",), ", conteste la facture de ", ("~", d_amount),
         " émise le ", ("~", d_date), ". Son véhicule immatriculé ", ("PLAQUE",), " n'était pas sur place."],
    ],
    "courrier_caf": [
        ["Caisse d'Allocations Familiales\nDossier allocataire n° ", ("~", d_order), "\n\n", ("PERSON",), "\n", ("ADDRESS",),
         "\n\nMadame, Monsieur,\nSuite à votre demande d'aide au logement, merci de nous transmettre : votre numéro fiscal de référence (",
         ("FISCAL",), "), votre RIB (", ("IBAN",), ") et une copie de votre passeport n° ", ("PASSEPORT",),
         ".\nMontant estimé : ", ("~", d_amount), " par mois à compter du ", ("~", d_date), "."],
    ],
    "attestation_employeur": [
        ["ATTESTATION EMPLOYEUR\nJe soussigné(e) ", ("PERSON",), ", agissant pour ", ("COMPANY",), " (SIRET ", ("SIRET",),
         "), atteste que ", ("PERSON",), ", né(e) le ", ("DOB",), ", est employé(e) depuis le ", ("~", d_date),
         " en qualité de comptable. Contact RH : ", ("PHONE",), " / ", ("EMAIL",), ".\nFait à Lyon le ", ("~", d_date), "."],
    ],
    "mail_client": [
        ["Bonjour,\nPouvez-vous préparer la déclaration de TVA de ", ("COMPANY",), " (SIREN ", ("SIREN",), ") ? Le gérant, ", ("PERSON",),
         ", est joignable au ", ("PHONE",), ". Sa nouvelle adresse : ", ("ADDRESS",), ".\nLe CA du trimestre est de ", ("~", d_amount),
         ", commande ", ("~", d_order), " incluse.\nMerci,\n", ("PERSON",)],
        ["Bonjour,\nCi-joint le dossier de ", ("PERSON",), " (", ("EMAIL",), "). Son numéro de sécu est ", ("NIR",),
         " et son numéro fiscal ", ("FISCAL",), ". Le remboursement de ", ("~", d_amount), " part sur ", ("IBAN",),
         " avant le ", ("~", d_date), ".\nCordialement,\n", ("PERSON",)],
    ],
    "pv_amende": [
        ["AVIS DE CONTRAVENTION n° ", ("~", d_order), "\nVéhicule : ", ("PLAQUE",), "\nTitulaire du certificat d'immatriculation : ",
         ("PERSON",), ", ", ("ADDRESS",), "\nInfraction constatée le ", ("~", d_date), ". Montant : ", ("~", d_amount),
         ". Pour contester : ", ("EMAIL",), " ou ", ("PHONE",), "."],
    ],
}


def render(segments):
    text, ents = "", []
    for seg in segments:
        if isinstance(seg, str):
            text += seg
        elif seg[0] == "~":
            text += seg[1]()
        else:
            label = seg[0]
            v = GEN[label]()
            if isinstance(v, tuple):               # (plain prefix, labelled value)
                text += v[0]
                v = v[1]
            ents.append({"start": len(text), "end": len(text) + len(v), "label": label, "text": v})
            text += v
    return text, ents


def main():
    types = list(T)
    with OUT.open("w", encoding="utf-8") as f:
        for i in range(N):
            dt = types[i % len(types)]
            tmpl = random.choice(T[dt])
            text, ents = render(tmpl)
            f.write(json.dumps({"id": f"{dt}-{i:04d}", "doc_type": dt, "text": text, "entities": ents}, ensure_ascii=False) + "\n")
    counts = {}
    for line in OUT.read_text(encoding="utf-8").splitlines():
        for e in json.loads(line)["entities"]:
            counts[e["label"]] = counts.get(e["label"], 0) + 1
    print(f"wrote {N} docs -> {OUT.name}")
    for k, v in sorted(counts.items()):
        print(f"  {k:10}{v:5d}")


if __name__ == "__main__":
    main()
