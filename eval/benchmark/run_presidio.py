"""Presidio + presidio-fr + spaCy fr_core_news_md over the benchmark -> pred_presidio.jsonl"""
import json
import sys
import time
from pathlib import Path

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from presidio_fr import add_fr_recognizers  # noqa: E402

BENCH = HERE / "fr_pii_bench_v0.jsonl"


def build():
    nlp = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "fr", "model_name": "fr_core_news_md"}],
    }).create_engine()
    registry = RecognizerRegistry(supported_languages=["fr"])
    registry.load_predefined_recognizers(languages=["fr"], nlp_engine=nlp)
    add_fr_recognizers(registry)
    return AnalyzerEngine(registry=registry, nlp_engine=nlp, supported_languages=["fr"])


def main():
    analyzer = build()
    docs = [json.loads(l) for l in BENCH.open(encoding="utf-8")]
    t0 = time.perf_counter()
    with (HERE / "pred_presidio.jsonl").open("w", encoding="utf-8") as f:
        for d in docs:
            res = analyzer.analyze(text=d["text"], language="fr", score_threshold=0.4)
            spans = [{"label": r.entity_type, "start": r.start, "end": r.end, "score": r.score, "text": d["text"][r.start:r.end]} for r in res]
            f.write(json.dumps({"id": d["id"], "spans": spans}, ensure_ascii=False) + "\n")
    dt = time.perf_counter() - t0
    print(f"presidio: {len(docs)} docs in {dt:.1f}s ({1000 * dt / len(docs):.0f} ms/doc)")


if __name__ == "__main__":
    main()
