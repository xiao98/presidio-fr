# presidio-fr

French PII recognizers for [Microsoft Presidio](https://github.com/microsoft/presidio).
Presidio ships country-specific recognizers for 18 countries and none for France. This package fills the gap.

| Entity | What | Validation |
|---|---|---|
| `FR_NIR` | Numéro de sécurité sociale (15 chars, Corse 2A/2B) | mod-97 key |
| `FR_SIREN` | 9-digit company id | Luhn |
| `FR_SIRET` | 14-digit establishment id | Luhn |
| `FR_NUMERO_FISCAL` | 13-digit tax id (SPI) | pattern + context |
| `FR_PLAQUE` | SIV licence plate `AA-123-AA` | pattern + context |
| `FR_PASSEPORT` | Passport `12AB34567` | pattern + context |

Phone numbers and IBANs are already covered by Presidio's built-in `PhoneRecognizer` (region FR) and `IbanRecognizer`.

## Install

```bash
pip install presidio-fr
python -m spacy download fr_core_news_md   # optional, for names/addresses via NER
```

## Use

```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_fr import add_fr_recognizers, FR_ENTITIES

nlp = NlpEngineProvider(nlp_configuration={
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "fr", "model_name": "fr_core_news_md"}],
}).create_engine()

registry = RecognizerRegistry(supported_languages=["fr"])
registry.load_predefined_recognizers(languages=["fr"], nlp_engine=nlp)
add_fr_recognizers(registry)

analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp, supported_languages=["fr"])
text = "Salarié n° sécu 1 85 05 78 006 084 36, société SIRET 552 100 554 00013."
for r in analyzer.analyze(text=text, language="fr", entities=FR_ENTITIES):
    print(r.entity_type, text[r.start:r.end], r.score)
```

## With LiteLLM

LiteLLM's open-source Presidio guardrail masks PII before the upstream call and restores placeholders in the response.
Run a Presidio analyzer server with `presidio-fr` registered, point LiteLLM's `presidio_analyzer_api_base` at it, and list the `FR_*` entities in `pii_entities_config`.

## Evaluate

```bash
uv run python eval/run_eval.py   # 200 synthetic French documents, recall per entity
```

## License

MIT

## FR-PII-Bench v0

Technical report (benchmark, three detectors, ablations, system design): [REPORT.md](REPORT.md). Publish the dataset to Hugging Face with `uv run hf auth login` once, then `uv run python scripts/upload_hf.py`.

`eval/benchmark/` holds a synthetic benchmark of 300 French administrative, accounting and legal documents
(payslips, invoices, employment contracts, lawyer and CAF letters, fines, client e-mails) with exact span labels
for 13 entity types, plus distractors (amounts, order numbers, event dates) that must not be masked.

```bash
uv run python eval/benchmark/generate.py 300 0        # regenerate (deterministic)
uv run python eval/benchmark/run_presidio.py          # Presidio + presidio-fr + spaCy fr_core_news_md
uv run python eval/benchmark/run_onnx.py nym          # Wismut/nym-pii-multilingual-small (edge-int8)
uv run python eval/benchmark/run_onnx.py astrlink     # QuantumNous/astrlink-guard (int8)
uv run python eval/benchmark/score.py presidio nym astrlink union union_nodate
```

Results (2026-09-30, `results.md`): recall_any / precision / false masks on 2,105 gold entities

| system | recall_any | precision | false masks |
|---|---:|---:|---:|
| Presidio + presidio-fr + spaCy fr | 0.728 | 0.730 | 921 |
| nym-pii-multilingual-small | 0.968 | 0.895 | 410 |
| astrlink-guard | 0.704 | 0.768 | 587 |
| nym + presidio-fr regex, generic DATE dropped | 0.948 | 0.978 | 92 |

Takeaways: nym is the only model that finds French street addresses; the regex layer fixes its SIRET / numéro fiscal
labelling; dropping nym's generic `DATE` label removes most false masks (invoice dates) at the cost of DOBs it did not
tag `DATE_OF_BIRTH`. The remaining French gap is the administrative `NOM Prénom` capitalised form (nym recall 0.55).
