"""Write a fictional, evaluator-shaped run into a fresh directory."""
import argparse
import hashlib
import json
from pathlib import Path


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_example(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    folder = output / "S01"
    folder.mkdir()
    texts = ["星岛课堂（虚构封面）", "三角形有三条边。", "画一个三角形。", "比较两个三角形的周长。"]
    # A shared placeholder digest models the evaluator's recorded source identity.
    digest = hashlib.sha256("fictional source".encode()).hexdigest()
    blocks = [dict(id=f"b{i}", text=text, kind="paragraph", textbox_texts=[],
                   images_count=int(i == 2), oles_count=int(i == 3), math_count=int(i == 1))
              for i, text in enumerate(texts)]
    save(folder / "source_dump.json", dict(sha256=digest, blocks=blocks, nodes=[], units=[]))
    templates = {}
    for template, tier in (("1v1", "SEMANTIC"), ("class", "PRESERVATION")):
        slots = {slot: dict(spans=[], block_count=0, text_summaries=[])
                 for slot in ("knowledge", "immediate", "final")}
        records = []
        for i, destination in enumerate((None, "knowledge", "immediate", "final")):
            if i and tier == "PRESERVATION":
                destination = "knowledge"
            block_id = f"b{i}"
            records.append(dict(block_id=block_id, source_index=i, kind="paragraph",
                                destination_slot=destination, unit_contributors=[],
                                exclusion_reason=None if i else "COVER_METADATA_PROJECTED_TO_TEMPLATE_COVER"))
            if destination:
                slot = slots[destination]
                slot["block_count"] += 1
                slot["spans"].append(dict(start=block_id, end=block_id))
                slot["text_summaries"].append(dict(block_id=block_id, text=texts[i]))
        item = dict(status="PLAN_CREATED_NOT_SEMANTICALLY_VERIFIED",
                    template_sha256=hashlib.sha256(template.encode()).hexdigest(),
                    evidence=dict(selected_tier=tier, source_sha256=digest,
                                  pair_alignment="NOT_REQUIRED_NOT_VERIFIED"),
                    slots=slots, block_records=records)
        save(folder / (template + ".json"), item)
        templates[template] = item
    sample = dict(id="S01", status="ASSESSED", analysis_mode="SEMANTIC", templates=templates,
                  expected_sha256=digest, sha256_before=digest, sha256_after=digest,
                  snapshot_sha256=digest, source_unchanged=True, block_count=len(blocks))
    save(folder / "assessment.json", sample)
    save(output / "report.json", dict(sources=[sample]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    make_example(parser.parse_args().output)
