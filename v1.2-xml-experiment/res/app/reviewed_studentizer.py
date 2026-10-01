# -*- coding: utf-8 -*-
"""Trusted server-side reviewed Studentizer evidence registry (fail closed).

This module is the production "reviewed coverage gate" data source. It never
infers answer ownership and never grants removal authority on its own:

- A manifest is only usable when its ``source_sha256`` equals the exact bytes
  the planner is holding. There is no filename, role, colour, marker or upload
  switch that enables the XML Studentizer.
- Every manifest carries an exhaustive per-``w:body`` ledger, the reviewed
  prompt/answer ranges, the independently approved expected after-root digest
  and the acknowledged inherited missing bookmark targets. The Studentizer
  revalidates all of them against the real document before any derivative is
  created, so a stale or tampered manifest refuses instead of mutating.
- A manifest is a human-reviewed artifact. Correctness of the review is a
  trusted operator boundary; this module only proves exact identity, complete
  ledger coverage and an exact approved transformation.

Nothing here imports, calls or alters A-Line, the C1 router, the B-Line
renderer or the frozen V0.9 runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import re
import threading

from studentizer_ranges import (PhysicalRangeSemantics, ReviewedAnswerRange,
                                ReviewedPhysicalBody)

MANIFEST_VERSION = 1
CONTRACT = "REVIEWED_PHYSICAL_RANGE_V1"
DEFAULT_MANIFEST_DIR = Path(__file__).resolve().parent / "reviewed_studentizer"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_DECISIONS = {"RETAIN", "REMOVE"}


class ReviewedManifestError(ValueError):
    """A reviewed manifest is missing, malformed or internally inconsistent."""


@dataclass(frozen=True)
class ReviewedManifest:
    sample_id: str
    subject: str
    review_id: str
    source_sha256: str
    expected_document_sha256: str
    inherited_missing_bookmark_targets: tuple[str, ...]
    approval_document: str
    removed_blocks: int
    retained_blocks: int
    reviewed_ranges: int
    manifest_sha256: str
    path: str
    body: tuple[ReviewedPhysicalBody, ...]
    ranges: tuple[ReviewedAnswerRange, ...]

    def semantics(self) -> PhysicalRangeSemantics:
        return PhysicalRangeSemantics(self.source_sha256, self.review_id, self.body,
                                      self.ranges, self.expected_document_sha256,
                                      self.inherited_missing_bookmark_targets)

    def describe(self) -> dict:
        return {"sample_id": self.sample_id, "subject": self.subject,
                "review_id": self.review_id, "source_sha256": self.source_sha256,
                "expected_document_sha256": self.expected_document_sha256,
                "removed_blocks": self.removed_blocks, "retained_blocks": self.retained_blocks,
                "reviewed_ranges": self.reviewed_ranges,
                "manifest_sha256": self.manifest_sha256,
                "approval_document": self.approval_document,
                "contract": CONTRACT, "coverage_basis": "EXACT_REVIEWED_GOLDEN_PHYSICAL_RANGE"}


def _load_manifest(path: Path) -> ReviewedManifest:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReviewedManifestError("%s: unreadable manifest: %s" % (path.name, exc)) from exc
    if not isinstance(raw, dict) or raw.get("manifest_version") != MANIFEST_VERSION:
        raise ReviewedManifestError("%s: unsupported manifest version" % path.name)
    if raw.get("contract") != CONTRACT:
        raise ReviewedManifestError("%s: unsupported evidence contract" % path.name)
    for key in ("sample_id", "subject", "review_id"):
        if not isinstance(raw.get(key), str) or not raw[key].strip():
            raise ReviewedManifestError("%s: missing review provenance: %s" % (path.name, key))
    source_sha256 = raw.get("source_sha256")
    expected = raw.get("expected_document_sha256")
    if not _HEX64.match(str(source_sha256 or "")) or not _HEX64.match(str(expected or "")):
        raise ReviewedManifestError("%s: exact source/after-root identity required" % path.name)
    missing = raw.get("inherited_missing_bookmark_targets")
    if not isinstance(missing, list) or any(not isinstance(item, str) or not item for item in missing):
        raise ReviewedManifestError("%s: inherited acknowledgement list malformed" % path.name)
    if len(set(missing)) != len(missing):
        raise ReviewedManifestError("%s: duplicated inherited acknowledgement" % path.name)
    raw_body = raw.get("body")
    if not isinstance(raw_body, list) or not raw_body:
        raise ReviewedManifestError("%s: exhaustive body ledger required" % path.name)
    body = []
    for row in raw_body:
        if not isinstance(row, dict) or type(row.get("index")) is not int:
            raise ReviewedManifestError("%s: malformed body ledger row" % path.name)
        if row.get("decision") not in _DECISIONS or not str(row.get("reason") or "").strip():
            raise ReviewedManifestError("%s: unreviewed body decision at %s" % (path.name, row.get("index")))
        if not _HEX64.match(str(row.get("sha256") or "")):
            raise ReviewedManifestError("%s: body fingerprint malformed at %s" % (path.name, row.get("index")))
        owner = row.get("owner_id")
        if owner is not None and not isinstance(owner, str):
            raise ReviewedManifestError("%s: body owner malformed at %s" % (path.name, row.get("index")))
        body.append(ReviewedPhysicalBody(row["index"], row["sha256"], row["decision"],
                                        row["reason"], raw["review_id"], owner))
    if sorted(row.index for row in body) != list(range(len(body))):
        raise ReviewedManifestError("%s: body ledger must cover every block exactly once" % path.name)
    raw_ranges = raw.get("ranges")
    if not isinstance(raw_ranges, list) or not raw_ranges:
        raise ReviewedManifestError("%s: reviewed prompt/answer ranges required" % path.name)
    ranges = []
    for scope in raw_ranges:
        if not isinstance(scope, dict) or not str(scope.get("owner_id") or "").strip():
            raise ReviewedManifestError("%s: malformed reviewed range" % path.name)
        if not str(scope.get("reason") or "").strip():
            raise ReviewedManifestError("%s: unreviewed range reason" % path.name)
        addresses = [scope.get(key) for key in ("prompt_start", "prompt_end", "answer_start", "answer_end")]
        if any(type(value) is not int for value in addresses):
            raise ReviewedManifestError("%s: malformed reviewed range addresses" % path.name)
        ranges.append(ReviewedAnswerRange(scope["owner_id"], *addresses, scope["reason"], raw["review_id"]))
    removed = sum(1 for row in body if row.decision == "REMOVE")
    if raw.get("removed_blocks") not in (None, removed):
        raise ReviewedManifestError("%s: declared removal count mismatch" % path.name)
    return ReviewedManifest(raw["sample_id"], raw["subject"], raw["review_id"], source_sha256,
                            expected, tuple(sorted(missing)), str(raw.get("approval_document") or ""),
                            removed, len(body) - removed, len(ranges),
                            sha256(path.read_bytes()).hexdigest(),
                            str(path), tuple(body), tuple(ranges))


class ReviewedRegistry:
    """Exact-source-keyed view of the reviewed evidence directory."""

    def __init__(self, directory: str | Path | None = None):
        self.directory = Path(directory).expanduser().resolve() if directory else DEFAULT_MANIFEST_DIR
        self._by_sha: dict[str, ReviewedManifest] = {}
        if not self.directory.is_dir():
            raise ReviewedManifestError("reviewed evidence directory is missing: %s" % self.directory)
        for path in sorted(self.directory.glob("*.json")):
            manifest = _load_manifest(path)
            if manifest.source_sha256 in self._by_sha:
                raise ReviewedManifestError("duplicate reviewed evidence for one source digest")
            self._by_sha[manifest.source_sha256] = manifest

    def manifests(self) -> tuple[ReviewedManifest, ...]:
        return tuple(self._by_sha[key] for key in sorted(self._by_sha))

    def lookup(self, source_sha256: str) -> ReviewedManifest | None:
        return self._by_sha.get(str(source_sha256 or ""))

    def evidence_provider(self):
        """Return the trusted provider callable used by the production planner.

        The provider only performs an exact-digest lookup. It cannot infer
        ownership and it never mutates the frozen A-Line snapshot.
        """
        def provider(_snapshot, data):
            manifest = self._by_sha.get(sha256(data).hexdigest())
            return manifest.semantics() if manifest is not None else None
        return provider


_CACHE_LOCK = threading.RLock()
_CACHE: dict[str, ReviewedRegistry | ReviewedManifestError] = {}


def registry(directory: str | Path | None = None) -> ReviewedRegistry:
    key = str(Path(directory).expanduser().resolve()) if directory else str(DEFAULT_MANIFEST_DIR)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached is None:
            try:
                cached = ReviewedRegistry(directory)
            except ReviewedManifestError as exc:
                cached = exc
            _CACHE[key] = cached
        if isinstance(cached, ReviewedManifestError):
            raise cached
        return cached


def reset_cache() -> None:
    """Test/compatibility hook; production never needs to clear the cache."""
    with _CACHE_LOCK:
        _CACHE.clear()
