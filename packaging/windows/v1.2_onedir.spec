# -*- mode: python ; coding: utf-8 -*-
"""Pinned Windows x64 onedir recipe. All output paths are supplied externally."""
from pathlib import Path
import os
from PyInstaller.utils.hooks import collect_all

ROOT = Path(os.environ["C4_REPO_ROOT"]).resolve()
APP = ROOT / "v1.2-xml-experiment" / "res" / "app"
WEBAPP = APP / "webapp"
ENTRY = WEBAPP / "windows_launcher.pyw"
if not ENTRY.is_file():
    raise SystemExit("C4 launcher entry is missing: %s" % ENTRY)

datas = []
runtime_module_names = [
    source.stem for source in sorted(APP.glob("*.py"))
    if not source.name.startswith("test_") and source.name != "struct_dump.py"
]


def add_file(source: Path, relative_destination: str) -> None:
    if not source.is_file():
        raise SystemExit("required C4 package resource is missing: %s" % source)
    datas.append((str(source), relative_destination.replace("/", os.sep)))


# Preserve repository-relative roots used by the existing template resolver,
# source-file A-Line loader, and frozen V0.9 runtime loader.
app_rel = Path("v1.2-xml-experiment/res/app")
for source in sorted(APP.glob("*.py")):
    if source.name.startswith("test_") or source.name == "struct_dump.py":
        continue
    add_file(source, str(app_rel))

for source in sorted((WEBAPP / "templates").glob("*")):
    if source.is_file():
        add_file(source, str(app_rel / "webapp" / "templates"))
for source in sorted((WEBAPP / "static").rglob("*")):
    if source.is_file():
        add_file(source, str(app_rel / "webapp" / "static" / source.relative_to(WEBAPP / "static").parent))

ocr_models = APP / "ocr_models"
for source in sorted(ocr_models.glob("*.onnx")):
    add_file(source, str(app_rel / "ocr_models"))
add_file(ocr_models / "NOTICE.md", str(app_rel / "ocr_models"))
if {source.name for source in ocr_models.glob("*.onnx")} != {
        "ch_PP-OCRv4_det_infer.onnx", "ch_PP-OCRv4_rec_infer.onnx",
        "ch_ppocr_mobile_v2.0_cls_infer.onnx"}:
    raise SystemExit("the reviewed offline OCR model set is incomplete")

ocr_hiddenimports = []
binaries = []
for ocr_package in ("rapidocr_onnxruntime", "onnxruntime", "cv2", "numpy", "shapely",
                    "pyclipper", "yaml", "PIL"):
    package_datas, package_binaries, package_hidden = collect_all(ocr_package)
    datas.extend(package_datas)
    binaries.extend(package_binaries)
    ocr_hiddenimports.extend(package_hidden)

# The web entry and job service are discovered as imports, while preserving
# their source files beside the other dynamically loaded app modules is useful
# for audited path-based imports and keeps the reviewed resource tree intact.
for source in (WEBAPP / "app.py", WEBAPP / "job_service.py"):
    add_file(source, str(app_rel / "webapp"))

manifest_dir = APP / "reviewed_studentizer"
for source in sorted(manifest_dir.glob("*.json")):
    add_file(source, str(app_rel / "reviewed_studentizer"))

for template_name in ("2025+1v1讲义模板(2).docx", "2025班课模板.docx"):
    add_file(ROOT / "v1.1-stable" / "res" / "app" / template_name,
             "v1.1-stable/res/app")

baseline_dir = ROOT / "tools" / "stage2_baseline"
add_file(baseline_dir / "run_baseline.py", "tools/stage2_baseline")

v09 = APP / "v09_fallback_runtime"
v09_manifest = v09 / "ASSET_MANIFEST.json"
add_file(v09_manifest, str(app_rel / "v09_fallback_runtime"))
import json
manifest = json.loads(v09_manifest.read_text(encoding="utf-8"))
if manifest.get("baseline_commit") != "0922e08631226b95a77a6599bbc0ac3784e9134b":
    raise SystemExit("V0.9 frozen baseline identity changed")
if len(manifest.get("assets", [])) != 10:
    raise SystemExit("expected the audited ten V0.9 manifest assets")
for asset in manifest["assets"]:
    add_file(v09 / asset["target"], str(app_rel / "v09_fallback_runtime"))

analysis = Analysis(
    [str(ENTRY)],
    pathex=[str(WEBAPP), str(APP)],
    binaries=binaries,
    datas=datas,
    # Keep Flask's root_path tied to the packaged source path so its default
    # templates/static lookup remains inside the audited webapp tree.
    # The web entry is intentionally source-loaded from the resource tree so
    # Flask sees the correct template root. Analyze the source-loaded runtime
    # closure separately, avoiding test modules and retaining their source data
    # for the two audited path-based loaders.
    hiddenimports=runtime_module_names + ["job_service", "flask"] + ocr_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "unittest", "tests", "test_app_api", "app"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="讲义生成器",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="讲义生成器",
)
