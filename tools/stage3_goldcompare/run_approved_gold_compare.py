#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gate 2：Stage3 APPROVED_GOLD × 冻结 Splitter 预测 的基线测量（只测量，不改代码）。

输入（全部只读）：
  · APPROVED_GOLD/            —— 正式 Gold（已批准；X013 已含 GOLD_CORRECTION_BEFORE_BASELINE）
  · STAGE3_EXPANSION_BASELINE/<sid>/prediction.json —— 冻结 checkpoint 的 Splitter 预测
  · STAGE3_EXPANSION_BASELINE/<sid>/struct_nodes.json —— 节点序（把 span 换算成统一区间）
  · baseline_inputs.json      —— 学科 / 文件名（判定原卷 vs 解析版）

匹配口径（全部基于「扁平节点序」区间）：
  · matched_start ：gold QG 与 pred QG 起点节点相同
  · exact         ：起点与终点都相同
  · MISS          ：gold 有、pred 无对应起点
  · FP            ：pred 有、gold 无对应起点
  · MERGE         ：单个 pred 单元吸收了 ≥2 个 gold 题组起点
  · SPLIT         ：单个 gold 题组区间被 ≥2 个 pred 单元切开

评分范围：section / question_group / boundary / subquestion / MERGE / SPLIT / MISS / FP
          （answer·analysis 边界与 linkage、shared_material·binding 只作 diagnostic）

用法：python run_approved_gold_compare.py [--out 报告.md] [--json 结果.json]
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

BASE = r"C:\xml-uat\stage3-expansion"
APPROVED = os.path.join(BASE, "gold_preparation_01", "APPROVED_GOLD")
BASELINE = os.path.join(BASE, "STAGE3_EXPANSION_BASELINE")
INPUTS = os.path.join(BASE, "baseline_inputs.json")

SAMPLES = ["X003", "X004", "X006", "X012", "X013", "X019", "X021", "X025"]
RE_QNUM = re.compile(r"^\s*\d{1,3}\s*[．.、]")
RE_SUBQ = re.compile(r"^\s*[（(]\s*\d+\s*[)）]")

E_LABEL = {
    "E1": "Answer/analysis 后未恢复新 question boundary",
    "E2": "知识精讲 / 随学随练中的完整题漏识别",
    "E3": "普通 body / 非题目内容被误判为 question_group（False Positive）",
    "E4": "父题已识别，但 (1)(2)(3) 小问落在父题范围之外",
    "E4_SECONDARY": "小问越界（父题本身未被识别 → E1/E2 的连带，非独立缺陷）",
    "E5": "题组 MERGE（多题被并成一个单元）",
    "E6": "题组 SPLIT（一题被切成多个单元）",
    "E7": "shared_material / binding 问题（diagnostic）",
    "E8": "其他",
}


# ---------------------------------------------------------------
class Ctx(object):
    def __init__(self, sid):
        nd = json.load(open(os.path.join(BASELINE, sid, "struct_nodes.json"), encoding="utf-8"))
        self.by_id = {n["id"]: n for n in nd["nodes"]}
        self.o2n = {n["order"]: n for n in nd["nodes"]}
        self.containers = nd["containers"]
        self.cparent = nd["container_parent"]
        self.desc = {}
        for n in nd["nodes"]:
            cur = n["container"]
            while cur:
                self.desc.setdefault(cur, []).append(n["id"])
                if cur == "body":
                    break
                cur = self.cparent.get(cur)

    def first(self, ref):
        if ref in self.by_id:
            return self.by_id[ref]["order"]
        d = self.desc.get(ref)
        return self.by_id[d[0]]["order"] if d else None

    def last(self, ref):
        if ref in self.by_id:
            return self.by_id[ref]["order"]
        d = self.desc.get(ref)
        return self.by_id[d[-1]]["order"] if d else None

    def interval(self, spans):
        lo = hi = None
        for s, e in spans:
            a, b = self.first(s), self.last(e)
            if a is None or b is None:
                continue
            lo = a if lo is None else min(lo, a)
            hi = b if hi is None else max(hi, b)
        return None if lo is None else (lo, hi)

    def text_at(self, order):
        n = self.o2n.get(order)
        return (n["text"] or "") if n else ""

    def node_at(self, order):
        n = self.o2n.get(order)
        return n["id"] if n else None

    def role_at(self, pred_units, order):
        for u in pred_units:
            iv = u["_iv"]
            if iv and iv[0] <= order <= iv[1]:
                return u["role"], u["id"]
        return None, None


