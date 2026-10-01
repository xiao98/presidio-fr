# On-device masking of French personal data before it reaches a language model

**Technical report, v0.1 — 1 October 2026**
Hao Xiao (Université Paris-Saclay, M2 Mathématiques et Intelligence Artificielle)
Code: [presidio-fr](https://github.com/xiao98/presidio-fr) · [presidio-fr-extension](https://github.com/xiao98/presidio-fr-extension) · [presidio-fr-core](https://github.com/xiao98/presidio-fr-core) · Benchmark: FR-PII-Bench v0 (this repository, `eval/benchmark/`; dataset: [huggingface.co/datasets/JaqueBill/fr-pii-bench](https://huggingface.co/datasets/JaqueBill/fr-pii-bench))

> **Résumé.** Les cabinets d'expertise comptable, d'avocats et de RH collent des dossiers clients dans ChatGPT. Le risque RGPD n'est pas ce que le fournisseur fait des données, c'est la transmission elle-même (art. 28 et 44). Nous décrivons un système qui masque les données personnelles françaises *sur le poste de l'utilisateur*, avant l'envoi, et restaure les valeurs à l'affichage : une extension navigateur pour ChatGPT, Claude et Le Chat, et une passerelle locale compatible OpenAI/Anthropic pour les outils installés. Pour le mesurer, nous publions FR-PII-Bench v0, 300 documents administratifs français synthétiques à annotations exactes (2 105 entités, 13 types), et comparons trois détecteurs ouverts. Aucun n'est entraîné pour le français : Presidio n'a pas de reconnaisseur français et ne voit pas les adresses (rappel 0,03) ; le modèle multilingue nym atteint 0,97 de rappel mais masque toutes les dates et rate la moitié des noms en capitales (« DUPONT Jean », 0,48) ; astrlink-guard, entraîné sur du chinois et de l'anglais, ne reconnaît ni plaque, ni passeport, ni IBAN. La configuration retenue, nym + règles françaises avec sommes de contrôle + règle pour les noms en capitales + dates gardées seulement en contexte de naissance, obtient **0,990 de rappel et 0,973 de précision** avec 41 masquages inutiles sur 300 documents, en 50 ms par document sur CPU, dans le navigateur. Nous n'avons entraîné aucun modèle : le benchmark a montré que ce n'était pas nécessaire.

## 1. Problem

A professional who handles third-party personal data (an accountant preparing a payslip, a lawyer drafting a letter, an HR officer) now routinely pastes documents into a hosted language model. Under the GDPR the transfer itself is the processing act that needs a legal basis; the provider's training policy does not change that. The only way to remove the question is to make sure personal data never leaves the machine. That requires detecting it locally, replacing it with something the model can still reason over, and putting the real values back where the user reads the answer.

Three constraints make the French case specific:

1. **Structured identifiers with checksums.** The social security number (NIR, 15 digits with a mod-97 key, Corsican departments written 2A/2B), SIREN and SIRET (Luhn), the IBAN, the tax number, the SIV licence plate, the passport number. None of these has a recognizer in Microsoft Presidio, which ships country-specific recognizers for 18 countries and none for France.
2. **Administrative spellings.** Names are written `DUPONT Jean` (surname first, capitals) on payslips and contracts, `Maître Dupont` in legal letters, `M. Jean Dupont` in correspondence. Multilingual NER models are trained on prose and see the capitalised form as a heading.
3. **Utility.** Masking every date on an invoice destroys what the user asked the model to do. The detector must distinguish a date of birth from a due date.

## 2. System

The same engine runs in two shells.

- **Browser extension** (Manifest V3): intercepts Enter and the send button on chatgpt.com, claude.ai and chat.mistral.ai, rewrites the editor, verifies the rewrite (if the editor refuses, the send is blocked), re-triggers the send. Attachments (PDF text layer, DOCX, XLSX) are replaced by masked copies before upload; DOCX and XLSX are rewritten inside their XML so layout and formulas survive. The model runs in an offscreen document with ONNX Runtime WASM. Placeholders are restored in the rendered page; a badge under each message shows that values were masked and a "model view" switch shows exactly what left the page.
- **Local gateway** (Node, `127.0.0.1`): OpenAI- and Anthropic-compatible endpoints; masks text leaves of the request (messages, tool arguments, tool results; signed reasoning blocks are replayed unchanged), forwards to the provider, restores placeholders in streamed replies with a carry-over for placeholders split across events. Placeholders are derived by HMAC(local key, type, value), so the same value gets the same placeholder on every turn without state. If the detector is unavailable the request is refused rather than forwarded. This layer takes its shape from reading AstrLink's privacy package (HMAC derivation, convention notice in the system channel, tolerant restore spellings, audit without plaintext, fail-closed policy).

Detection is two layers combined:

- **Rules** (`presidio-fr`, also ported to JavaScript): NIR with key validation, SIREN/SIRET with Luhn, IBAN with mod-97, tax number (pattern + fiscal context only), plate, passport, e-mail, phone. Rules are authoritative on structured identifiers.
- **Model**: `Wismut/nym-pii-multilingual-small` (ModernBERT, 277 M parameters, edge-int8 ONNX, 108 MB), decoded in *recall-first* mode (a token is an entity when P(O) < 0.5 even when the entity mass is spread across several labels), mapped to product types; its generic `DATE` label is kept only when the 24 preceding characters say *né(e) le / naissance*.
- **A capitalised-name rule**: one to three all-caps words optionally followed by one or two capitalised words (`DUPONT Jean`, `LE GOFF Isaac`, `XIAO HAO`), with a stop-list of acronyms (SARL, TVA, SIRET…), document headings (BULLETIN, ATTESTATION, CONTRAT…) and function words (DE, DU, ET, À…; LE/LA are kept for `LE GOFF`).

Model spans are trimmed around rule spans rather than dropped, so a model span covering "XIAO HAO 12 rue de la Paix" yields `{{PERSON_1}} {{ADDRESS_1}}`.

## 3. FR-PII-Bench v0

300 synthetic documents of eight kinds (payslip, invoice, employment contract, lawyer's letter, CAF letter, employer certificate, client e-mail, traffic fine), generated deterministically with Faker `fr_FR` plus the identifier generators above; 2 105 gold entities of 13 types with exact character offsets; distractors (amounts, order numbers, event dates) that must not be masked. Honorifics are not part of a name span. The generator and all runners are in `eval/benchmark/`; one command regenerates the set.

Metrics are chosen for redaction, not for NER: *recall_any* (a gold entity is ≥80 % covered by predicted spans of any type: was it masked?), *recall_label* (same, with the right type), *precision* (a predicted span overlaps gold by ≥50 % of its length) and *false masks* (predicted spans with no overlap at all: the utility cost).

Limitations that matter: the documents are synthetic and template-based, so they overstate recall on structured identifiers (which always appear in canonical forms) and say nothing about scanned documents, handwriting or free-form notes. Names and addresses come from Faker's French lists. The benchmark was built by the same person who tuned the system; the stop-list of the capitalised-name rule was adjusted after seeing its false positives on this set. v1 should add real, consented documents and a held-out split.

## 4. Results

Three open detectors as shipped, then the product configuration. Python onnxruntime runs; 300 documents.

| system | recall_any | recall_label | precision | false masks |
|---|---:|---:|---:|---:|
| Presidio 2.2 + presidio-fr rules + spaCy `fr_core_news_md` | 0.728 | 0.676 | 0.730 | 921 |
| nym-pii-multilingual-small (edge-int8), argmax | 0.968 | 0.923 | 0.895 | 410 |
| astrlink-guard (int8) | 0.704 | 0.568 | 0.768 | 587 |
| nym + rules (union) | 0.968 | 0.950 | 0.909 | 410 |
| nym + rules, generic DATE dropped | 0.948 | 0.930 | 0.978 | 92 |

Per type (recall_any): Presidio finds French street addresses in 3 % of cases (spaCy's LOCATION is a city, not an address); nym finds 100 % of addresses but labels SIRET as tax id and the tax number as something else (recall_label 0.68 and 0.53), which the rules fix; astrlink-guard, built for Chinese and English code and logs, scores 0.00 on plates, 0.22 on passports, 0.75 on IBANs and 0.17 on company names. Of nym's 410 false masks, 318 are event dates: it treats every date as sensitive.

The product configuration is measured through the JavaScript pipeline (transformers.js 4.3, same int8 model), which reproduces the Python scores within 0.003:

| configuration (JS pipeline) | recall_any | precision | false masks | PERSON recall, `NOM Prénom` form (n=97) |
|---|---:|---:|---:|---:|
| argmax decoding, no caps rule | 0.965 | 0.973 | 40 | 0.48 |
| recall-first decoding, no caps rule | 0.967 | 0.973 | 41 | 0.48 |
| argmax decoding + caps rule | 0.989 | 0.973 | 40 | 0.99 |
| **recall-first + caps rule (shipped)** | **0.990** | **0.973** | **41** | **0.99** |

Two honest readings of this table. The capitalised-name rule is what moves the benchmark: +0.024 recall, and the administrative name form goes from 0.48 to 0.99, at no cost in precision. Recall-first decoding is worth 0.001 here; its value showed on real inputs rather than on the benchmark ("XIAO HAO 12 rue de la Paix", where the model spreads its mass between STREET_ADDRESS, COMPANY_NAME and SURNAME and argmax lands on O), and we keep it because the benchmark has no such inputs, not because it proved it. The "né(e) le" gate recovers the date-of-birth recall that dropping nym's DATE label had cost (0.63 → 1.00) while keeping false masks at 41.

Throughput: 43–76 ms per document on a laptop CPU in Node; 23 ms for a one-sentence message; model ready 12–14 s after a cold start in the browser (download included), instantly afterwards.

## 5. What we did not do, and why

- **Train a French model.** The benchmark showed the gap was not in the model's language ability but in labelling conventions (dates) and one surface form (capitals). Both are fixed by rules with no training data, no GPU and no risk of regression on other languages. A fine-tune becomes justified only when real documents expose errors that rules cannot express; we have none yet.
- **Natural stand-ins.** AstrLink replaces e-mails, IPs and phones with syntactically valid values in reserved namespaces so that the model copies them without instruction. We use opaque `{{TYPE_n}}` markers plus a system-channel notice. Stand-ins for names, addresses and dates (the types that matter here) remain an open problem for both systems; a date-shifting scheme that preserves intervals is the obvious next step.
- **OCR.** Scanned PDFs are blocked, not processed.

## 6. Reproduce

```bash
git clone https://github.com/xiao98/presidio-fr && cd presidio-fr && uv sync
uv run python eval/benchmark/generate.py 300 0
uv run python eval/benchmark/run_presidio.py; uv run python eval/benchmark/run_onnx.py nym; uv run python eval/benchmark/run_onnx.py astrlink
uv run python eval/benchmark/score.py presidio nym astrlink union union_nodate
# product configuration and ablations (JS pipeline)
git clone https://github.com/xiao98/presidio-fr-extension && cd presidio-fr-extension && npm install
npm run test:ner                       # shipped configuration
PFR_DECODE=argmax npm run test:ner     # ablation: plain argmax
PFR_NO_CAPS=1 npm run test:ner         # ablation: no capitalised-name rule
```

## References

- Microsoft Presidio, https://github.com/microsoft/presidio (MIT).
- Wismut, *nym-pii-multilingual*, https://huggingface.co/Wismut/nym-pii-multilingual-small (MIT), trained on https://huggingface.co/datasets/Wismut/nym-pii-multilingual-data.
- QuantumNous, *AstrLink Guard*, https://huggingface.co/QuantumNous/astrlink-guard (Apache-2.0); AstrLink, https://github.com/Calcium-Ion/AstrLink.
- Hugging Face, *transformers.js*; Microsoft, *ONNX Runtime Web*.
