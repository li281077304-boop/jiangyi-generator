"""Standalone, reviewed-allowlist Studentizer; no production routing or COM.

Bindings are trusted, reviewed caller evidence, not A-Line role predictions.
This module never creates answer ownership from color, role, or text matching.
Body addresses are zero-based direct children of w:body on one source snapshot.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import os
import re
import tempfile
import time
import zipfile

from lxml import etree
from package_validator import validate_package
from studentizer_ranges import PhysicalRangeSemantics

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
TAG = lambda name: "{%s}%s" % (W, name)
FALLBACK = "STUDENTIZER_FALLBACK_REQUIRED"
POLICY_VERSION = "reviewed-plain-answer-v1"
QUESTION = re.compile(r"^\s*\d{1,3}[.．、]\s*\S")
ANSWER = re.compile(r"^\s*【(?:答案|解析|详解|解答)】")


@dataclass(frozen=True)
class AnswerBinding:
    owner_id: str
    owner_kind: str
    owner_start: int
    owner_end: int
    answer_index: int
    answer_sha256: str
    relation: str
    review_id: str


@dataclass(frozen=True)
class StudentizerSemantics:
    source_sha256: str
    bindings: tuple[AnswerBinding, ...] = ()
    # Shared material / knowledge / question nodes that must survive unchanged.
    protected_indices: tuple[int, ...] = ()


@dataclass(frozen=True)
class StudentizerPolicy:
    input_version: str = "TEACHER_ONLY"
    source_role: str = "teacher"
    version: str = POLICY_VERSION


@dataclass(frozen=True)
class StudentizerResult:
    status: str
    engine: str | None
    source_sha256: str
    output_path: str | None = None
    output_sha256: str | None = None
    reason_code: str | None = None
    reason_detail: str | None = None
    mutations: tuple[dict, ...] = ()
    validation: dict | None = None
    elapsed_seconds: float = 0.0
    com_invocations: int = 0


def element_sha256(element) -> str:
    """Full structural fingerprint at an exact address, never text search."""
    return sha256(etree.tostring(element, method="c14n")).hexdigest()


def _text(element) -> str:
    return "".join(element.itertext())


class _Unsupported(ValueError):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail


def _refuse(code, detail):
    raise _Unsupported(code, detail)


def _plan(root, semantics):
    body = root.find(TAG("body"))
    if body is None:
        _refuse("STUDENTIZER_XML_PREPARATION_FAILED", "document body missing")
    children = list(body)
    if semantics is None or not semantics.bindings:
        _refuse("STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN", "no reviewed question-answer binding")
    if any(type(i) is not int or not 0 <= i < len(children) for i in semantics.protected_indices):
        _refuse("STUDENTIZER_SOURCE_IDENTITY_MISMATCH", "invalid protected address")
    # Initial scope does not alter documents containing these boundary systems.
    categories = {
        "STUDENTIZER_BOOKMARK_SCOPE_UNSUPPORTED": {"bookmarkStart", "bookmarkEnd", "hyperlink"},
        "STUDENTIZER_REVISION_SCOPE_UNSUPPORTED": {"ins", "del", "moveFrom", "moveTo", "sdt", "customXml", "commentReference", "footnoteReference", "endnoteReference"},
        "STUDENTIZER_FIELD_SCOPE_UNSUPPORTED": {"fldChar", "instrText", "fldSimple"},
    }
    for element in body.iter():
        local = etree.QName(element).localname if isinstance(element.tag, str) else ""
        if local.endswith("Change"):
            _refuse("STUDENTIZER_REVISION_SCOPE_UNSUPPORTED", local)
        for code, names in categories.items():
            if local in names:
                _refuse(code, local)
    removed, mutations = set(), []
    allowed_answer_tags = {TAG(n) for n in ("p", "pPr", "pStyle", "jc", "spacing", "ind", "keepNext", "keepLines", "widowControl", "r", "rPr", "rStyle", "b", "i", "u", "color", "sz", "szCs", "rFonts", "lang", "t")}
    for binding in semantics.bindings:
        if (binding.owner_kind != "question_group" or binding.relation != "reviewed_question_answer"
                or not binding.owner_id or not binding.review_id):
            _refuse("STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN", "section parent / role / unreviewed relation is not deletion authority")
        addresses = (binding.owner_start, binding.owner_end, binding.answer_index)
        if (any(type(i) is not int for i in addresses)
                or not 0 <= binding.owner_start < binding.answer_index == binding.owner_end < len(children)):
            _refuse("STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN", "require terminal answer inside an exact owner interval")
        answer_index = binding.answer_index
        if answer_index in removed or answer_index in semantics.protected_indices:
            _refuse("STUDENTIZER_PRESERVATION_CHECK_FAILED", "duplicate deletion / protected content")
        owner_nodes = children[binding.owner_start:binding.owner_end + 1]
        if any(n.tag == TAG("tbl") for n in owner_nodes):
            _refuse("STUDENTIZER_TABLE_SCOPE_UNSUPPORTED", "owner or answer crosses an atomic table")
        if any(n.tag != TAG("p") for n in owner_nodes):
            _refuse("STUDENTIZER_MIXED_CONTENT_UNSUPPORTED", "owner interval contains a non-paragraph block")
        if not QUESTION.match(_text(owner_nodes[0])):
            _refuse("STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN", "owner start is not a corroborating question paragraph")
        if any(QUESTION.match(_text(n)) for n in owner_nodes[1:-1]):
            _refuse("STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN", "owner crosses another numbered prompt")
        answer = children[answer_index]
        if element_sha256(answer) != binding.answer_sha256:
            _refuse("STUDENTIZER_SOURCE_IDENTITY_MISMATCH", "answer address fingerprint mismatch")
        # Marker is corroboration only. Review supplies ownership and removal
        # authorization; neither marker, numbering nor role alone suffices.
        if not ANSWER.match(_text(answer)):
            _refuse("STUDENTIZER_MIXED_CONTENT_UNSUPPORTED", "only dedicated marked answer paragraphs are supported")
        if any(n.tag == TAG("txbxContent") for n in answer.iter()):
            _refuse("STUDENTIZER_TEXTBOX_SCOPE_UNSUPPORTED", "answer contains textbox content")
        for node in answer.iter():
            if node.tag not in allowed_answer_tags:
                local = etree.QName(node).localname if isinstance(node.tag, str) else "non-element"
                code = "STUDENTIZER_FORMULA_OBJECT_UNSUPPORTED" if local in ("oMath", "oMathPara", "drawing", "pict", "object") else "STUDENTIZER_MIXED_CONTENT_UNSUPPORTED"
                _refuse(code, "unsupported answer child: " + local)
        removed.add(answer_index)
        mutations.append({"operation": "remove_answer_paragraph", "body_index": answer_index,
                          "before_sha256": binding.answer_sha256, "owner_id": binding.owner_id,
                          "relation": binding.relation, "review_id": binding.review_id})
    # An owner's prompt cannot also be another binding's removable answer.
    if any(i in removed for b in semantics.bindings for i in range(b.owner_start, b.owner_end)):
        _refuse("STUDENTIZER_PRESERVATION_CHECK_FAILED", "answer overlaps preserved owner content")
    retained = [element_sha256(n) for i, n in enumerate(children) if i not in removed]
    for i in sorted(removed, reverse=True):
        body.remove(children[i])
    return retained, tuple(mutations)


def prepare_student(source_snapshot: bytes | str | Path,
                    semantic_snapshot: StudentizerSemantics | PhysicalRangeSemantics | None,
                    output_path: str | Path,
                    policy: StudentizerPolicy = StudentizerPolicy()) -> StudentizerResult:
    """Validate and publish a fresh standalone derived source, or fail closed.

    A reviewed caller allowlist is mandatory for teacher input. Frozen A-Line
    SemanticSnapshot does not satisfy that contract. Unsupported cases return
    FALLBACK without an output; this function never invokes fallback or COM.
    PhysicalRangeSemantics is a separate standalone exhaustive reviewed ledger
    and exact-Golden contract; the legacy marked-single-answer scope is unchanged.
    """
    started = time.perf_counter()
    digest = ""
    staging = None
    try:
        source_path = Path(source_snapshot).resolve() if isinstance(source_snapshot, (str, Path)) else None
        data = source_path.read_bytes() if source_path else bytes(source_snapshot)
        digest = sha256(data).hexdigest()
        output = Path(output_path).resolve()
        if source_path == output or output.exists():
            _refuse("STUDENTIZER_PRESERVATION_CHECK_FAILED", "output must be fresh and distinct from source")
        if output.suffix.lower() != ".docx":
            _refuse("STUDENTIZER_XML_PREPARATION_FAILED", "output must be DOCX")
        if policy.version != POLICY_VERSION:
            _refuse("STUDENTIZER_XML_PREPARATION_FAILED", "unsupported policy version")
        bypass = (policy.input_version in ("STUDENT_ONLY", "TEACHER_AND_STUDENT")
                  and policy.source_role == "student")
        if not bypass and (policy.input_version != "TEACHER_ONLY" or policy.source_role != "teacher"):
            _refuse("STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN", "input version and source side must be explicit")
        if not bypass and not isinstance(semantic_snapshot, (StudentizerSemantics, PhysicalRangeSemantics)):
            _refuse("STUDENTIZER_ANSWER_OWNERSHIP_UNPROVEN", "frozen roles/section parents are not reviewed ownership")
        if not bypass and semantic_snapshot.source_sha256 != digest:
            _refuse("STUDENTIZER_SOURCE_IDENTITY_MISMATCH", "semantic snapshot must bind the identical source bytes")
        with zipfile.ZipFile(BytesIO(data)) as source:
            infos = source.infolist()
            if len({i.filename for i in infos}) != len(infos) or source.testzip() is not None:
                _refuse("STUDENTIZER_PACKAGE_VALIDATION_FAILED", "duplicate or corrupt package members")
            parts = {i.filename: source.read(i.filename) for i in infos}
            xml = parts["word/document.xml"]
        root = etree.fromstring(xml, etree.XMLParser(resolve_entities=False, no_network=True))
        mutations = ()
        if bypass:
            generated = data  # Supplied student is preserved byte for byte.
        else:
            if isinstance(semantic_snapshot, PhysicalRangeSemantics):
                from studentizer_ranges import plan_physical_ranges
                retained, mutations = plan_physical_ranges(root, semantic_snapshot, parts)
            else:
                retained, mutations = _plan(root, semantic_snapshot)
            revised = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
            check = etree.fromstring(revised, etree.XMLParser(resolve_entities=False, no_network=True))
            if [element_sha256(n) for n in check.find(TAG("body"))] != retained:
                _refuse("STUDENTIZER_PRESERVATION_CHECK_FAILED", "retained block structure/order changed")
            if isinstance(semantic_snapshot, PhysicalRangeSemantics) and element_sha256(check) != semantic_snapshot.expected_document_sha256:
                _refuse("STUDENTIZER_GOLDEN_COMPARISON_FAILED", "serialized after-root does not match independent Golden")
            buffer = BytesIO()
            with zipfile.ZipFile(buffer, "w") as target:
                for info in infos:
                    target.writestr(info, revised if info.filename == "word/document.xml" else parts[info.filename])
            generated = buffer.getvalue()
            with zipfile.ZipFile(BytesIO(generated)) as package:
                if package.namelist() != [i.filename for i in infos] or any(package.read(name) != value for name, value in parts.items() if name != "word/document.xml"):
                    _refuse("STUDENTIZER_PRESERVATION_CHECK_FAILED", "untouched package member changed")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".docx", delete=False) as handle:
            staging = Path(handle.name)
            handle.write(generated)
        report = validate_package(str(staging))
        if not report.get("valid"):
            _refuse("STUDENTIZER_PACKAGE_VALIDATION_FAILED", str(report))
        # Atomic no-overwrite publication; racing callers cannot replace output.
        os.link(staging, output)
        return StudentizerResult("STUDENT_SOURCE_BYPASS" if bypass else "XML_PREPARED",
                                 "BYPASS" if bypass else "XML", digest, str(output),
                                 sha256(generated).hexdigest(), mutations=mutations, validation=report,
                                 elapsed_seconds=round(time.perf_counter() - started, 6))
    except _Unsupported as exc:
        return StudentizerResult(FALLBACK, None, digest, reason_code=exc.code,
                                 reason_detail=exc.detail, elapsed_seconds=round(time.perf_counter() - started, 6))
    except Exception as exc:
        return StudentizerResult(FALLBACK, None, digest, reason_code="STUDENTIZER_XML_PREPARATION_FAILED",
                                 reason_detail="%s: %s" % (type(exc).__name__, exc),
                                 elapsed_seconds=round(time.perf_counter() - started, 6))
    finally:
        if staging is not None:
            try:
                staging.unlink(missing_ok=True)
            except OSError:
                pass