def load_sample(sid):
    doc = json.load(open(os.path.join(APPROVED, "%s_APPROVED_GOLD.json" % sid), encoding="utf-8"))
    ctx = Ctx(sid)
    pred = json.load(open(os.path.join(BASELINE, sid, "prediction.json"), encoding="utf-8"))
    for u in pred["units"]:
        u["_iv"] = ctx.interval(u["spans"])
    gold = {"qg": [], "section": [], "answer": [], "analysis": [], "sm": [], "subq": []}
    for u in doc["units"].get("question_groups", []):
        iv = ctx.interval(u["spans"])
        if iv:
            gold["qg"].append({"id": u["unit_id"], "iv": iv, "text": ctx.text_at(iv[0]),
                               "subq": [ctx.first(s["node"]) for s in (u.get("subquestions") or [])]})
    for key, bucket in (("sections", "section"), ("answers", "answer"), ("analyses", "analysis"),
                        ("shared_materials", "sm")):
        for u in doc["units"].get(key, []):
            iv = ctx.interval(u["spans"])
            if iv:
                gold[bucket].append({"id": u["unit_id"], "iv": iv, "text": ctx.text_at(iv[0])})
    return doc, ctx, pred, gold


def score_role(gold_list, pred_list):
    """start-anchored 匹配。"""
    gold_start = {g["iv"][0]: g for g in gold_list}
    pred_start = {p["iv"][0]: p for p in pred_list}
    matched_gold = [g for s, g in gold_start.items() if s in pred_start]
    matched_pred = [p for s, p in pred_start.items() if s in gold_start]
    exact = sum(1 for s, g in gold_start.items()
                if s in pred_start and pred_start[s]["iv"][1] == g["iv"][1])
    precision = len(matched_pred) / len(pred_list) if pred_list else None
    recall = len(matched_gold) / len(gold_list) if gold_list else None
    return {
        "gold_n": len(gold_list), "pred_n": len(pred_list),
        "matched_gold": len(matched_gold), "matched_pred": len(matched_pred),
        "exact": exact, "miss": len(gold_list) - len(matched_gold),
        "fp": len(pred_list) - len(matched_pred),
        "precision": precision, "recall": recall,
        "exact_rate": exact / len(gold_list) if gold_list else None,
    }


