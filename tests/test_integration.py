import pytest

pytest.importorskip("fr_core_news_md")

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

from presidio_fr import FR_ENTITIES, add_fr_recognizers


@pytest.fixture(scope="module")
def analyzer():
    nlp = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "fr", "model_name": "fr_core_news_md"}],
    }).create_engine()
    registry = RecognizerRegistry(supported_languages=["fr"])
    registry.load_predefined_recognizers(languages=["fr"], nlp_engine=nlp)
    add_fr_recognizers(registry)
    return AnalyzerEngine(registry=registry, nlp_engine=nlp, supported_languages=["fr"])


def test_end_to_end(analyzer):
    text = "Salarié n° sécu 1 85 05 78 006 084 91, société SIRET 552 100 554 00013, plaque AB-123-CD."
    res = {r.entity_type: (text[r.start:r.end], r.score) for r in analyzer.analyze(text=text, language="fr", entities=FR_ENTITIES)}
    assert res["FR_NIR"][0] == "1 85 05 78 006 084 91"
    assert res["FR_SIRET"][0] == "552 100 554 00013"
    assert res["FR_PLAQUE"][0] == "AB-123-CD"
    # context words ("sécu", "SIRET", "plaque") must lift scores above the bare pattern score
    assert res["FR_NIR"][1] > 0.5 and res["FR_SIRET"][1] > 0.4 and res["FR_PLAQUE"][1] > 0.4


def test_context_gates_low_score_entities(analyzer):
    bare = analyzer.analyze(text="Commande 1234567890123 expédiée.", language="fr", entities=["FR_NUMERO_FISCAL"])
    ctx = analyzer.analyze(text="Numéro fiscal 1234567890123.", language="fr", entities=["FR_NUMERO_FISCAL"])
    assert max((r.score for r in bare), default=0) < 0.5 < max(r.score for r in ctx)
