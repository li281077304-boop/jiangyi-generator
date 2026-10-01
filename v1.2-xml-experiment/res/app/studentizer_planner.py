"""Full-scope reviewed evidence gate. No automatic answer-ownership inference.

Two reviewed contracts are accepted, and only these two:

- ``CompleteStudentEvidence``: frozen-A-Line-QG-bound complete Golden evidence.
- ``PhysicalRangeSemantics``: an exhaustive independently reviewed physical
  body ledger with exact reviewed prompt/answer ranges and an exact approved
  after-root digest. This is the capability verified in C3 R7 and is the
  contract production reviewed manifests use.

Neither contract is inferred from role, colour, marker, filename or upload
switches. Both fail closed, and neither can create removal authority by itself.
"""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import re
import json
import time
import zipfile

from lxml import etree
from semantic_facade import analyze_source, read_source_snapshot
from studentizer import (AnswerBinding, StudentizerSemantics, StudentizerResult,
                         element_sha256, prepare_student, TAG, FALLBACK, _plan)
from studentizer_ranges import PhysicalRangeSemantics


@dataclass(frozen=True)
class ReviewedBody:
    index: int
    sha256: str
    classification: str  # question, knowledge, material, layout, answer
    candidate_review: str | None = None  # remove / preserve after Golden review


@dataclass(frozen=True)
class CompleteStudentEvidence:
    source_sha256: str
    semantic_sha256: str
    review_id: str
    body: tuple[ReviewedBody, ...]
    question_ids: tuple[str, ...]
    bindings: tuple[AnswerBinding, ...]
    golden_document_sha256: str
    coverage_basis: str = "EXACT_REVIEWED_GOLDEN"


class CoverageRejected(ValueError):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(detail)


def _reject(code, detail):
    raise CoverageRejected(code, detail)


def semantic_fingerprint(snapshot):
    return sha256(json.dumps(snapshot.units, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':')).encode('utf-8')).hexdigest()


def reviewed_range_plan(data, snapshot, evidence):
    """Cross-check a reviewed physical-range ledger against the exact source.

    The Studentizer itself revalidates every fingerprint, the complete ledger
    coverage, the boundary inventory and the exact approved after-root before
    publishing anything. This gate additionally proves that the evidence binds
    this exact byte snapshot and that it carries usable review provenance, so a
    mismatch is reported with a precise ``STUDENTIZER_*`` reason instead of a
    generic preparation failure.
    """
    if evidence is None:
        _reject("STUDENTIZER_COVERAGE_UNPROVEN", "no reviewed evidence for this exact source")
    if not isinstance(evidence, PhysicalRangeSemantics):
        _reject("STUDENTIZER_COVERAGE_UNPROVEN", "unsupported reviewed evidence contract")
    digest = sha256(data).hexdigest()
    if evidence.source_sha256 != digest or snapshot.source_sha256 != digest:
        _reject("STUDENTIZER_SOURCE_IDENTITY_MISMATCH", "source/evidence/semantic digest mismatch")
    if not evidence.review_id or not re.fullmatch(r"[0-9a-f]{64}", str(evidence.expected_document_sha256)):
        _reject("STUDENTIZER_COVERAGE_UNPROVEN", "reviewed range provenance or approved after-root missing")
    if not evidence.body or not evidence.ranges:
        _reject("STUDENTIZER_COVERAGE_INCOMPLETE", "reviewed range evidence is not exhaustive")
    return evidence, {"scope_blocks": len(evidence.body), "reviewed_ranges": len(evidence.ranges),
                      "removed_blocks": sum(1 for row in evidence.body if row.decision == "REMOVE"),
                      "answer_paragraphs": sum(1 for row in evidence.body if row.decision == "REMOVE"),
                      "question_groups": len(evidence.ranges),
                      "review_id": evidence.review_id,
                      "coverage_basis": "EXACT_REVIEWED_GOLDEN_PHYSICAL_RANGE"}


