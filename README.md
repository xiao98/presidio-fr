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
