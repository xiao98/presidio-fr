"""Publish FR-PII-Bench v0 as a Hugging Face dataset.

Prerequisite (once, interactive): `uv run hf auth login`
Usage: uv run python scripts/upload_hf.py [repo_id]   (default: <your username>/fr-pii-bench)
"""
import sys
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "eval" / "benchmark"

CARD = """---
license: cc-by-4.0
language:
- fr
task_categories:
- token-classification
tags:
- pii
- privacy
- gdpr
- rgpd
- anonymization
- french
pretty_name: FR-PII-Bench v0
size_categories:
- n<1K
---

# FR-PII-Bench v0

300 synthetic French administrative, accounting and legal documents (payslips, invoices, employment
contracts, lawyer and CAF letters, employer certificates, client e-mails, traffic fines) with exact
character-offset annotations for 13 personal-data types, plus distractors (amounts, order numbers, event
dates) that must not be masked. Built to measure *redaction* systems, not NER: the question is "was it
masked?" first, "with the right label?" second, and "what was masked for nothing?" third.

| label | count | validation in the generator |
|---|---:|---|
| PERSON | 488 | Faker fr_FR; four surface forms incl. `NOM Prénom` and `Maître Nom`; honorifics excluded from the span |
| ADDRESS | 397 | Faker fr_FR, flattened to one line |
| COMPANY | 208 | Faker + legal form (SARL, SAS…) |
| EMAIL / PHONE | 168 / 169 | four French phone layouts |
| DOB | 113 | three date formats, always introduced as a birth date |
| NIR | 94 | mod-97 key valid |
| SIREN / SIRET | 95 / 75 | Luhn valid |
| IBAN | 131 | FR, mod-97 valid |
| FISCAL | 55 | 13 digits, fiscal context |
| PLAQUE | 75 | SIV format |
| PASSEPORT | 37 | 2 digits + 2 letters + 5 digits |

Format: JSON lines, one document per line: `{"id", "doc_type", "text", "entities": [{"start", "end", "label", "text"}]}`,
offsets are Unicode character positions into `text`.

## Baselines (recall_any / precision / false masks)

| system | recall_any | precision | false masks |
|---|---:|---:|---:|
| Presidio 2.2 + presidio-fr rules + spaCy fr_core_news_md | 0.728 | 0.730 | 921 |
| Wismut/nym-pii-multilingual-small (edge-int8) | 0.968 | 0.895 | 410 |
| QuantumNous/astrlink-guard (int8) | 0.704 | 0.768 | 587 |
| nym + presidio-fr rules + caps-name rule, DATE gated on birth context (shipped) | 0.990 | 0.973 | 41 |

Scorer, runners and the generator: https://github.com/xiao98/presidio-fr/tree/main/eval/benchmark.
Technical report: https://github.com/xiao98/presidio-fr/blob/main/REPORT.md.

## Limitations

Synthetic and template-based: identifiers appear in canonical forms, names and addresses come from Faker's
French lists, no scans, no handwriting, no free-form notes. The set was used to tune the shipped
configuration's stop-list, so it is not a held-out test for that system. v1 will add consented real
documents and a held-out split.

## Citation

Xiao, H. (2026). *On-device masking of French personal data before it reaches a language model* (technical
report v0.1). https://github.com/xiao98/presidio-fr/blob/main/REPORT.md
"""


def main():
    api = HfApi()
    user = api.whoami()["name"]
    repo_id = sys.argv[1] if len(sys.argv) > 1 else f"{user}/fr-pii-bench"
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True)
    api.upload_file(path_or_fileobj=str(BENCH / "fr_pii_bench_v0.jsonl"), path_in_repo="fr_pii_bench_v0.jsonl", repo_id=repo_id, repo_type="dataset")
    api.upload_file(path_or_fileobj=CARD.encode("utf-8"), path_in_repo="README.md", repo_id=repo_id, repo_type="dataset")
    api.upload_file(path_or_fileobj=str(BENCH / "generate.py"), path_in_repo="generate.py", repo_id=repo_id, repo_type="dataset")
    print("published: https://huggingface.co/datasets/" + repo_id)


if __name__ == "__main__":
    main()
