#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repeatable Stage 2 baseline, faithfully adapted from _research/gen_gold_draft.py.

This is a baseline snapshot of the old candidate rules, not a new classifier.
Input/output plumbing and reporting are made reproducible; rule thresholds and
candidate decisions below intentionally preserve the original implementation.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from collections import Counter

APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                   "v1.2-xml-experiment", "res", "app"))
sys.path.insert(0, APP)

from gold_compare import compare, render_report, _norm  # noqa: E402
from struct_doc import read_struct_doc_bytes  # noqa: E402
from struct_nodes import NodeIndex, ROOT  # noqa: E402


BLOCK_ROLES = [
    (re.compile(r"^(知识精讲|例题讲解|知识讲解|知识回顾|课堂启动|知识点|归纳总结|课堂小结|"
                r"方法指导|目标导航|知识导图|考点梳理|技法指导|技法点拨|题型解读|考点解读|"
                r"典例剖析|典例精讲|例题精讲|思维导图|要点梳理)"), "knowledge"),
    (re.compile(r"^(即时训练|基础巩固|基础速刷|能力提升|能力跃升|思维挑战|巩固练习|"
                r"提升专练|真题感知|真题闯关|课堂检测|出门测试|当堂检测|达标检测|"
                r"实战演练|写作训练|强化训练|课后作业|随堂练习|变式训练|考点突破|专项训练)"),
     "question_group"),
    (re.compile(r"^(参考答案|答案与解析|答案解析|答案与点拨|答案详解|试题解析|解析与答案|"
                r"【答案】|【解析】|【思路】|解析：)"), "answer"),
]
RE_MATERIAL_HEAD = re.compile(r"^(范文|例文|参考范文|Passage\s*\d|阅读(材料|短文|理解)|"
                              r"材料\s*\d|语篇\s*\d|【材料】|示例)")
RE_TYPE_HEAD = re.compile(r"^(题型|类型|角度|考点|考向|专题)\s*\d+")
RE_TOC_LINE = re.compile(r"(\.{5,}|·{5,}|．{5,})")
RE_TOC_ENTRY = re.compile(r"(\.{3,}|·{3,}|．{3,})\s*\d{1,4}\s*$")
RE_OPTION = re.compile(r"^\s*[A-D][.．、]\s*\S")
RE_QNUM = re.compile(r"^\s*\d{1,3}\s*[．.、]")
RE_TOC_WORD = re.compile(r"^(目录|目　录|Contents)$")
MERGE_ROLES = {"answer", "analysis", "knowledge", "body"}


def detect_question_runs(index, cands):
    """Original candidate rule: infer runs from numbered short/question lines."""
    taken = {c["node"] for c in cands}
    answer_like = {c["node"] for c in cands
                   if c["role"] in ("answer", "analysis", "toc")}
    out = []
    nodes = index.nodes
    i = 0
    while i < len(nodes):
        n = nodes[i]
        t = _norm(n.text)
        if not RE_QNUM.match(t) or n.id in answer_like:
            i += 1
            continue
        run = [n.id]
        j = i + 1
        while j < len(nodes):
            if nodes[j].id in answer_like or nodes[j].id in taken:
                break
            tt = _norm(nodes[j].text)
            if not tt:
                j += 1
                continue
            if RE_QNUM.match(tt) or RE_OPTION.match(tt) or len(tt) <= 60:
                run.append(nodes[j].id)
                j += 1
                continue
            break
        if len(run) >= 4:
            out.append({"node": run[0], "role": "question_group", "conf": "medium",
                        "evidence": "题号连续段 %d 段（无显式标记）" % len(run)})
            i = j
        else:
            i += 1
    return out


