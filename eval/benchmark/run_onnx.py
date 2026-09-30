"""Run an ONNX BIO token-classification model over the benchmark.

python eval/benchmark/run_onnx.py nym       -> eval/benchmark/pred_nym.jsonl
python eval/benchmark/run_onnx.py astrlink  -> eval/benchmark/pred_astrlink.jsonl
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from huggingface_hub import snapshot_download
from tokenizers import Tokenizer

HERE = Path(__file__).resolve().parent
BENCH = HERE / "fr_pii_bench_v0.jsonl"

MODELS = {
    "nym": dict(repo="Wismut/nym-pii-multilingual-small", sub="edge-int8", onnx="model_int8.onnx", labels="config.json", max_len=8192),
    "astrlink": dict(repo="QuantumNous/astrlink-guard", sub="int8", onnx="model_int8.onnx", labels="labels.json", max_len=512),
}


def load(name):
    m = MODELS[name]
    # local_dir (no symlinks): onnxruntime refuses external-data files that resolve outside the model directory
    local = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "local" / m["repo"].replace("/", "__")
    d = Path(snapshot_download(m["repo"], allow_patterns=[m["sub"] + "/*", "config.json"], local_dir=str(local))) / m["sub"]
    tok = Tokenizer.from_file(str(d / "tokenizer.json"))
    cfg = json.load(open(d / m["labels"] if (d / m["labels"]).exists() else d.parent / m["labels"], encoding="utf-8"))
    id2label = {int(k): v for k, v in cfg["id2label"].items()}
    sess = ort.InferenceSession(str(d / m["onnx"]), providers=["CPUExecutionProvider"])
    return tok, id2label, sess, [i.name for i in sess.get_inputs()], m["max_len"]


def decode(text, ids, offsets, logits, id2label):
    probs = np.exp(logits - logits.max(-1, keepdims=True))
    probs /= probs.sum(-1, keepdims=True)
    spans, cur = [], None
    for lab, p, (s, e) in zip(probs.argmax(-1), probs.max(-1), offsets):
        if s == e:
            continue
        tag, _, kind = id2label[int(lab)].partition("-")
        if tag == "O":
            cur = None
        elif tag == "B" or cur is None or cur["label"] != kind:
            cur = {"label": kind, "start": s, "end": e, "score": float(p)}
            spans.append(cur)
        else:
            cur["end"] = e
            cur["score"] = min(cur["score"], float(p))
    for sp in spans:
        sp["text"] = text[sp["start"]:sp["end"]]
    return spans


def predict(text, tok, id2label, sess, inputs, max_len, stride=128):
    enc = tok.encode(text)
    ids, offsets = enc.ids, enc.offsets
    if len(ids) <= max_len:
        chunks = [(0, len(ids))]
    else:  # sliding windows on raw token positions; specials are already inside ids for short docs only
        chunks, i = [], 0
        while i < len(ids):
            chunks.append((i, min(i + max_len, len(ids))))
            if i + max_len >= len(ids):
                break
            i += max_len - stride
    all_spans = []
    for a, b in chunks:
        arr = np.array([ids[a:b]], dtype=np.int64)
        feed = {"input_ids": arr, "attention_mask": np.ones_like(arr)}
        if "token_type_ids" in inputs:
            feed["token_type_ids"] = np.zeros_like(arr)
        logits = sess.run(None, feed)[0][0]
        all_spans += decode(text, ids[a:b], offsets[a:b], logits, id2label)
    # merge overlapping windows: keep first occurrence by start
    out, seen = [], set()
    for sp in sorted(all_spans, key=lambda s: (s["start"], -s["end"])):
        if sp["start"] in seen:
            continue
        seen.add(sp["start"])
        out.append(sp)
    return out


def main():
    name = sys.argv[1]
    tok, id2label, sess, inputs, max_len = load(name)
    docs = [json.loads(l) for l in BENCH.open(encoding="utf-8")]
    t0 = time.perf_counter()
    with (HERE / f"pred_{name}.jsonl").open("w", encoding="utf-8") as f:
        for d in docs:
            spans = predict(d["text"], tok, id2label, sess, inputs, max_len)
            f.write(json.dumps({"id": d["id"], "spans": spans}, ensure_ascii=False) + "\n")
    dt = time.perf_counter() - t0
    print(f"{name}: {len(docs)} docs in {dt:.1f}s ({1000 * dt / len(docs):.0f} ms/doc), inputs={inputs}")


if __name__ == "__main__":
    main()
