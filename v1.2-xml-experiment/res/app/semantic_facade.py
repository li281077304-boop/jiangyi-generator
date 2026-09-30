# -*- coding: utf-8 -*-
"""Production A-Line facade over the frozen Stage 2 candidate implementation.

The implementation source remains ``tools/stage2_baseline/run_baseline.py``;
this module is the only app-facing import point. It loads the source-tree
dependency by an explicit path instead of adding the tools directory to
``sys.path``. ``predict`` accepts the StructDoc built from the exact byte
snapshot hashed here, so identity and semantic spans refer to one input.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

from struct_doc import StructDoc, read_struct_doc_bytes
from struct_nodes import NodeIndex


APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parents[2]
PREDICTOR_PATH = REPO_ROOT / "tools" / "stage2_baseline" / "run_baseline.py"
_PREDICTOR: Optional[ModuleType] = None


@dataclass(frozen=True)
class SemanticSnapshot:
    source_sha256: str
    source_name: str
    document: StructDoc
    node_index: NodeIndex
    units: list[dict[str, Any]]


def _load_predictor() -> ModuleType:
    global _PREDICTOR
    if _PREDICTOR is not None:
        return _PREDICTOR
    if not PREDICTOR_PATH.is_file():
        raise RuntimeError(
            "A-Line dependency is missing: expected %s" % PREDICTOR_PATH
        )
    spec = spec_from_file_location("jiangyi_c0_stage2_baseline", PREDICTOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load A-Line dependency: %s" % PREDICTOR_PATH)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "predict", None)):
        raise RuntimeError("A-Line dependency has no callable predict(doc)")
    _PREDICTOR = module
    return module


def read_source_snapshot(source: bytes | bytearray | memoryview | str | Path) -> tuple[bytes, str]:
    """Read a path once, or freeze provided bytes, and return bytes + name."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        return path.read_bytes(), path.name
    if isinstance(source, (bytes, bytearray, memoryview)):
        return bytes(source), "<bytes>"
    raise TypeError("source must be DOCX bytes or a filesystem path")


def analyze_source(source: bytes | bytearray | memoryview | str | Path) -> SemanticSnapshot:
    """Parse a single immutable source snapshot and return A-Line semantics."""
    data, name = read_source_snapshot(source)
    digest = sha256(data).hexdigest()
    doc = read_struct_doc_bytes(data, name=name)
    # Keep the eval-identical A-Line rules in the existing Stage 2 source.
    # No rule code is copied or modified in this facade.
    index, units = _load_predictor().predict(doc)
    return SemanticSnapshot(digest, name, doc, index, units)
