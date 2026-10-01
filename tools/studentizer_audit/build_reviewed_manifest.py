"""Build a production reviewed-evidence manifest from an approved Golden review.

This tool is read-only with respect to every source and approved artifact. It
converts the independently approved Chief ledger plus the reviewed candidate
packet into a self-contained, exact-source-keyed manifest that the production
registry can consume.

The produced manifest is *not* trusted by construction: it is verified by
running the public ``studentizer.prepare_student`` contract against the exact
source bytes and requiring ``XML_PREPARED`` with the approved candidate DOCX
digest. A wrong ledger, wrong acknowledgement set or stale fingerprint makes
this tool fail instead of emitting a manifest.

Usage:
    python build_reviewed_manifest.py --source <X008.docx> \
        --packet <X008-source-candidate.json> \
        --approval <C3_X008_INDEPENDENT_GOLDEN_APPROVAL.md> \
        --candidate <X008-candidate-expected-student.docx> \
        --sample X008 --subject physics --out <manifest.json>
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
import argparse
import json
import re
import sys
import tempfile
import zipfile

from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "v1.2-xml-experiment/res/app"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from probe_approved_source import approved_ledger  # noqa: E402
from studentizer import TAG, element_sha256, prepare_student  # noqa: E402
from studentizer_ranges import (PhysicalRangeSemantics, ReviewedAnswerRange,  # noqa: E402
                               ReviewedPhysicalBody)

MANIFEST_VERSION = 1
CONTRACT = "REVIEWED_PHYSICAL_RANGE_V1"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_CROSS_STORY_SKIP = {"word/document.xml"}


def referenced_targets(root, parts):
    """Collect every bookmark target referenced by the package, exactly as the
    studentizer boundary validator does (main story + cross-story parts).

    Mirrors ``studentizer_ranges._boundaries`` target collection. Drift cannot
    ship silently because the produced manifest is verified end to end below.
    """
    names = {node.get(TAG("name")) for node in root.iter(TAG("bookmarkStart"))}
    targets = set()
    for node in root.iter(TAG("hyperlink")):
        anchor = node.get(TAG("anchor"))
        if anchor:
            targets.add(anchor)
    for node in root.iter(TAG("instrText")):
        text = node.text or ""
        match = (re.search(r"\b(?:PAGEREF|REF)\s+(\"[^\"]+\"|[^\s\\]+)", text, re.I)
                 or re.search(r"\bHYPERLINK\s+\\l\s+(\"[^\"]+\"|[^\s\\]+)", text, re.I))
        if match:
            targets.add(match.group(1).strip('"'))
    for name, data in parts.items():
        if not name.startswith("word/") or not name.endswith(".xml") or name in _CROSS_STORY_SKIP:
            continue
        other = etree.fromstring(data, etree.XMLParser(resolve_entities=False, no_network=True))
        for node in other.iter(TAG("hyperlink")):
            anchor = node.get(TAG("anchor"))
            if anchor:
                targets.add(anchor)
        for node in other.iter(TAG("instrText")):
            text = node.text or ""
            match = (re.search(r"\b(?:PAGEREF|REF)\s+(\"[^\"]+\"|[^\s\\]+)", text, re.I)
                     or re.search(r"\bHYPERLINK\s+\\l\s+(\"[^\"]+\"|[^\s\\]+)", text, re.I))
            if match:
                targets.add(match.group(1).strip('"'))
    return tuple(sorted(name for name in targets if name and name not in names))


def build(source_path, packet_path, approval_path, candidate_path, sample_id, subject):
    packet = json.loads(Path(packet_path).read_text(encoding="utf-8"))
    approval_text = Path(approval_path).read_text(encoding="utf-8")
    ledger = approved_ledger(approval_path, packet)
    source_path = Path(source_path)
    candidate_path = Path(candidate_path)
    data = source_path.read_bytes()
    digest = sha256(data).hexdigest()
    if digest != packet["source_sha256"]:
        raise SystemExit("source digest does not match the reviewed packet")
    golden = candidate_path.read_bytes()
    if sha256(golden).hexdigest() != packet["candidate_docx_sha256"]:
        raise SystemExit("candidate artifact digest does not match the reviewed packet")
    if not approval_text.count(packet["source_sha256"]):
        raise SystemExit("approval document does not bind this source digest")
    with zipfile.ZipFile(BytesIO(data)) as package:
        parts = {name: package.read(name) for name in package.namelist()}
    root = etree.fromstring(parts["word/document.xml"],
                            etree.XMLParser(resolve_entities=False, no_network=True))
    children = list(root.find(TAG("body")))
    if [element_sha256(node) for node in children] != [row["sha256"] for row in packet["body"]]:
        raise SystemExit("candidate packet body fingerprints do not match the reviewed source")
    missing = referenced_targets(root, parts)

    review_id = packet["review_id"] if "review_id" in packet else "C3-X008-CHIEF-FULL"
    body = tuple(ReviewedPhysicalBody(row["index"], row["sha256"],
                                     "REMOVE" if row["decision"] == "PROPOSE_REMOVE" else "RETAIN",
                                     row["rationale"], review_id, row["owner"]) for row in packet["body"])
    ranges = tuple(ReviewedAnswerRange(question["id"], start, end, answer_start, answer_end,
                                      "Independently approved complete answer and explanation range",
                                      review_id)
                   for question, (_number, start, end, answer_start, answer_end) in zip(packet["questions"], ledger))
    semantics = PhysicalRangeSemantics(digest, review_id, body, ranges,
                                       packet["candidate_expected_document_sha256"], missing)

    with tempfile.TemporaryDirectory() as scratch:
        result = prepare_student(source_path, semantics, Path(scratch) / "verify.docx")
        if result.status != "XML_PREPARED":
            raise SystemExit("manifest verification refused: %s %s" % (result.reason_code, result.reason_detail))
        if result.output_sha256 != packet["candidate_docx_sha256"]:
            raise SystemExit("manifest verification produced a different document than the approved artifact")

    return {
        "manifest_version": MANIFEST_VERSION,
        "contract": CONTRACT,
        "sample_id": sample_id,
        "subject": subject,
        "review_id": review_id,
        "source_sha256": digest,
        "source_bytes": len(data),
        "expected_document_sha256": packet["candidate_expected_document_sha256"],
        "expected_docx_sha256": packet["candidate_docx_sha256"],
        "inherited_missing_bookmark_targets": list(missing),
        "approval_document": str(Path(approval_path).as_posix()),
        "approval_marker": "**X008_GOLDEN_APPROVED**" if sample_id == "X008" else "",
        "candidate_packet": str(Path(packet_path).as_posix()),
        "candidate_packet_sha256": sha256(Path(packet_path).read_bytes()).hexdigest(),
        "removed_blocks": sum(1 for row in body if row.decision == "REMOVE"),
        "retained_blocks": sum(1 for row in body if row.decision == "RETAIN"),
        "reviewed_ranges": len(ranges),
        "body": [{"index": row.index, "sha256": row.sha256, "decision": row.decision,
                  "reason": row.reason, "owner_id": row.owner_id} for row in body],
        "ranges": [{"owner_id": scope.owner_id, "prompt_start": scope.prompt_start,
                    "prompt_end": scope.prompt_end, "answer_start": scope.answer_start,
                    "answer_end": scope.answer_end, "reason": scope.reason} for scope in ranges],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = build(args.source, args.packet, args.approval, args.candidate, args.sample, args.subject)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in
                      ("manifest_version", "contract", "sample_id", "review_id", "source_sha256",
                       "expected_document_sha256", "inherited_missing_bookmark_targets",
                       "removed_blocks", "retained_blocks", "reviewed_ranges")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