def detect(index, doc):
    """Original heading/format/TOC/question-run heuristics, unchanged."""
    body_sz = doc.body_size or 0
    sizes = sorted({n.block.eff_sz for n in index.nodes
                    if n.block and n.block.eff_sz and n.block.eff_sz > body_sz}, reverse=True)
    cands, toc_nodes = [], []
    for n in index.nodes:
        t = _norm(n.text)
        if not t:
            continue
        if RE_TOC_LINE.search(t) or RE_TOC_WORD.match(t):
            continue
        hit = None
        for pat, role in BLOCK_ROLES:
            if pat.match(t):
                hit = (role, "策略关键词: %s" % pat.pattern[:28])
                break
        if hit is None and RE_TYPE_HEAD.match(t):
            hit = ("question_group", "题型/考点标题")
        if hit is None and RE_MATERIAL_HEAD.match(t):
            hit = ("shared_material", "材料/范文标题")
        if hit is None and n.block is not None and n.block.eff_sz and body_sz \
                and n.block.eff_sz > body_sz and len(t) <= 40:
            lvl = sizes.index(n.block.eff_sz) + 1 if n.block.eff_sz in sizes else 2
            hit = ("section", "字号层 %s(正文%s)%s" % (
                "%gpt" % (n.block.eff_sz / 2.0), "%gpt" % (body_sz / 2.0),
                " 加粗" if n.block.bold else ""), lvl)
        if hit:
            role, ev = hit[0], hit[1]
            lvl = hit[2] if len(hit) > 2 else None
            cands.append({"node": n.id, "role": role,
                          "conf": "high" if "关键词" in ev or "题型" in ev or "材料标题" in ev else "medium",
                          "evidence": ev, "level": lvl})
    for n in index.nodes:
        t = _norm(n.text)
        if RE_TOC_ENTRY.search(t):
            toc_nodes.append(n.id)
    clusters, cur = [], []
    for nid in toc_nodes:
        if cur and index.order_of(nid) - index.order_of(cur[-1]) <= 2:
            cur.append(nid)
        else:
            if cur:
                clusters.append(cur)
            cur = [nid]
    if cur:
        clusters.append(cur)
    for cl in clusters:
        if len(cl) >= 3:
            cands.append({"node": cl[0], "role": "toc", "conf": "medium",
                          "evidence": "目录行簇 %d 行（点线+页码）" % len(cl), "toc_end": cl[-1]})
    for n in index.nodes:
        if not RE_TOC_WORD.match(re.sub(r"\s+", " ", (n.text or "")).strip()):
            continue
        cid, best = n.container, None
        while cid and cid != ROOT:
            if index.descendants.get(cid) and len(index.descendants[cid]) >= 3:
                best = cid
                break
            cid = index.container_parent.get(cid)
        if best:
            cands.append({"node": best, "role": "toc", "conf": "medium",
                          "evidence": "目录标签所在容器（%s）含 %d 个条目，结构位于表格/嵌套表格内部"
                                      % (index.containers.get(best), len(index.descendants[best])),
                          "toc_container": best, "toc_end": best})
        else:
            cands.append({"node": n.id, "role": "toc", "conf": "low",
                          "evidence": "疑似目录标题（单节点，需确认是否真目录区）", "toc_end": n.id})
    cands.extend(detect_question_runs(index, cands))
    toc_containers = [c["toc_container"] for c in cands if c.get("toc_container")]
    if toc_containers:
        cands = [c for c in cands if not (c["node"] in index.by_id and
                  any(c["node"] in index.descendants[tc] for tc in toc_containers))]
    def candidate_order(c):
        nid = c["node"]
        o = index.order_of(nid)
        if o is None:
            first = index.first_content(nid)
            o = index.order_of(first) if first else 10 ** 9
        return o
    return sorted(cands, key=candidate_order)


