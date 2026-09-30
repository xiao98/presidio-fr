"""Score pred_*.jsonl against fr_pii_bench_v0.jsonl.

Redaction-oriented metrics:
  recall_any   : gold entity is >=80% covered by predicted spans of ANY label   (was it masked at all?)
  recall_label : same, but only predicted spans whose mapped label matches the gold label
  precision    : predicted span overlaps gold by >=50% of its own length         (label-agnostic)
  false_masks  : predicted spans with zero overlap with any gold entity           (utility damage)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE / "fr_pii_bench_v0.jsonl"
LABELS = ["PERSON", "ADDRESS", "EMAIL", "PHONE", "DOB", "COMPANY", "NIR", "SIREN", "SIRET", "IBAN", "FISCAL", "PLAQUE", "PASSEPORT"]
IDS = {"NIR", "SIREN", "SIRET", "FISCAL", "PASSEPORT"}

MAP = {
    "nym": {
        "GIVEN_NAME": {"PERSON"}, "SURNAME": {"PERSON"},
        "STREET_ADDRESS": {"ADDRESS"}, "STREET_NAME": {"ADDRESS"}, "BUILDING_NUMBER": {"ADDRESS"}, "ZIP_CODE": {"ADDRESS"},
        "CITY": {"ADDRESS"}, "SECONDARY_ADDRESS": {"ADDRESS"}, "STATE": {"ADDRESS"}, "COUNTRY": {"ADDRESS"},
        "EMAIL": {"EMAIL"}, "PHONE": {"PHONE"}, "FAX_NUMBER": {"PHONE"}, "DATE_OF_BIRTH": {"DOB"}, "DATE": {"DOB"},
        "COMPANY_NAME": {"COMPANY"}, "SSN": {"NIR"}, "GOVERNMENT_ID": IDS, "TAX_ID": IDS, "ACCOUNT_NUMBER": IDS | {"IBAN"},
        "CUSTOMER_ID": IDS, "EMPLOYEE_ID": IDS, "IBAN": {"IBAN"}, "LICENSE_PLATE": {"PLAQUE"}, "PASSPORT": {"PASSEPORT"},
    },
    "astrlink": {
        "private_person": {"PERSON"}, "private_address": {"ADDRESS"}, "email": {"EMAIL"}, "phone": {"PHONE"},
        "private_date": {"DOB"}, "account": IDS, "payment_card": {"IBAN"},
    },
    "union": None,  # filled below: nym labels + presidio FR_* labels
    "presidio": {
        "PERSON": {"PERSON"}, "LOCATION": {"ADDRESS"}, "EMAIL_ADDRESS": {"EMAIL"}, "PHONE_NUMBER": {"PHONE"}, "DATE_TIME": {"DOB"},
        "ORGANIZATION": {"COMPANY"}, "IBAN_CODE": {"IBAN"}, "FR_NIR": {"NIR"}, "FR_SIREN": {"SIREN"}, "FR_SIRET": {"SIRET"},
        "FR_NUMERO_FISCAL": {"FISCAL"}, "FR_PLAQUE": {"PLAQUE"}, "FR_PASSEPORT": {"PASSEPORT"},
    },
}

MAP["union_nodate"] = None
MAP["union"] = {**MAP["nym"], **{k: v for k, v in MAP["presidio"].items() if k.startswith("FR_") or k == "IBAN_CODE"}}
MAP["union_nodate"] = MAP["union"]


def covered(gold, spans, thr=0.8):
    chars = set()
    for s in spans:
        lo, hi = max(gold["start"], s["start"]), min(gold["end"], s["end"])
        if lo < hi:
            chars.update(range(lo, hi))
    return len(chars) >= thr * (gold["end"] - gold["start"])


def score(system):
    docs = {d["id"]: d for d in (json.loads(l) for l in BENCH.open(encoding="utf-8"))}
    preds = {p["id"]: p["spans"] for p in (json.loads(l) for l in (HERE / f"pred_{system}.jsonl").open(encoding="utf-8"))}
    m = MAP[system]
    n = {k: 0 for k in LABELS}
    hit_any = {k: 0 for k in LABELS}
    hit_lab = {k: 0 for k in LABELS}
    n_pred = tp_pred = false_masks = 0
    for did, d in docs.items():
        spans = preds.get(did, [])
        for g in d["entities"]:
            n[g["label"]] += 1
            if covered(g, spans):
                hit_any[g["label"]] += 1
            if covered(g, [s for s in spans if g["label"] in m.get(s["label"], set())]):
                hit_lab[g["label"]] += 1
        for s in spans:
            n_pred += 1
            ov = 0
            for g in d["entities"]:
                lo, hi = max(g["start"], s["start"]), min(g["end"], s["end"])
                ov += max(0, hi - lo)
            if ov >= 0.5 * (s["end"] - s["start"]):
                tp_pred += 1
            elif ov == 0:
                false_masks += 1
    tot = sum(n.values())
    r_any = sum(hit_any.values()) / tot
    r_lab = sum(hit_lab.values()) / tot
    p = tp_pred / n_pred if n_pred else 0.0
    f1 = 2 * p * r_any / (p + r_any) if p + r_any else 0.0
    return dict(n=n, r_any={k: hit_any[k] / n[k] for k in LABELS}, r_lab={k: hit_lab[k] / n[k] for k in LABELS},
                R_any=r_any, R_lab=r_lab, P=p, F1=f1, n_pred=n_pred, false_masks=false_masks, n_docs=len(docs))


def main():
    systems = sys.argv[1:] or [s for s in MAP if (HERE / f"pred_{s}.jsonl").exists()]
    res = {s: score(s) for s in systems}
    lines = []
    lines.append("## FR-PII-Bench v0 — recall_any per gold label (masked by anything?)\n")
    lines.append("| label | n | " + " | ".join(systems) + " |")
    lines.append("|---|---:|" + "---:|" * len(systems))
    n = res[systems[0]]["n"]
    for k in LABELS:
        lines.append(f"| {k} | {n[k]} | " + " | ".join(f"{res[s]['r_any'][k]:.2f}" for s in systems) + " |")
    lines.append("")
    lines.append("## recall_label per gold label (masked with the right type?)\n")
    lines.append("| label | " + " | ".join(systems) + " |")
    lines.append("|---|" + "---:|" * len(systems))
    for k in LABELS:
        lines.append(f"| {k} | " + " | ".join(f"{res[s]['r_lab'][k]:.2f}" for s in systems) + " |")
    lines.append("")
    lines.append("## Overall\n")
    lines.append("| system | recall_any | recall_label | precision | F1 (any) | predicted spans | false masks |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for s in systems:
        r = res[s]
        lines.append(f"| {s} | {r['R_any']:.3f} | {r['R_lab']:.3f} | {r['P']:.3f} | {r['F1']:.3f} | {r['n_pred']} | {r['false_masks']} |")
    out = "\n".join(lines)
    print(out)
    (HERE / "results.md").write_text(out + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