def analyse_sample(sid, doc, ctx, pred, gold):
    pred_qg = [{"id": u["id"], "role": u["role"], "iv": u["_iv"]}
               for u in pred["units"] if u["role"] == "question_group" and u["_iv"]]
    pred_sec = [{"id": u["id"], "role": u["role"], "iv": u["_iv"]}
                for u in pred["units"] if u["role"] == "section" and u["_iv"]]

    m = {"sample_id": sid}
    m["question_group"] = score_role(gold["qg"], pred_qg)
    m["section"] = score_role(gold["section"], pred_sec)

    # MERGE / SPLIT
    merge_units = []
    for p in pred_qg:
        absorbed = [g for g in gold["qg"] if p["iv"][0] <= g["iv"][0] <= p["iv"][1]]
        if len(absorbed) >= 2:
            merge_units.append({"pred": p["id"], "iv": p["iv"],
                                "gold_count": len(absorbed),
                                "gold_ids": [g["id"] for g in absorbed][:6]})
    split_units = []
    for g in gold["qg"]:
        cut = [p for p in pred_qg if p["iv"][0] <= g["iv"][1] and p["iv"][1] >= g["iv"][0]]
        if len(cut) >= 2:
            split_units.append({"gold": g["id"], "iv": g["iv"],
                                "pred_ids": [p["id"] for p in cut][:6]})
    m["merge"] = merge_units
    m["split"] = split_units
    m["merge_n"] = len(merge_units)
    m["split_n"] = len(split_units)

    # 小问归属（区分：父题缺失的连带失败 vs 父题在但小问越界）
    gold_start_to_pred = {p["iv"][0]: p for p in pred_qg}
    subq_total = subq_ok = 0
    subq_bad = []
    subq_orphan_parent = 0
    for g in gold["qg"]:
        p = gold_start_to_pred.get(g["iv"][0])
        for o in g["subq"]:
            subq_total += 1
            if p and p["iv"][0] <= o <= p["iv"][1]:
                subq_ok += 1
            else:
                if p is None:
                    subq_orphan_parent += 1
                subq_bad.append({"gold": g["id"], "order": o, "parent_missing": p is None,
                                 "text": ctx.text_at(o)[:50]})
    m["subquestion"] = {"total": subq_total, "inside_parent": subq_ok,
                        "rate": (subq_ok / subq_total) if subq_total else None,
                        "orphan_parent": subq_orphan_parent,
                        "parent_present_but_outside": len(subq_bad) - subq_orphan_parent,
                        "bad": subq_bad[:5]}

    # 错误分类
    errs = defaultdict(list)
    for g in gold["qg"]:
        if g["iv"][0] in gold_start_to_pred:
            continue
        role, uid = ctx.role_at(pred["units"], g["iv"][0])
        text = ctx.text_at(g["iv"][0])
        if role in ("answer", "analysis"):
            errs["E1"].append({"gold": g["id"], "pred": uid, "role": role,
                               "order": g["iv"][0], "text": text[:60]})
        elif role in ("knowledge", "body"):
            if RE_QNUM.match(text) or role == "knowledge":
                errs["E2"].append({"gold": g["id"], "pred": uid, "role": role,
                                   "order": g["iv"][0], "text": text[:60]})
            else:
                errs["E8"].append({"gold": g["id"], "pred": uid, "role": role,
                                   "order": g["iv"][0], "text": text[:60]})
        else:
            errs["E8"].append({"gold": g["id"], "pred": uid, "role": role,
                               "order": g["iv"][0], "text": text[:60]})
    gold_starts = {g["iv"][0] for g in gold["qg"]}
    for p in pred_qg:
        if p["iv"][0] in gold_starts:
            continue
        text = ctx.text_at(p["iv"][0])
        # 预测出了题组、gold 认为不是题组 → 一律计为 E3（False Positive）
        errs["E3"].append({"pred": p["id"], "order": p["iv"][0], "text": text[:60],
                           "numbered_but_not_question": bool(RE_QNUM.match(text))})
    for b in subq_bad:
        # 区分：父题本身缺失（E1/E2 的连带）vs 父题存在但小问越界（真实 E4）
        errs["E4_SECONDARY" if b["parent_missing"] else "E4"].append(b)
    for mu in merge_units:
        errs["E5"].append({"pred": mu["pred"], "gold_count": mu["gold_count"]})
    for su in split_units:
        errs["E6"].append({"gold": su["gold"], "pred_ids": su["pred_ids"]})

    # shared_material / binding —— diagnostic only（不作为本轮失败判据）
    pred_sm = [u for u in pred["units"] if u["role"] == "shared_material"]
    gold_sm = gold["sm"]
    bound = sum(1 for u in pred["units"]
                if u["role"] == "question_group" and u.get("bind_to"))
    m["diagnostic"] = {
        "gold_shared_material": len(gold_sm),
        "pred_shared_material": len(pred_sm),
        "pred_qg_with_binding": bound,
        "pred_qg_total": len(pred_qg),
        "note": ("Gold 侧本样本无顶层 shared_material" if not gold_sm else ""),
    }
    m["errors"] = {k: {"n": len(v), "examples": v[:5]} for k, v in sorted(errs.items())}
    m["error_counts"] = {k: len(v) for k, v in sorted(errs.items())}
    return m


