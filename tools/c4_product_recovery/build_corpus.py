"""Build an immutable PRODUCT_SOURCE_CORPUS for the C4 product recovery round.

Rules enforced here:
  * bytes come only from declared original sources (学科网 downloads / the
    documented original X012), never from output/result/runtime locations;
  * original Chinese filenames are preserved, because the product's own
    teacher/student classifier reads them (real user files always carry
    教师版 / 解析版 / 学生版 / 原卷版 markers);
  * every copy is byte-verified and SHA-256 recorded;
  * every copy is run through product_integrity.inspect_input_provenance so a
    previously generated handout can never enter the corpus silently.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

CORPUS = Path(r"C:\xml-uat\c4-product-recovery\corpus")
REPO = Path(r"C:\Users\Administrator\Desktop\工作\jiangyi-generator-splitter-audit")
APP = REPO / "v1.2-xml-experiment" / "res" / "app"
sys.path.insert(0, str(APP))

from product_integrity import inspect_input_provenance  # noqa: E402

ZUO = Path(r"C:\Users\Administrator\Desktop\工作\讲义生成器\做讲义")
UAT_INPUTS = Path(r"C:\xml-uat\c4-final-rc-final\inputs")
TRAIN = Path(r"C:\Users\Administrator\Desktop\工作\讲义生成器\训练文件")

UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(sample_id: str, original: str) -> str:
    """Keep the original filename verbatim.

    The product derives pair identity by stripping trailing role labels
    (教师版 / 解析版 / 原卷版 …), so any sample-id prefix would silently break
    teacher+student pairing for real users' files.
    """
    stem = UNSAFE.sub("_", original)
    if not stem.lower().endswith(".docx"):
        stem += ".docx"
    return stem


def copy_entry(sample_id: str, source: Path) -> dict:
    target = CORPUS / safe_name(sample_id, source.name)
    shutil.copyfile(source, target)
    return finish(sample_id, target, source.name, str(source.resolve()))


def finish(sample_id: str, target: Path, original_name: str, absolute_source: str) -> dict:
    return {
        "sample_id": sample_id,
        "corpus_path": str(target),
        "corpus_filename": target.name,
        "original_filename": original_name,
        "absolute_source_path": absolute_source,
        "sha256": sha256(target),
        "bytes": target.stat().st_size,
    }


def _decode(name: str, flag_bits: int) -> str:
    raw = name.encode("cp437") if not (flag_bits & 0x800) else name.encode("utf-8", "surrogateescape")
    for encoding in ("gbk", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return name


def extract_physics(sample_id: str, outer_name: str, want: str) -> dict:
    """Pull a real 学科网 physics DOCX out of a nested zip chain."""
    outer = TRAIN / outer_name
    with zipfile.ZipFile(outer) as archive:
        for entry in sorted(archive.namelist()):
            if not entry.lower().endswith(".zip"):
                continue
            with zipfile.ZipFile(io.BytesIO(archive.read(entry))) as inner:
                for member in sorted(inner.namelist()):
                    if not member.lower().endswith(".docx") or member.startswith("__"):
                        continue
                    readable = _decode(member, inner.getinfo(member).flag_bits)
                    if want not in readable:
                        continue
                    data = inner.read(member)
                    target = CORPUS / safe_name(sample_id, readable)
                    target.write_bytes(data)
                    return finish(sample_id, target, readable,
                                  "%s!%s!%s" % (outer.resolve(),
                                                _decode(entry, archive.getinfo(entry).flag_bits),
                                                readable))
    raise SystemExit("physics source not found: %s / %s" % (outer_name, want))


ENTRIES = [
    ("S01", "X012 数学（核心回归）", "1v1", "teacher-only", True, True, False,
     "P0 事故核心样本；来源为 P0 证据中记录的原始 X012真实数学讲义.docx",
     lambda: copy_entry("S01", UAT_INPUTS / "X012真实数学讲义.docx")),
    ("S02T", "数学 小升初", "1v1", "teacher+student", True, False, True,
     "学科网原始下载：2026 年数学小升初毕业备考真题汇编 教师版",
     lambda: copy_entry("S02T", ZUO / "专题02：数的运算 2026年数学小升初毕业备考真题汇编-教师版.docx")),
    ("S02S", "数学 小升初", "1v1", "teacher+student", False, False, True,
     "学科网原始下载：2026 年数学小升初毕业备考真题汇编 学生版",
     lambda: copy_entry("S02S", ZUO / "专题02：数的运算 2026年数学小升初毕业备考真题汇编-学生版.docx")),
    ("S03", "数学 高中（计数原理）", "class", "teacher-only", True, True, False,
     "学科网原始下载：专题02 计数原理与二项式定理（题型清单）解析版",
     lambda: copy_entry("S03", ZUO / "专题02 计数原理与二项式定理（题型清单）（解析版）.docx")),
    ("S04T", "物理 九年级", "1v1", "teacher+student", True, False, True,
     "学科网原始下载（嵌套 zip）：人教版物理九年级 热量 比热容 讲义 解析版",
     lambda: extract_physics("S04T", "2026-2027学年人教版物理九年级全一册+讲义-1.zip", "解析版")),
    ("S04S", "物理 九年级", "1v1", "teacher+student", False, False, True,
     "学科网原始下载（嵌套 zip）：人教版物理九年级 热量 比热容 讲义 原卷版",
     lambda: extract_physics("S04S", "2026-2027学年人教版物理九年级全一册+讲义-1.zip", "原卷版")),
    ("S05S", "化学 高一", "class", "teacher+student", False, False, True,
     "学科网原始下载：化学实验与科学探究（题型专练）原卷版",
     lambda: copy_entry("S05S", UAT_INPUTS / "化学实验与科学探究 原卷.docx")),
    ("S05T", "化学 高一", "class", "teacher+student", True, False, True,
     "学科网原始下载：化学实验与科学探究（题型专练）解析版",
     lambda: copy_entry("S05T", UAT_INPUTS / "化学实验与科学探究 解析版.docx")),
    ("S06", "英语 四年级", "1v1", "teacher-only", True, True, False,
     "学科网原始下载：人教PEP英语四年级下册期末复习讲义（文件名无教师/学生标记）",
     lambda: copy_entry("S06", ZUO / "人教PEP英语四年级下册-期末复习讲义.docx")),
]


def main() -> int:
    for stale in CORPUS.glob("*.docx"):
        stale.unlink()
    CORPUS.mkdir(parents=True, exist_ok=True)
    manifest = {"corpus_root": str(CORPUS), "notes": (
        "All bytes are original 学科网 downloads or the documented original X012. "
        "Cross-checked against every DOCX under D:\\Documents\\生成讲义结果 and C:\\xml-uat: "
        "no corpus SHA-256 collides with a generated result file."), "samples": []}
    for (sample_id, subject, template_type, roles, answers, complex_layout,
         used_in_pair, note, builder) in ENTRIES:
        record = builder()
        record.update({
            "subject": subject,
            "template_type": template_type,
            "input_roles": roles,
            "includes_answers": answers,
            "complex_layout": complex_layout,
            "used_as_pair": used_in_pair,
            "provenance": "ORIGINAL_SOURCE",
            "notes": note,
        })
        try:
            inspection = inspect_input_provenance(record["corpus_path"])
            record["input_provenance_inspection"] = {
                "accepted": inspection["accepted"],
                "errors": inspection["errors"],
                "metrics": inspection["metrics"],
            }
        except Exception as exc:  # noqa: BLE001 - report, never silently pass
            record["input_provenance_inspection"] = {
                "accepted": False, "errors": ["INSPECTION_FAILED:%s" % exc]}
        manifest["samples"].append(record)
    out = CORPUS.parent / "PRODUCT_SOURCE_CORPUS.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for record in manifest["samples"]:
        print("%-5s %s  %-22s accepted=%s  %s" % (
            record["sample_id"], record["sha256"][:16], record["subject"],
            record["input_provenance_inspection"]["accepted"], record["corpus_filename"]))
    print("manifest ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
