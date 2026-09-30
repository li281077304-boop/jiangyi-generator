#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-run the (patched) Stage2/Stage3 splitter over the 8 Stage3 samples.

Writes `<out>/<sid>/prediction.json` in the same shape the frozen baseline uses,
so `run_approved_gold_compare.py --predictions-dir <out>` can measure it and the
Before/After numbers stay directly comparable.

Reads only the staged source DOCX (`sources/<sid>.docx`); never touches Gold,
StructDoc or the frozen baseline directory.

Usage:
    python rerun_predictions.py --out C:\\xml-uat\\stage3-e1-after
"""
import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "v1.2-xml-experiment", "res", "app"))
sys.path.insert(0, os.path.join(ROOT, "tools", "stage2_baseline"))

from run_baseline import predict  # noqa: E402
from struct_doc import read_struct_doc_bytes  # noqa: E402

STAGE3 = r"C:\xml-uat\stage3-expansion"
SOURCES = os.path.join(STAGE3, "sources")
INPUTS = os.path.join(STAGE3, "baseline_inputs.json")
SAMPLES = ["X003", "X004", "X006", "X012", "X013", "X019", "X021", "X025"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples", default=",".join(SAMPLES))
    args = ap.parse_args()

    meta = {s["sample_id"]: s for s in json.load(open(INPUTS, encoding="utf-8"))["samples"]}
    rows = []
    for sid in [s for s in args.samples.split(",") if s]:
        path = os.path.join(SOURCES, "%s.docx" % sid)
        data = open(path, "rb").read()
        sha = hashlib.sha256(data).hexdigest()
        expected = meta[sid]["source_sha256"]
        t0 = time.perf_counter()
        doc = read_struct_doc_bytes(data, name="%s.docx" % sid)
        _index, units = predict(doc)
        elapsed = time.perf_counter() - t0
        out_dir = os.path.join(args.out, sid)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "prediction.json"), "w", encoding="utf-8") as fh:
            json.dump({"sample_id": sid, "baseline_commit": "WORKING-TREE-PATCHED",
                       "units": units}, fh, ensure_ascii=False, indent=2)
        qg = sum(1 for u in units if u["role"] == "question_group")
        rows.append({"sample_id": sid, "sha256_ok": sha == expected, "units": len(units),
                     "question_group": qg, "elapsed": round(elapsed, 4)})
        print("%-6s units=%-4d QG=%-3d sha_ok=%s (%.2fs)"
              % (sid, len(units), qg, sha == expected, elapsed))

    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump({"samples": rows, "note": "patched splitter re-run for Before/After measurement"},
                  fh, ensure_ascii=False, indent=2)
    print("\n预测已写出:", args.out)


if __name__ == "__main__":
    sys.exit(main())