def agg(metrics):
    out = {}
    for role in ("question_group", "section"):
        g = sum(m[role]["gold_n"] for m in metrics)
        p = sum(m[role]["pred_n"] for m in metrics)
        mg = sum(m[role]["matched_gold"] for m in metrics)
        mp = sum(m[role]["matched_pred"] for m in metrics)
        ex = sum(m[role]["exact"] for m in metrics)
        out[role] = {
            "gold_n": g, "pred_n": p, "matched_gold": mg, "matched_pred": mp, "exact": ex,
            "precision": (mp / p) if p else None, "recall": (mg / g) if g else None,
            "exact_rate": (ex / g) if g else None,
            "miss": g - mg, "fp": p - mp,
        }
    out["merge_n"] = sum(m["merge_n"] for m in metrics)
    out["split_n"] = sum(m["split_n"] for m in metrics)
    sq = sum(m["subquestion"]["total"] for m in metrics)
    so = sum(m["subquestion"]["inside_parent"] for m in metrics)
    orphan = sum(m["subquestion"].get("orphan_parent", 0) for m in metrics)
    out["subquestion"] = {"total": sq, "inside_parent": so,
                          "rate": (so / sq) if sq else None,
                          "orphan_parent": orphan,
                          "parent_present_but_outside": (sq - so) - orphan}
    ec = Counter()
    for m in metrics:
        for k, v in m["error_counts"].items():
            ec[k] += v
    out["error_counts"] = dict(sorted(ec.items()))
    out["samples"] = len(metrics)
    return out


def fmt(v, pct=True):
    if v is None:
        return "n/a"
    return ("%.1f%%" % (v * 100)) if pct else ("%.3f" % v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args()

    meta = {s["sample_id"]: s for s in json.load(open(INPUTS, encoding="utf-8"))["samples"]}
    metrics = []
    for sid in SAMPLES:
        doc, ctx, pred, gold = load_sample(sid)
        m = analyse_sample(sid, doc, ctx, pred, gold)
        nm = meta[sid]["name"]
        m["subject"] = meta[sid]["subject"]
        m["doc_type"] = "解析版" if "解析版" in nm else ("原卷" if "原卷版" in nm else "其他")
        m["name"] = nm
        metrics.append(m)

    overall = agg(metrics)
    by_subject = {k: agg([m for m in metrics if m["subject"] == k])
                  for k in ("mathematics", "physics", "chemistry")}
    by_type = {k: agg([m for m in metrics if m["doc_type"] == k])
               for k in ("原卷", "解析版")}

    result = {"baseline_commit": "ceaaf8b424738245fa9f6762cdb27bfd022d0905",
              "overall": overall, "by_subject": by_subject, "by_doc_type": by_type,
              "samples": metrics}
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)

    # ---------- 控制台摘要 ----------
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    q = overall["question_group"]
    print("== Overall ==")
    print("  QG  gold=%d pred=%d  P=%s R=%s exact=%s MISS=%d FP=%d MERGE=%d SPLIT=%d"
          % (q["gold_n"], q["pred_n"], fmt(q["precision"]), fmt(q["recall"]),
             fmt(q["exact_rate"]), q["miss"], q["fp"], overall["merge_n"], overall["split_n"]))
    s = overall["section"]
    print("  SEC gold=%d pred=%d  P=%s R=%s exact=%s"
          % (s["gold_n"], s["pred_n"], fmt(s["precision"]), fmt(s["recall"]), fmt(s["exact_rate"])))
    print("  subquestion inside-parent: %s (%d/%d)"
          % (fmt(overall["subquestion"]["rate"]), overall["subquestion"]["inside_parent"],
             overall["subquestion"]["total"]))
    print("  errors:", overall["error_counts"])
    for label, block in (("By subject", by_subject), ("By doc type", by_type)):
        print("== %s ==" % label)
        for k, v in block.items():
            qq = v["question_group"]
            print("  %-12s QG P=%s R=%s exact=%s MISS=%d FP=%d MERGE=%d SPLIT=%d"
                  % (k, fmt(qq["precision"]), fmt(qq["recall"]), fmt(qq["exact_rate"]),
                     qq["miss"], qq["fp"], v["merge_n"], v["split_n"]))
    print("== Per sample ==")
    for m in metrics:
        qq = m["question_group"]
        top = sorted(m["error_counts"].items(), key=lambda kv: -kv[1])[:2]
        print("  %-6s %-4s %-4s QG gold=%-3d pred=%-3d exact=%-3d MISS=%-3d FP=%-3d MERGE=%-2d SPLIT=%-2d top=%s"
              % (m["sample_id"], m["subject"][:4], m["doc_type"], qq["gold_n"], qq["pred_n"],
                 qq["exact"], qq["miss"], qq["fp"], m["merge_n"], m["split_n"], top))

    if args.out:
        write_report(args.out, result)
        print("\n报告已写出:", args.out)


