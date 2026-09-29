# -*- coding: utf-8 -*-
"""Regression tests for the frozen Stage2 baseline adapter (no heuristic tuning)."""
import json
import os
import sys

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                       "v1.2-xml-experiment", "res", "app")
BASELINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                            "tools", "stage2_baseline")
sys.path.insert(0, os.path.abspath(APP_DIR))
sys.path.insert(0, os.path.abspath(BASELINE_DIR))

from run_baseline import predict  # noqa: E402
from struct_doc import Block, StructDoc  # noqa: E402


def _fixture():
    texts = ["第一单元", "即时训练", "1．题干", "A. 选项", "B. 选项", "【答案】A"]
    doc = StructDoc(name="baseline-fixture")
    doc.body_size = 21
    doc.blocks = [Block(seq=i, pno=i + 1, kind="paragraph", text=text,
                        eff_sz=32 if i == 0 else 21, is_empty=False)
                  for i, text in enumerate(texts)]
    return doc


def test_baseline_is_deterministic():
    doc = _fixture()
    idx1, first = predict(doc)
    idx2, second = predict(doc)
    assert idx1.order_ids == idx2.order_ids
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == \
        json.dumps(second, ensure_ascii=False, sort_keys=True)
    assert [u["role"] for u in first] == ["section", "question_group", "answer"]


def test_baseline_keeps_original_coarse_roles():
    _, units = predict(_fixture())
    # Original draft rule classifies answer-key headings as answer and does not
    # infer analysis or unknown as separate roles.
    assert not any(u["role"] in ("analysis", "unknown") for u in units)
    assert units[-1]["role"] == "answer"


def test_type_heading_rule_is_frozen_from_gold_draft_generator():
    doc = StructDoc(name="type-heading-fixture")
    doc.body_size = 21
    doc.blocks = [Block(seq=0, pno=1, kind="paragraph", text="题型1 整数运算",
                        eff_sz=21, is_empty=False)]
    _, units = predict(doc)
    assert units[0]["role"] == "question_group"


def test_real_corpus_manifest_has_exact_gold_set():
    path = os.path.join(BASELINE_DIR, "manifest.json")
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    assert [s["sample_id"] for s in manifest["samples"]] == ["S01", "S11", "S12", "S04"]
    assert all(len(s["sha256"]) == 64 for s in manifest["samples"])


ALL = [v for k, v in sorted(globals().items()) if k.startswith("test_")]


def main():
    failures = []
    for test in ALL:
        try:
            test()
            print("PASS %s" % test.__name__)
        except Exception as exc:
            failures.append((test.__name__, exc))
            print("FAIL %s: %s: %s" % (test.__name__, type(exc).__name__, exc))
    print("\n%d passed, %d failed" % (len(ALL) - len(failures), len(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