def complete_plan(data, snapshot, evidence):
    """Cross-check caller-reviewed complete Golden evidence with frozen A-Line.

    Human-reviewed Golden content correctness is the evidence-provider trust
    boundary; neither a Boolean `complete` nor role/color predictions qualify.
    No real-source evidence provider is shipped in this round.
    """
    if not isinstance(evidence, CompleteStudentEvidence):
        _reject("STUDENTIZER_COVERAGE_UNPROVEN", "no complete reviewed Golden evidence")
    digest = sha256(data).hexdigest()
    if evidence.source_sha256 != digest or snapshot.source_sha256 != digest:
        _reject("STUDENTIZER_SOURCE_IDENTITY_MISMATCH", "source/evidence/semantic digest mismatch")
    if evidence.semantic_sha256 != semantic_fingerprint(snapshot):
        _reject("STUDENTIZER_SOURCE_IDENTITY_MISMATCH", "QG/section/span semantic manifest mismatch")
    if not evidence.review_id or evidence.coverage_basis != "EXACT_REVIEWED_GOLDEN":
        _reject("STUDENTIZER_COVERAGE_UNPROVEN", "reviewed Golden provenance missing")
    with zipfile.ZipFile(BytesIO(data)) as package:
        root = etree.fromstring(package.read("word/document.xml"), etree.XMLParser(resolve_entities=False, no_network=True))
    body = root.find(TAG("body")); children = list(body)
    entries = {entry.index: entry for entry in evidence.body}
    if len(entries) != len(evidence.body) or set(entries) != set(range(len(children))):
        _reject("STUDENTIZER_COVERAGE_INCOMPLETE", "each source body block needs one reviewed classification")
    for index, child in enumerate(children):
        entry = entries[index]
        if entry.sha256 != element_sha256(child):
            _reject("STUDENTIZER_SOURCE_IDENTITY_MISMATCH", "body address fingerprint mismatch")
        if entry.classification not in {"question", "knowledge", "material", "layout", "answer"}:
            _reject("STUDENTIZER_COVERAGE_INCOMPLETE", "unclassified source content")
        if child.tag == TAG("tbl"):
            _reject("STUDENTIZER_TABLE_SCOPE_UNSUPPORTED", "initial complete scope does not support tables/cells")
        if any(n.tag == TAG("txbxContent") for n in child.iter()):
            _reject("STUDENTIZER_TEXTBOX_SCOPE_UNSUPPORTED", "initial complete scope does not support textboxes")
        text = "".join(child.itertext())
        marker = bool(re.search(r"【(?:答案|解析|详解|解答)】|参考答案|参考解析|[（(](?:答案|解析|详解)[）)]", text))
        explicit_red = False
        for color in child.iter(TAG("color")):
            value = color.get(TAG("val"), "")
            try:
                explicit_red |= len(value) == 6 and int(value[:2], 16) >= 100 and int(value[2:4], 16) <= 70 and int(value[4:], 16) <= 70
            except ValueError:
                pass
        if marker or explicit_red:
            expected = "remove" if entry.classification == "answer" else "preserve"
            if entry.candidate_review != expected:
                _reject("STUDENTIZER_UNHANDLED_ANSWER_CANDIDATE", "candidate requires explicit reviewed removal/preservation decision")
    questions = {u['id']: u for u in snapshot.units if u.get('role') == 'question_group'}
    if len(set(evidence.question_ids)) != len(evidence.question_ids) or set(evidence.question_ids) != set(questions):
        _reject("STUDENTIZER_COVERAGE_INCOMPLETE", "all frozen A-Line QGs must be reviewed")
    answer_indices = {entry.index for entry in evidence.body if entry.classification == "answer"}
    if answer_indices != {b.answer_index for b in evidence.bindings}:
        _reject("STUDENTIZER_COVERAGE_INCOMPLETE", "all answer paragraphs must have exact ownership bindings")
    if not evidence.bindings:
        _reject("STUDENTIZER_COVERAGE_UNPROVEN", "no supported removable answer scope")
    for binding in evidence.bindings:
        unit = questions.get(binding.owner_id)
        if not unit or binding.review_id != evidence.review_id:
            _reject("STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN", "binding is not a reviewed QG identity")
        spans = unit.get('spans', [])
        if not spans or any(not re.fullmatch(r'b\d+', str(node)) for pair in spans for node in pair):
            _reject("STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN", "complex QG endpoint unsupported")
        start = min(int(pair[0][1:]) for pair in spans)
        end = max(int(pair[1][1:]) for pair in spans)
        if start != binding.owner_start or end >= binding.answer_index:
            _reject("STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN", "answer ownership conflicts with frozen QG span")
        if entries[start].classification != 'question':
            _reject("STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN", "owner start is not reviewed question content")
    semantics = StudentizerSemantics(digest, evidence.bindings,
                                    tuple(i for i in entries if i not in answer_indices))
    # Apply only to an in-memory copy to verify the independently reviewed exact
    # Golden document before any derived file is created. No text search.
    try:
        _plan(root, semantics)
    except Exception as exc:
        _reject(getattr(exc, 'code', 'STUDENTIZER_COVERAGE_UNPROVEN'), str(getattr(exc, 'detail', exc)))
    if element_sha256(root) != evidence.golden_document_sha256:
        _reject("STUDENTIZER_GOLDEN_COMPARISON_FAILED", "complete projected document does not match reviewed Golden")
    return semantics, {'scope_blocks': len(children), 'question_groups': len(questions),
                       'answer_paragraphs': len(answer_indices), 'review_id': evidence.review_id,
                       'coverage_basis': evidence.coverage_basis}


def prepare_complete_student(source, output, evidence_provider=None):
    """Prepare a student source through the reviewed gate, or fail closed.

    Returns ``(StudentizerResult, coverage | None)``. A refusal never leaves a
    partial derivative behind and never reports ``XML_PREPARED``.
    """
    started = time.perf_counter(); digest = ''
    try:
        data, _name = read_source_snapshot(source); digest = sha256(data).hexdigest()
        snapshot = analyze_source(data)
        frozen_semantics = semantic_fingerprint(snapshot)
        evidence = evidence_provider(snapshot, data) if evidence_provider else None
        if semantic_fingerprint(snapshot) != frozen_semantics:
            _reject("STUDENTIZER_SOURCE_IDENTITY_MISMATCH", "evidence provider mutated frozen A-Line semantics")
        if isinstance(evidence, PhysicalRangeSemantics):
            semantics, coverage = reviewed_range_plan(data, snapshot, evidence)
        else:
            semantics, coverage = complete_plan(data, snapshot, evidence)
        result = prepare_student(data, semantics, output)
        return result, coverage
    except Exception as exc:
        return StudentizerResult(FALLBACK, None, digest,
                                 reason_code=getattr(exc, 'code', 'STUDENTIZER_XML_PREPARATION_FAILED'),
                                 reason_detail=str(exc),
                                 elapsed_seconds=round(time.perf_counter()-started, 6)), None