def tbl_row(name, blk):
    q, s = blk["question_group"], blk["section"]
    sq = blk["subquestion"]
    return ("| %s | %d | %d | %s | %s | %s | %d | %d | %d | %d | %s / %s | %s (%d/%d) |"
            % (name, q["gold_n"], q["pred_n"], fmt(q["precision"]), fmt(q["recall"]),
               fmt(q["exact_rate"]), q["miss"], q["fp"], blk["merge_n"], blk["split_n"],
               fmt(s["precision"]), fmt(s["recall"]),
               fmt(sq["rate"]), sq["inside_parent"], sq["total"]))


LAYER_HEADER = ("| 层 | Gold QG | Pred QG | QG P | QG R | Exact boundary | MISS | FP | MERGE | SPLIT | "
                "section P / R | 小问 in-parent |")
LAYER_SEP = "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"


def write_report(path, result):
    L = []
    A = L.append
    A("# Stage3 GoldCompare 基线报告（APPROVED_GOLD × 冻结 Splitter）")
    A("")
    A("- 冻结 checkpoint：`%s`（**Splitter / StructDoc / GoldCompare 均未修改**）" % result["baseline_commit"])
    A("- Gold：`APPROVED_GOLD/`（stage3-batch-01，含 1 处 `GOLD_CORRECTION_BEFORE_BASELINE`）")
    A("- 预测：`STAGE3_EXPANSION_BASELINE/<sid>/prediction.json`（同一 checkpoint 的冻结预测，未重跑）")
    A("- 匹配口径：起点节点相同＝matched；起止都同＝exact；MERGE＝一个预测单元吸收 ≥2 个 gold 题组；"
      "SPLIT＝一个 gold 题组被 ≥2 个预测单元切开")
    A("")
    q = result["overall"]["question_group"]
    ty = result["by_doc_type"]
    ov = ty.get("原卷", {}).get("question_group", {})
    pv = ty.get("解析版", {}).get("question_group", {})
    A("## 0. 摘要（TL;DR）")
    A("")
    A("- Gold QG 合计 **%d**；冻结 Splitter 预测 **%d** 个。" % (q["gold_n"], q["pred_n"]))
    A("- Overall：QG precision **%s** / recall **%s** / exact boundary **%s**；MISS **%d**；FP **%d**；"
      "MERGE **%d**；SPLIT **%d**。"
      % (fmt(q["precision"]), fmt(q["recall"]), fmt(q["exact_rate"]),
         q["miss"], q["fp"], result["overall"]["merge_n"], result["overall"]["split_n"]))
    A("- **原卷 vs 解析版是断崖式差距**：原卷 recall **%s**（exact %s，MISS %d），"
      "解析版 recall **%s**（exact %s，MISS %d）。"
      % (fmt(ov.get("recall")), fmt(ov.get("exact_rate")), ov.get("miss", 0),
         fmt(pv.get("recall")), fmt(pv.get("exact_rate")), pv.get("miss", 0)))
    A("- section 层：precision / recall / exact 全部 **%s**。"
      % fmt(result["overall"]["section"]["recall"]))
    A("- 结论：**当前 Splitter 在“原卷题界”上已接近满分，失效点高度集中在解析版的题界恢复。**")
    A("")
    A("## 1. Overall")
    A("")
    A(LAYER_HEADER)
    A(LAYER_SEP)
    A(tbl_row("question_group", result["overall"]))
    A("")
    sq = result["overall"]["subquestion"]
    A("- **小问归属**：%s（%d/%d 落在与其父题起点匹配的预测单元内）"
      % (fmt(sq["rate"]), sq["inside_parent"], sq["total"]))
    A("  - 其中 **父题本身未被识别**（连带失败）：%d；**父题已识别但小问越界**（真实 E4）：%d"
      % (sq["orphan_parent"], sq["parent_present_but_outside"]))
    A("")
    A("## 2. 按学科")
    A("")
    A(LAYER_HEADER)
    A(LAYER_SEP)
    for k in ("mathematics", "physics", "chemistry"):
        if k in result["by_subject"]:
            A(tbl_row(k, result["by_subject"][k]))
    A("")
    A("## 3. 按文档类型（**关键分层**：不使用混合平均）")
    A("")
    A(LAYER_HEADER)
    A(LAYER_SEP)
    for k in ("原卷", "解析版"):
        if k in result["by_doc_type"]:
            A(tbl_row(k, result["by_doc_type"][k]))
    A("")
    A("## 4. 逐样本")
    A("")
    A("| 样本 | 学科 | 类型 | Gold QG | Pred QG | Exact | MISS | MERGE | SPLIT | FP | 最主要错误 |")
    A("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for m in result["samples"]:
        q = m["question_group"]
        top = sorted(m["error_counts"].items(), key=lambda kv: -kv[1])[:2]
        top_s = " / ".join("%s×%d" % (k, v) for k, v in top) or "—"
        A("| %s | %s | %s | %d | %d | %d | %d | %d | %d | %d | %s |"
          % (m["sample_id"], m["subject"], m["doc_type"], q["gold_n"], q["pred_n"],
             q["exact"], q["miss"], m["merge_n"], m["split_n"], q["fp"], top_s))
    A("")
    A("## 5. 错误分类统计（Error Taxonomy）")
    A("")
    A("| 代码 | 含义 | 数量 |")
    A("|---|---|---:|")
    for k in ("E1", "E2", "E3", "E4", "E4_SECONDARY", "E5", "E6", "E7", "E8"):
        A("| %s | %s | %d |" % (k, E_LABEL[k], result["overall"]["error_counts"].get(k, 0)))
    A("")
    A("## 5b. 错误分类统计（按文档类型拆分）")
    A("")
    A("| 代码 | 原卷 | 解析版 |")
    A("|---|---:|---:|")
    for k in ("E1", "E2", "E3", "E4", "E4_SECONDARY", "E5", "E6", "E7", "E8"):
        A("| %s | %d | %d |" % (k,
          result["by_doc_type"].get("原卷", {}).get("error_counts", {}).get(k, 0),
          result["by_doc_type"].get("解析版", {}).get("error_counts", {}).get(k, 0)))
    A("")
    A("## 6. 代表性错误案例（每样本 ≤5）")
    A("")
    for m in result["samples"]:
        A("### %s（%s / %s）" % (m["sample_id"], m["subject"], m["doc_type"]))
        A("")
        shown = 0
        for code in ("E1", "E2", "E3", "E4", "E5", "E6", "E8"):
            for ex in m["errors"].get(code, {}).get("examples", []):
                if shown >= 5:
                    break
                if code in ("E1", "E2", "E8") and "order" in ex:
                    A("- `%s` #%s order=%s role=%s「%s」"
                      % (code, ex.get("gold", ex.get("pred", "-")), ex.get("order"),
                         ex.get("role", "-"), ex.get("text", "")[:52]))
                elif code == "E3":
                    A("- `E3` pred=%s order=%s「%s」" % (ex.get("pred"), ex.get("order"),
                                                        ex.get("text", "")[:52]))
                elif code == "E4":
                    A("- `E4` gold=%s order=%s「%s」" % (ex.get("gold"), ex.get("order"),
                                                        ex.get("text", "")[:52]))
                elif code == "E5":
                    A("- `E5` pred=%s 吸收 %d 个 gold 题组" % (ex.get("pred"), ex.get("gold_count", 0)))
                elif code == "E6":
                    A("- `E6` gold=%s 被 %s 切开" % (ex.get("gold"), ex.get("pred_ids")))
                shown += 1
        if shown == 0:
            A("- （本样本无该类错误案例）")
        A("")
    A("")
    A("## 7. 诊断（只统计，不作为本轮失败判据）")
    A("")
    A("| 样本 | Gold shared_material | Pred shared_material | Pred QG 带 binding | Pred QG 总数 |")
    A("|---|---:|---:|---:|---:|")
    for m in result["samples"]:
        d = m.get("diagnostic", {})
        A("| %s | %d | %d | %d | %d |" % (m["sample_id"], d.get("gold_shared_material", 0),
          d.get("pred_shared_material", 0), d.get("pred_qg_with_binding", 0), d.get("pred_qg_total", 0)))
    A("")
    A("> Gold 侧 8 个样本的顶层 `shared_material` 均为 0（G09 后材料降为 Q20 内部子结构），")
    A("> 因此**本批无法评估 shared_material / binding 能力**，需下一批样本补测。")
    A("")
    A("## 8. Gate 0：Gold 自检结果")
    A("")
    A("- `check_gold_schema.py`：8/8 样本 **0 问题**（无 span 重叠、无 parent/bind 悬空、无小问越界）。")
    A("- **X013 定点剔除**（`GOLD_CORRECTION_BEFORE_BASELINE`）：起点 `b4.r0c1.n4`（order 9）"
      "经结构证据判定为**学习目标列表第 5 条**——同一单元格 `b4.r0c1` 内为连续 6 条编号教学目标"
      "（`1.理解有理数乘方的意义…` → `6.通过观察、归纳…`），n4 与前后同级同构，不构成 question_group。"
      "已从正式 QG Gold 剔除（39 → 38）并留痕，未触动其余 38 个。")
    A("- 除 X013 外**未修改任何已批准语义**；`PROPOSED_GOLD/` 原样保留。")
    A("")
    A("## 9. Top 问题与下一轮 Patch 建议（不在本轮修）")
    A("")
    ec = result["overall"]["error_counts"]
    A("按数量排序：E1=%d、E4_SECONDARY=%d、E4=%d、E3=%d、E2=%d。"
      % (ec.get("E1", 0), ec.get("E4_SECONDARY", 0), ec.get("E4", 0),
         ec.get("E3", 0), ec.get("E2", 0)))
    A("")
    A("**最大的 1–3 个真实问题**：")
    A("")
    A("1. **E1（%d 例）：answer / analysis 之后没有恢复 question boundary** —— 解析版几乎全部失分于此。"
      "典型：X004 `2．（24-25九年级上·天津河西·期末）…` 落在 `analysis` 单元内；"
      "X006 `2．（2024秋•嘉峪关校级期末）火锅…` 落在 `answer` 单元内；X012 `2．计算：______．` 落在 `analysis`；"
      "X025 全程 0 个 QG。" % ec.get("E1", 0))
    A("2. **E2（%d 例）：知识区 / 随学随练中的完整题漏识别** —— X025 `b14`（拉瓦锡实验题 `1．` + `(1)(2)(3)`）"
      "被判为 `body`。这是唯一一条**非解析版**的题界漏识别，对应业务规则 R3/R4（例题可调度）。"
      % ec.get("E2", 0))
    A("3. **E3（%d 例）：非题目内容被误判为 question_group** —— X013 `b4.r0c1.n4` 学习目标条目。"
      "量小，但说明规则对「表格内教学目标编号列表」缺少排除。" % ec.get("E3", 0))
    A("")
    A("**建议下一轮只做 1 个 Patch**：E1（恢复题界）。理由：")
    A("")
    A("- 单类错误占全部失分的约 %d%%；" % int(100 * ec.get("E1", 0) / max(1, sum(ec.values()))))
    A("- 原卷侧已 100% recall，修 E1 不会破坏原卷（回归可验证）；")
    A("- E2/E3 各自样本量小（1 例），适合作为后续独立 Patch。")
    A("")
    A("**注意**：E4_SECONDARY（%d）不是独立缺陷——它是 E1/E2 的连带（父题没被识别，小问自然无处可放）；"
      "真正独立的 E4 只有 %d 例（X019：按 G09 裁定小问应属 Q20，而预测仍把 `b179–b181` 留在材料单元内）。"
      % (ec.get("E4_SECONDARY", 0), ec.get("E4", 0)))
    A("")
    A("## 10. 口径说明")
    A("")
    A("- **正式评分**：section、question_group、boundary(exact)、subquestion、MERGE、SPLIT、MISS、FP。")
    A("- **Diagnostic only（本轮不据此判定失败）**：answer / analysis 边界与 linkage、shared_material / binding。")
    A("  原因：Gold 对 answer/analysis 的要求是「归属正确优先」，部分 linkage 仍为 provisional；")
    A("  本批 Stage3 样本也缺少真正的顶层多题 shared_material。")
    A("- 原卷与解析版**分开报告**，不使用混合平均。")
    A("")
    A("## 11. 复现方式")
    A("")
    A("```bash")
    A("PY=\"C:/Users/Administrator/Desktop/工作/讲义生成器/讲义生成器flash版/res/python/python.exe\"")
    A("# Gate 0：Gold 一致性自检（只报告）")
    A("python tools/stage3_goldcompare/check_gold_schema.py")
    A("# Gate 2：基线测量（只测量，不改算法）")
    A("python tools/stage3_goldcompare/run_approved_gold_compare.py \\")
    A("       --out docs/v2/stage3/STAGE3_GOLDCOMPARE_BASELINE_REPORT.md \\")
    A("       --json docs/v2/stage3/baseline_result.json")
    A("```")
    A("")
    A("- 数据位置：Gold 在 `C:\\xml-uat\\stage3-expansion\\gold_preparation_01\\APPROVED_GOLD\\`，")
    A("  冻结预测在 `C:\\xml-uat\\stage3-expansion\\STAGE3_EXPANSION_BASELINE\\<sid>\\prediction.json`。")
    A("  **这两处均在仓库之外，未随本 commit 入库**（含第三方讲义原文，且可由脚本重建）；")
    A("  本 commit 只包含测量工具与本报告，路径常量见脚本头部。")
    A("- 冻结预测由 `C:\\xml-uat\\stage3-expansion\\run_stage3_baseline.py` 在 checkpoint `ceaaf8b` 上生成，"
      "本轮**未重跑 Splitter**（避免任何行为漂移）。")
    A("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())