def build_units(index, cands):
    def first_of(nid):
        return nid if nid in index.by_id else index.first_content(nid)
    def last_of(nid):
        return nid if nid in index.by_id else index.last_content(nid)
    units = []
    for i, c in enumerate(cands):
        start = first_of(c["node"])
        if start is None:
            continue
        if "toc_end" in c:
            end = last_of(c["toc_end"]) or start
        else:
            nxt = next((first_of(c2["node"]) for c2 in cands[i + 1:]
                        if first_of(c2["node"]) is not None), None)
            if nxt is None:
                end = index.nodes[-1].id
            else:
                o = index.order_of(nxt)
                end = index.nodes[o - 1].id if o and o > 0 else start
        if index.order_of(end) < index.order_of(start):
            end = start
        units.append({"id": "u%03d" % (i + 1), "role": c["role"], "mode": "spans",
                      "spans": [[start, end]], "_conf": c["conf"],
                      "_evidence": c["evidence"], "level": c.get("level")})
    return units


def merge_adjacent(index, units):
    merged = []
    for u in units:
        if merged:
            prev = merged[-1]
            same_role = prev["role"] == u["role"] and u["role"] in MERGE_ROLES
            contiguous = index.order_of(u["spans"][0][0]) == index.order_of(prev["spans"][0][1]) + 1
            if same_role and contiguous:
                prev["spans"][0][1] = u["spans"][0][1]
                prev["_evidence"] += " + 合并 %s" % u["id"]
                continue
        merged.append(u)
    for i, u in enumerate(merged):
        u["id"] = "u%03d" % (i + 1)
    return merged


def fill_gaps(index, units):
    covered = set()
    for u in units:
        covered |= index.interval(*u["spans"][0])
    missing = [n.id for n in index.nodes if n.id not in covered and n.has_content]
    if not missing:
        return units
    gaps, cur = [], [missing[0]]
    for a, b in zip(missing, missing[1:]):
        if index.order_of(b) == index.order_of(a) + 1:
            cur.append(b)
        else:
            gaps.append(cur)
            cur = [b]
    gaps.append(cur)
    extra = [{"id": "gap%03d" % (i + 1), "role": "body", "mode": "spans",
              "spans": [[g[0], g[-1]]], "_conf": "low",
              "_evidence": "兜底：未被任何规则命中（%d 个节点）" % len(g)}
             for i, g in enumerate(gaps)]
    merged = sorted(units + extra, key=lambda u: index.order_of(u["spans"][0][0]))
    for i, u in enumerate(merged):
        u["id"] = "u%03d" % (i + 1)
    return merged


def assign_relations(units):
    last_section = last_material = None
    for u in units:
        role = u["role"]
        if role == "section":
            last_section = u["id"]
            u["level"] = u.get("level") or 1
        elif role in ("question_group", "answer", "analysis", "knowledge") and last_section:
            u["parent"] = last_section
        if role == "shared_material":
            last_material = u["id"]
        elif role == "question_group" and last_material:
            u["bind_to"] = last_material
            u["_evidence"] += "；绑定材料 %s（相邻）" % last_material
    return units


def predict(doc):
    """Return the exact old candidate pipeline in gold_compare-compatible form."""
    index = NodeIndex(doc)
    units = build_units(index, detect(index, doc))
    units = merge_adjacent(index, units)
    units = fill_gaps(index, units)
    units = assign_relations(units)
    return index, [{"id": u["id"], "role": u["role"], **(
        {k: u[k] for k in ("level", "parent", "bind_to") if u.get(k) is not None}),
        "spans": u["spans"], "note": "[%s] %s" % (u["_conf"], u["_evidence"])} for u in units]


def _unit_exact_role(gold, pred):
    return gold.role == pred.role


