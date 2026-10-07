"""Offline OCR evidence for conservative, node-bound image-role routing."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import posixpath
import re
import threading
import zipfile
from typing import Callable, Iterable, Mapping, Optional, Sequence, Tuple


MODEL_FILES = (
    "ch_PP-OCRv4_det_infer.onnx",
    "ch_PP-OCRv4_rec_infer.onnx",
    "ch_ppocr_mobile_v2.0_cls_infer.onnx",
)
DEFAULT_MIN_CONFIDENCE = 0.80


class LocalOCRError(RuntimeError):
    """OCR could not run with the explicitly supplied local runtime/models."""


class LocalOCRRecognizer:
    """Process-local CPU recognizer; load the model set once per process."""

    def __init__(self, model_dir: Path, *, engine_factory=None):
        self.model_dir = Path(model_dir).expanduser().resolve(strict=True)
        self.model_paths = _validated_models(self.model_dir)
        self.model_hashes = {path.name: _sha256(path.read_bytes())
                             for path in self.model_paths}
        self.engine = (engine_factory(self.model_paths) if engine_factory is not None
                       else _create_rapidocr(self.model_paths))
        self._cache: dict[str, LocalOCRResult] = {}
        self._lock = threading.RLock()

    def recognize(self, image_bytes: bytes, *, source_node_id: str) -> LocalOCRResult:
        if not isinstance(image_bytes, bytes) or not image_bytes:
            raise LocalOCRError("OCR source image bytes are empty or invalid")
        if not source_node_id or not source_node_id.strip():
            raise LocalOCRError("OCR source node id is required")
        digest = _sha256(image_bytes)
        with self._lock:
            cached = self._cache.get(digest)
            if cached is not None:
                return cached
            try:
                raw = self.engine(image_bytes)
            except Exception as exc:
                raise LocalOCRError("local OCR inference failed: %s" % exc) from exc
            result = LocalOCRResult(digest, dict(self.model_hashes),
                                    _parse_rapidocr_result(raw), "rapidocr_onnxruntime-cpu")
            if len(self._cache) >= 512:
                self._cache.pop(next(iter(self._cache)))
            self._cache[digest] = result
            return result


_RECOGNIZERS: dict[str, LocalOCRRecognizer] = {}
_RECOGNIZERS_LOCK = threading.RLock()


def get_local_ocr_recognizer(model_dir: Path) -> LocalOCRRecognizer:
    """Reuse one validated CPU model session for the app process lifetime."""
    key = str(Path(model_dir).expanduser().resolve(strict=True))
    with _RECOGNIZERS_LOCK:
        recognizer = _RECOGNIZERS.get(key)
        if recognizer is None:
            recognizer = LocalOCRRecognizer(Path(key))
            _RECOGNIZERS[key] = recognizer
        return recognizer


@dataclass(frozen=True)
class OCRLine:
    text: str
    confidence: float
    box: object = None


@dataclass(frozen=True)
class LocalOCRResult:
    image_sha256: str
    model_sha256: Mapping[str, str]
    lines: Tuple[OCRLine, ...]
    engine: str


@dataclass(frozen=True)
class ImageRoleEvidence:
    image_sha256: str
    source_node_id: str
    role: str
    confidence: str
    matched_cues: Tuple[str, ...]
    evidence_lines: Tuple[OCRLine, ...]
    actionable: bool = False


_ROLE_CUES = (
    ("TEACHING_METADATA", ("教学目标", "教学重难点", "重点难点", "教学重点", "教学难点")),
    ("KNOWLEDGE_ASSET", ("知识清单", "知识回顾", "知识梳理", "知识要点")),
    ("TOPIC_CUE", ("专题", "题型", "考点")),
)
_SPACE_RE = re.compile(r"\s+")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validated_models(model_dir: Path) -> Tuple[Path, ...]:
    root = model_dir.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise LocalOCRError("local OCR model directory is not a directory")
    paths = tuple(root / name for name in MODEL_FILES)
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        raise LocalOCRError("local OCR models missing: " + ", ".join(missing))
    return paths


def _create_rapidocr(paths: Sequence[Path]):
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise LocalOCRError("rapidocr_onnxruntime is not installed") from exc
    det, rec, cls = paths
    try:
        return RapidOCR(
            det_model_path=str(det),
            rec_model_path=str(rec),
            cls_model_path=str(cls),
            det_use_cuda=False,
            rec_use_cuda=False,
            cls_use_cuda=False,
            det_use_dml=False,
            rec_use_dml=False,
            cls_use_dml=False,
        )
    except Exception as exc:
        raise LocalOCRError("could not initialize local CPU OCR engine: %s" % exc) from exc


def _parse_rapidocr_result(raw) -> Tuple[OCRLine, ...]:
    # RapidOCR returns (detections, elapsed); detections are [box, text, score].
    detections = raw[0] if isinstance(raw, tuple) and len(raw) == 2 else raw
    if detections is None:
        return ()
    lines = []
    try:
        for detection in detections:
            if len(detection) < 3:
                raise LocalOCRError("malformed OCR detection")
            box, text, confidence = detection[0], detection[1], float(detection[2])
            if not isinstance(text, str) or not 0.0 <= confidence <= 1.0:
                raise LocalOCRError("invalid OCR text or confidence")
            lines.append(OCRLine(text=text, confidence=confidence, box=box))
    except (TypeError, ValueError) as exc:
        if isinstance(exc, LocalOCRError):
            raise
        raise LocalOCRError("malformed OCR result") from exc
    return tuple(lines)


def recognize_image_local(
    image_path: Path,
    model_dir: Path,
    *,
    engine_factory: Optional[Callable[[Sequence[Path]], object]] = None,
) -> LocalOCRResult:
    """Run CPU OCR from local model files and verify the source bytes stayed intact.

    ``engine_factory`` exists for deterministic tests. Production callers must
    still explicitly supply the model directory; there is no download path.
    """
    image_path = Path(image_path).expanduser().resolve(strict=True)
    if not image_path.is_file():
        raise LocalOCRError("OCR source is not a file")
    image_bytes = image_path.read_bytes()
    if not image_bytes:
        raise LocalOCRError("OCR source image is empty")
    image_sha = _sha256(image_bytes)
    result = LocalOCRRecognizer(model_dir, engine_factory=engine_factory).recognize(
        image_bytes, source_node_id=str(image_path))
    if _sha256(image_path.read_bytes()) != image_sha:
        raise LocalOCRError("source image changed during OCR")
    return result


def _question_asset_nodes(snapshot) -> set[str]:
    question_nodes = set()
    for unit in snapshot.units:
        if unit.get("role") != "question_group":
            continue
        starts = []
        for start, _end in unit.get("spans") or []:
            match = re.match(r"^b(\d+)(?:\.|$)", str(start))
            if match:
                starts.append(int(match.group(1)))
        if starts:
            first = min(starts)
            if 0 <= first < len(snapshot.document.blocks):
                block = snapshot.document.blocks[first]
                text = str(block.text or "")
                if (block.kind == "table" and
                        re.search(r"(?:教学目标|学习目标)", text) and
                        re.search(r"(?:教学重难点|重点难点|重难点)", text)):
                    continue
        for start, end in unit.get("spans") or []:
            for node in snapshot.node_index.interval(str(start), str(end)):
                match = re.match(r"^b(\d+)(?:\.|$)", node)
                if match:
                    question_nodes.add("b" + match.group(1))
    return question_nodes


def requires_local_ocr(snapshot) -> bool:
    """Whether a main-story image is outside all semantic question spans."""
    question_nodes = _question_asset_nodes(snapshot)
    return any(block.images and "b%d" % block.seq not in question_nodes
               for block in snapshot.document.blocks)


def inspect_document_images(source_docx: Path, snapshot, recognizer: LocalOCRRecognizer,
                            *, min_confidence: float = DEFAULT_MIN_CONFIDENCE) -> dict:
    """Classify bound question images structurally and OCR unbound images.

    Images already inside a semantic question span are QUESTION_ASSETs and do
    not need OCR. OCR is reserved for standalone images that may carry section
    meaning, reducing CPU work and preventing question diagrams from becoming
    accidental boundaries.
    """
    source_docx = Path(source_docx).expanduser().resolve(strict=True)
    if not source_docx.is_file():
        raise LocalOCRError("DOCX image source is not a file")
    source_sha = _sha256(source_docx.read_bytes())
    question_nodes = _question_asset_nodes(snapshot)
    targets: dict[str, list[tuple[str, str]]] = {}
    for block in snapshot.document.blocks:
        for image in block.images:
            target = str(image.target or "").replace("\\", "/")
            normalized = posixpath.normpath(target)
            if (not target or normalized in (".", "..") or normalized.startswith("../")
                    or normalized.startswith("/") or ":" in normalized):
                raise LocalOCRError("unsafe DOCX image relationship target at b%d" % block.seq)
            node_id = "b%d" % block.seq
            role = "QUESTION_ASSET" if node_id in question_nodes else "OCR_CANDIDATE"
            targets.setdefault(normalized, []).append((node_id, role))

    by_digest: dict[str, tuple[LocalOCRResult, ImageRoleEvidence]] = {}
    evidence_rows = []
    try:
        with zipfile.ZipFile(source_docx, "r") as package:
            members = set(package.namelist())
            for target, node_ids in targets.items():
                if target not in members:
                    raise LocalOCRError("DOCX image relationship target is missing: %s" % target)
                image_bytes = package.read(target)
                digest = _sha256(image_bytes)
                for node_id, structural_role in node_ids:
                    if structural_role == "QUESTION_ASSET":
                        evidence_rows.append({
                            "image_sha256": digest, "source_node_id": node_id,
                            "role": "QUESTION_ASSET", "confidence": "STRUCTURAL_QUESTION_OWNER",
                            "matched_cues": [], "evidence_lines": [], "actionable": True,
                            "engine": "STRUCTURAL_A_LINE_QUESTION_GROUP", "model_sha256": {},
                        })
                        continue
                    if recognizer is None:
                        raise LocalOCRError("standalone image requires local OCR")
                    cached = by_digest.get(digest)
                    if cached is None:
                        result = recognizer.recognize(image_bytes, source_node_id=node_id)
                        classification = classify_image_role(
                            image_sha256=result.image_sha256,
                            source_node_id=node_id,
                            lines=result.lines,
                            min_confidence=min_confidence,
                        )
                        cached = (result, classification)
                        by_digest[digest] = cached
                    result, classification = cached
                    evidence_rows.append({
                        "image_sha256": result.image_sha256,
                        "source_node_id": node_id,
                        "role": classification.role,
                        "confidence": classification.confidence,
                        "matched_cues": list(classification.matched_cues),
                        "evidence_lines": [
                            {"text": line.text, "confidence": line.confidence}
                            for line in classification.evidence_lines
                        ],
                        "actionable": classification.actionable,
                        "engine": result.engine,
                        "model_sha256": dict(result.model_sha256),
                    })
    except (OSError, zipfile.BadZipFile) as exc:
        raise LocalOCRError("could not inspect DOCX image package: %s" % exc) from exc
    if _sha256(source_docx.read_bytes()) != source_sha:
        raise LocalOCRError("source DOCX changed during OCR image inspection")
    return {
        "source_sha256": source_sha,
        "model_sha256": dict(recognizer.model_hashes) if recognizer else {},
        "engine": "rapidocr_onnxruntime-cpu" if recognizer else "STRUCTURAL_ONLY",
        "images": sorted(evidence_rows, key=lambda row: (
            int(re.match(r"^b(\d+)", row["source_node_id"]).group(1)),
            row["source_node_id"], row["image_sha256"])),
    }


def classify_image_role(
    *,
    image_sha256: str,
    source_node_id: str,
    lines: Iterable[OCRLine],
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> ImageRoleEvidence:
    """Classify only explicit, high-confidence labels; never infer a topic.

    A unique, high-confidence knowledge cue may inform section routing. OCR
    text is never emitted into the DOCX or used to replace the original image.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", image_sha256 or ""):
        raise ValueError("image_sha256 must be a lowercase SHA-256 hex digest")
    if not source_node_id or not source_node_id.strip():
        raise ValueError("source_node_id is required for auditable evidence")
    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError("min_confidence must be between 0 and 1")

    accepted = tuple(
        line for line in lines
        if isinstance(line, OCRLine)
        and line.confidence >= min_confidence
        and line.text.strip()
    )
    roles = []
    matched = []
    for role, cues in _ROLE_CUES:
        evidence = tuple(
            line for line in accepted
            if any(cue in _SPACE_RE.sub("", line.text) for cue in cues)
        )
        if evidence:
            roles.append((role, evidence))
            matched.extend(cue for cue in cues if any(
                cue in _SPACE_RE.sub("", line.text) for line in evidence
            ))

    if len(roles) == 1:
        role, evidence = roles[0]
        status = "HIGH_CONFIDENCE_CUE"
    elif len(roles) > 1:
        role = "AMBIGUOUS"
        evidence = tuple(line for _name, group in roles for line in group)
        status = "CONFLICTING_CUES"
    else:
        role = "UNKNOWN"
        evidence = accepted
        status = "NO_EXPLICIT_CUE"

    return ImageRoleEvidence(
        image_sha256=image_sha256,
        source_node_id=source_node_id,
        role=role,
        confidence=status,
        matched_cues=tuple(dict.fromkeys(matched)),
        evidence_lines=evidence,
        actionable=(role == "KNOWLEDGE_ASSET" and status == "HIGH_CONFIDENCE_CUE"),
    )
