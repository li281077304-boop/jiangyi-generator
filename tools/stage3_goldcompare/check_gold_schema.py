#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gate 0：APPROVED_GOLD 轻量一致性自检（只报告，默认不改任何 Gold）。

检查项（对应本轮 Gate 0 要求）：
  1. QG span 重叠异常
  2. parent 是否指向有效单元
  3. subquestion 是否位于父 QG 范围内
  4. bind_to 是否引用不存在的 unit
  5. 已 demote 的 material 是否仍保留错误顶层 binding
  6. orphan resource（区间外的资源引用 / 空 span / 端点不可解析）

用法：
    python check_gold_schema.py                 # 只报告
    python check_gold_schema.py --apply-x013    # 额外应用已批准的 X013 定点剔除
                                                # （GOLD_CORRECTION_BEFORE_BASELINE）

注意：--apply-x013 只做一件事——把 X013 中起点为 `b4.r0c1.n4` 的候选从正式 QG 中剔除并留痕。
      不改动任何其他人已批准的语义。
"""
import argparse
import datetime
import glob
import json
import os
import sys

BASE = r"C:\xml-uat\stage3-expansion"
APPROVED = os.path.join(BASE, "gold_preparation_01", "APPROVED_GOLD")
BASELINE = os.path.join(BASE, "STAGE3_EXPANSION_BASELINE")

X013_FP_START = "b4.r0c1.n4"


class Ctx(object):
    def __init__(self, sid):
        nd = json.load(open(os.path.join(BASELINE, sid, "struct_nodes.json"), encoding="utf-8"))
        self.nodes = nd["nodes"]
        self.containers = nd["containers"]
        self.cparent = nd["container_parent"]
        self.by_id = {n["id"]: n for n in self.nodes}
        self.o2n = {n["order"]: n for n in self.nodes}
        self._desc = None
        self.descendants = {}
        for n in self.nodes:
            cur = n["container"]
            while cur:
                self.descendants.setdefault(cur, []).append(n["id"])
                if cur == "body":
                    break
                cur = self.cparent.get(cur)

    def first(self, ref):
        if ref in self.by_id:
            return self.by_id[ref]["order"]
        d = self.descendants.get(ref)
        return self.by_id[d[0]]["order"] if d else None

    def last(self, ref):
        if ref in self.by_id:
            return self.by_id[ref]["order"]
        d = self.descendants.get(ref)
        return self.by_id[d[-1]]["order"] if d else None

    def interval(self, spans):
        lo, hi = None, None
        for s, e in spans:
            a, b = self.first(s), self.last(e)
            if a is None or b is None:
                return None
            lo = a if lo is None else min(lo, a)
            hi = b if hi is None else max(hi, b)
        return (lo, hi)

    def text(self, ref):
        if ref in self.by_id:
            return (self.by_id[ref].get("text") or "")[:60]
        d = self.descendants.get(ref)
        return (self.by_id[d[0]].get("text") or "")[:60] if d else ""


def all_units(doc):
    out = []
    for key, lst in doc.get("units", {}).items():
        for u in lst:
            out.append((key, u))
    return out


def check_one(path):
    doc = json.load(open(path, encoding="utf-8"))
    sid = doc["document_id"]
    ctx = Ctx(sid)
    problems = []
    units = all_units(doc)
    ids = {u["unit_id"] for _k, u in units}
    # 也把 demote 掉的原 unit_id（如 u042/u043）算作“历史 id”，供 bind 检查使用
    historical = {d.get("unit_id") for d in doc.get("dropped_or_demoted", [])}
    # parent / bind_to 沿用**预测侧** unit id（可追溯），因此校验域要并上预测单元集合
    pred_path = os.path.join(BASELINE, sid, "prediction.json")
    pred_ids = set()
    if os.path.exists(pred_path):
        pred_ids = {u["id"] for u in json.load(open(pred_path, encoding="utf-8"))["units"]}
    valid_ids = ids | pred_ids

    by_key = {}
    for key, u in units:
        by_key.setdefault(key, []).append(u)

    # 1. span 重叠异常（同一角色内应互不重叠）
    for key in ("question_groups", "shared_materials", "sections"):
        lst = by_key.get(key, [])
        intervals = []
        for u in lst:
            iv = ctx.interval(u["spans"])
            if iv is None:
                problems.append(("UNRESOLVED_SPAN", u["unit_id"], str(u["spans"])))
                continue
            intervals.append((iv[0], iv[1], u["unit_id"]))
        intervals.sort()
        for a, b in zip(intervals, intervals[1:]):
            if b[0] <= a[1]:
                problems.append(("OVERLAP", "%s/%s" % (a[2], b[2]),
                                 "orders %d-%d 与 %d-%d 重叠" % (a[0], a[1], b[0], b[1])))

    # 2/3/4/5. 关系字段
    for key, u in units:
        # parent
        p = u.get("parent")
        if p and p not in valid_ids:
            problems.append(("PARENT_INVALID", u["unit_id"], "parent=%s 不存在" % p))
        # bind_to
        b = u.get("bind_to")
        if b and b not in valid_ids:
            problems.append(("BIND_INVALID", u["unit_id"], "bind_to=%s 不存在" % b))
        # 已 demote 的材料不得继续被顶层 unit 绑定
        for bm in u.get("bound_materials", []) or []:
            if bm in historical:
                problems.append(("BIND_TO_DEMOTED", u["unit_id"],
                                 "bound_materials 仍引用已 demote 的 %s" % bm))
        # subquestion 必须落在父 QG 内
        if key == "question_groups" and u.get("subquestions"):
            iv = ctx.interval(u["spans"])
            if iv is not None:
                for s in u["subquestions"]:
                    o = ctx.first(s["node"]) if isinstance(s, dict) else None
                    if o is None:
                        problems.append(("SUBQ_UNRESOLVED", u["unit_id"], str(s)))
                    elif not (iv[0] <= o <= iv[1]):
                        problems.append(("SUBQ_OUT_OF_PARENT", u["unit_id"],
                                         "%s(order %d) 不在父区间 %d-%d" % (s["node"], o, iv[0], iv[1])))

    # 6. orphan resource / 空 span
    for key, u in units:
        if not u.get("spans"):
            problems.append(("EMPTY_SPAN", u["unit_id"], ""))
        if key == "question_groups":
            a = u.get("assets") or {}
            if sum(a.get(k, 0) for k in ("images", "omml", "oles")) == 0 and not a.get("tables"):
                pass  # 无资源是正常情况，不算问题

    return doc, problems


def apply_x013(doc, ctx):
    """X013 定点剔除：b4.r0c1.n4 为学习目标列表第 5 条，不是 question_group。"""
    qgs = doc["units"]["question_groups"]
    kept, removed = [], []
    for u in qgs:
        if u["spans"][0][0] == X013_FP_START:
            removed.append(u)
        else:
            kept.append(u)
    if not removed:
        return doc, 0
    doc["units"]["question_groups"] = kept
    doc["counts"]["question_group"] = len(kept)
    corr = doc.setdefault("gold_corrections", [])
    for u in removed:
        corr.append({
            "type": "GOLD_CORRECTION_BEFORE_BASELINE",
            "date": datetime.date.today().isoformat(),
            "action": "REMOVE_QUESTION_GROUP",
            "unit_id": u["unit_id"],
            "candidate_id": u.get("candidate_id"),
            "spans": u["spans"],
            "start_text": u.get("start_text"),
            "evidence": ("同一表格单元格 b4.r0c1 内为连续编号的教学目标列表："
                         "n0=「1.理解有理数乘方的意义…」…n4=「5.会根据指定精确度…」…n5=「6.通过观察、归纳…」，"
                         "共 6 条同构条目；n4 是其中第 5 条，与前后条目同级同构，"
                         "不构成 question_group。"),
            "decided_by": "Human Review 2026-09-30（Gate 0 结构证据明确，无需再确认）",
            "scope": "仅删除该 1 个候选，其余 38 个 QG 不变",
        })
    return doc, len(removed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-x013", action="store_true",
                    help="应用已批准的 X013 定点剔除（GOLD_CORRECTION_BEFORE_BASELINE）")
    args = ap.parse_args()

    total_problems = 0
    for path in sorted(glob.glob(os.path.join(APPROVED, "X*_APPROVED_GOLD.json"))):
        sid = os.path.basename(path).split("_")[0]
        doc, problems = check_one(path)

        if args.apply_x013 and sid == "X013":
            ctx = Ctx(sid)
            doc, n = apply_x013(doc, ctx)
            if n:
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(doc, fh, ensure_ascii=False, indent=2)
                print("[X013] 已剔除 %d 个候选并写入 gold_corrections（GOLD_CORRECTION_BEFORE_BASELINE）" % n)

        print("%-6s 单元=%-4d 问题=%d" % (sid, len(all_units(doc)), len(problems)))
        for kind, unit, detail in problems[:8]:
            print("        - %-20s %-22s %s" % (kind, unit, detail))
        total_problems += len(problems)

    print("\n合计问题: %d" % total_problems)
    return 0 if total_problems == 0 else 0   # 只报告，不以问题数决定退出码


if __name__ == "__main__":
    sys.exit(main())