def role_metrics(cmp):
    roles = ("section", "toc", "question_group", "shared_material", "answer", "analysis", "unknown")
    result = {}
    for role in roles:
        golds = [u for u in cmp.gold_units if u.role == role]
        preds = [u for u in cmp.pred_units if u.role == role]
        # A deterministic one-to-one exact match (in document order).
        used_g, used_p, correct = set(), set(), 0
        for g in golds:
            for p in preds:
                if p.id not in used_p and g.id not in used_g and g.nodes == p.nodes:
                    correct += 1
                    used_g.add(g.id)
                    used_p.add(p.id)
                    break
        boundary = sum(1 for g in golds if g.nodes and any(
            g.nodes & p.nodes for p in preds) and g.id not in used_g)
        result[role] = {"gold": len(golds), "predicted": len(preds), "correct": correct,
                        "missed": len(golds) - correct, "erroneous": len(preds) - correct,
                        "boundary_errors": boundary, "binding_errors": 0}
    gold_by_id = {u.id: u for u in cmp.gold_units}
    for issue in cmp.issues:
        if issue.code != "UNBOUND" or "<->" not in issue.subject:
            continue
        left, right = issue.subject.split("<->", 1)
        for uid in (left, right):
            unit = gold_by_id.get(uid)
            if unit and unit.role in result:
                result[unit.role]["binding_errors"] += 1
    return result


def _read_sample(root, spec):
    path = os.path.join(root, spec["source"])
    if spec.get("member"):
        with zipfile.ZipFile(path) as zf:
            data = zf.read(spec["member"])
        name = os.path.basename(spec["member"])
    else:
        with open(path, "rb") as fh:
            data = fh.read()
        name = os.path.basename(path)
    sha = hashlib.sha256(data).hexdigest()
    if sha.lower() != spec["sha256"].lower():
        raise ValueError("%s source SHA256 mismatch: expected %s got %s" %
                         (spec["sample_id"], spec["sha256"], sha))
    return name, data


def run(manifest_path, corpus_root, out_dir):
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    os.makedirs(out_dir, exist_ok=True)
    summaries = []
    all_issue_counts = Counter()
    for spec in manifest["samples"]:
        sample_id = spec["sample_id"]
        name, data = _read_sample(corpus_root, spec)
        gold_path = os.path.abspath(os.path.join(os.path.dirname(manifest_path), spec["gold"]))
        with open(gold_path, encoding="utf-8") as fh:
            gold = json.load(fh)
        doc = read_struct_doc_bytes(data, name=name)
        index, predicted = predict(doc)
        cmp = compare(doc, gold, predicted)
        issues = Counter(i.code for i in cmp.issues)
        all_issue_counts.update(issues)
        role_stats = role_metrics(cmp)
        pred_doc = {"doc": name, "baseline": "gold-draft-heuristics-v1", "units": predicted}
        prefix = os.path.join(out_dir, sample_id)
        with open(prefix + "_pred.json", "w", encoding="utf-8") as fh:
            json.dump(pred_doc, fh, ensure_ascii=False, indent=2)
        with open(prefix + "_gold_compare.md", "w", encoding="utf-8") as fh:
            fh.write(render_report(doc, cmp, gold_path, prefix + "_pred.json"))
        with open(prefix + "_gold_compare.json", "w", encoding="utf-8") as fh:
            json.dump(cmp.as_dict(), fh, ensure_ascii=False, indent=2)
        summaries.append({"sample_id": sample_id, "name": name, "source_sha256": spec["sha256"],
                          "node_count": len(index.nodes), "gold_unit_count": cmp.summary["gold_units"],
                          "prediction_count": len(predicted), "binding_errors": issues.get("UNBOUND", 0),
                          "gold_compare_verdict": cmp.verdict, "errors": cmp.summary["errors"],
                          "warnings": cmp.summary["warns"], "infos": cmp.summary["infos"],
                          "roles": role_stats,
                          "issue_counts": dict(sorted(issues.items())),
                          "top_failure_codes": [c for c, _ in issues.most_common(3)]})
    gold_files = {}
    for spec in manifest["samples"]:
        gold_path = os.path.abspath(os.path.join(os.path.dirname(manifest_path), spec["gold"]))
        with open(gold_path, "rb") as fh:
            gold_sha = hashlib.sha256(fh.read()).hexdigest()
        gold_files[spec["sample_id"]] = {"path": spec["gold"], "sha256": gold_sha}
    return {"baseline": "gold-draft-heuristics-v1", "rule_source": "_research/gen_gold_draft.py",
            "gold_files": gold_files,
            "samples": summaries, "issue_counts": dict(sorted(all_issue_counts.items()))}


