"""Verify copied V0.9 application assets against frozen Git blobs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "v1.2-xml-experiment" / "res" / "app" / "v09_fallback_runtime" / "ASSET_MANIFEST.json"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures = []
    for asset in manifest["assets"]:
        local = MANIFEST.parent / asset["target"]
        local_hash = hashlib.sha256(local.read_bytes()).hexdigest() if local.is_file() else None
        blob = subprocess.check_output(["git", "cat-file", "blob", asset["git_blob"]], cwd=ROOT)
        blob_hash = hashlib.sha256(blob).hexdigest()
        if local_hash != asset["sha256"] or local_hash != blob_hash:
            failures.append({"target": asset["target"], "local_sha256": local_hash,
                             "expected_sha256": asset["sha256"], "blob_sha256": blob_hash})
    result = {"baseline_commit": manifest["baseline_commit"],
              "asset_count": len(manifest["assets"]),
              "verified": len(manifest["assets"]) - len(failures),
              "failures": failures}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