def render_summary(summary):
    lines = ["# Splitter V2 Stage2 自动结构识别基线", "",
             "本报告固定使用 Gold 初稿生成器 `_research/gen_gold_draft.py` 中的既有候选规则；"
             "没有调整阈值或识别行为。`gold_compare.py` 是正式对照器。",
             "正确=Gold 单元与预测单元节点集合完全相同且角色相同；漏识别=未精确匹配的 Gold 单元；"
             "错误识别=未精确匹配的预测单元；边界错误=有同角色预测与 Gold 节点相交但范围不一致。",
             "漏识别/错误识别统计单位为单元，可与边界错误重叠。程序额外输出 body/knowledge 等角色，"
             "此表只列本轮要求的七类角色。", "",
             "## 样本结果", "",
             "| 样本 | GoldCompare | Gold / 预测单元 | 错误/警告/提示 | 主要失败原因 |",
             "|---|---|---:|---:|---|"]
    for s in summary["samples"]:
        lines.append("| %s | %s | %d / %d | %d / %d / %d | %s |" %
                     (s["sample_id"], s["gold_compare_verdict"],
                      s["gold_unit_count"],
                      s["prediction_count"], s["errors"], s["warnings"], s["infos"],
                      ", ".join("%s×%d" % (c, s["issue_counts"][c]) for c in s["top_failure_codes"]) or "无"))
    lines += ["", "## 按角色统计", ""]
    for s in summary["samples"]:
        lines += ["### %s" % s["sample_id"], "",
                  "| 角色 | Gold | 预测 | 正确 | 漏识别 | 错误识别 | 边界错误 | 绑定错误端点 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for role, values in s["roles"].items():
            lines.append("| %s | %d | %d | %d | %d | %d | %d | %d |" %
                         (role, values["gold"], values["predicted"], values["correct"],
                          values["missed"], values["erroneous"], values["boundary_errors"],
                          values["binding_errors"]))
        lines.append("")
    lines += ["## 总体失败类型", ""]
    for code, count in summary["issue_counts"].items():
        lines.append("- `%s`: %d" % (code, count))
    binding_total = sum(s["binding_errors"] for s in summary["samples"])
    lines += ["", "绑定错误（UNBOUND）：%d 对。角色表中的绑定错误端点分别计入题组和材料。" % binding_total,
              "", "## 失败解读与下一轮优先项", "",
              "最大共性问题是边界候选过稀并由‘当前候选延伸到下一个候选’形成大段合并：正式对照累计"
              " `MERGE` 95 次；`question_group` 精确范围命中仅 5 个（四份合计 Gold 191 个）。",
              "其次是角色含义错位：旧规则把 `题型N` 直接标为 `question_group`，而正式口径把题型标题视为 `section`。"
              "S12 产生 1 次 `TOC_AS_BODY`；S04 的 20 个共享材料均未被规则产出，产生 20 对 `UNBOUND`。",
              "建议 Stage2-1 只优先解决‘题目边界与栏目标题分离’：题型标题先按 section 识别，题组起止以明确题号/"
              "题组连续结构确定，并用 S01/S11/S12/S04 做回归。暂不同时扩展答案语义或共享材料推断。", "",
              "## 可重复性", "", "同一 runner、相同 source SHA256、相同 Gold 文件与 StructDoc 代码会生成相同预测单元和对照统计；"
              "报告不含运行耗时等非确定性字段。", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Reproduce the frozen Stage2 heuristic baseline")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--corpus-root", required=True)
    ap.add_argument("--out", required=True, help="Reports/predictions directory outside repo/corpus")
    args = ap.parse_args()
    result = run(os.path.abspath(args.manifest), os.path.abspath(args.corpus_root), os.path.abspath(args.out))
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write(render_summary(result))
    print(render_summary(result))


if __name__ == "__main__":
    main()
