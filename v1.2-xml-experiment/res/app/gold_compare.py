# -*- coding: utf-8 -*-
"""
gold_compare.py —— 「人工标准答案 vs 程序结果」自动对照工具（Splitter V2 验收用）

设计原则
--------
1. **按身份与关系判分，不按顺序判分**：内容单元允许被重排（例题前移、练习下沉），
   因此每个单元用「节点集合」表示，所有判定都是集合运算；顺序变化只作为 info 提示。
2. **不实现任何 Stage 2 自动识别算法**：本模块只做对照，不产生结构。
3. 双向检查：既报「程序做错了什么」，也报「gold 没标什么」（标注缺口）与
   「程序多做了什么」。

寻址层（详见 struct_nodes.py）
------------------------------
单元定位支持四种写法，可混用：

  a) `anchor` / `end_anchor`     全局按文档序做文本匹配（最省力的写法）
  b) `scope` + `anchor`          在**指定容器内**匹配文本；
                                 scope 可以是单元格，如 "b12.r1c0"，
                                 于是能表达「同一张表中，前半是知识、后半是题组」
  c) `node`                      直接给一个节点 id（容器 id 表示整个容器）
  d) `spans` / `start`+`end`     节点区间；整数 = 顶层块号（向后兼容旧 gold）

  节点 id 语法：b{seq} ／ b12.r1c0 ／ b12.r1c0.n2 ／ b12.r1c0.n2.r0c1.n0
  容器端点会自动扩展到其首/末后代，因此 `spans: [[2,7]]` 仍表示
  「第 2..7 块里的**全部内容**」，包含其中表格单元格内的段落。

单元字段
--------
  id / role / level / parent / bind_to / scope / anchor / end_anchor / node / spans
  must_stay_together（默认：question_group / shared_material 为 true）

问题码（error = 必须修，warn = 结构降级，info = 只提示不判错）
------------------------------------------------------------
  OMISSION 内容遗漏 ／ DUPLICATION 无意重复 ／ GROUP_SPLIT 题组被拆
  TOC_AS_BODY 目录误当正文 ／ BODY_AS_TOC 正文误当目录
  HIERARCHY 章节关系错误 ／ UNBOUND 共享材料解绑 ／ ROLE_MISMATCH 角色冲突
  MISSED_STRUCTURE gold 有而程序未识别   [完全未覆盖=error / 降级=warn]
  MERGE 独立单元被合并 [warn] ／ EXTRA_STRUCTURE 程序多标结构 [warn]
  PRED_ANCHOR 程序单元定位失败 [error]
  EXTRA_UNIT 程序多出 [info] ／ GOLD_GAP 标注缺口 [info]
  GOLD_OVERLAP ／ GOLD_ANCHOR gold 自身问题 [info]
  ORDER_CHANGE 顺序变化（按约定**不判错**）[info]

命令行
------
  python gold_compare.py --doc <讲义.docx> --gold gold.json [--pred pred.json]
                         [-o report.md] [--json result.json]
  省略 --pred 时只做 gold 自审（锚点可行性 + 覆盖缺口）。
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from struct_doc import read_struct_doc  # noqa: E402
from struct_nodes import ROOT, NodeIndex  # noqa: E402

# ---------------------------------------------------------------
# 词汇表与兼容规则
# ---------------------------------------------------------------
ALL_ROLES = {
    "toc", "section", "shared_material", "question_group", "question_item",
    "answer", "analysis", "knowledge", "unknown", "body",
}

ROLE_RULES = {
    "toc":             {"ok": {"toc"},                             "soft": set()},
    "section":         {"ok": {"section"},                         "soft": {"body", "knowledge"}},
    "shared_material": {"ok": {"shared_material"},                 "soft": {"body", "knowledge", "unknown"}},
    "question_group":  {"ok": {"question_group", "question_item"},  "soft": {"body"}},
    "question_item":   {"ok": {"question_item", "question_group"},  "soft": {"body"}},
    "answer":          {"ok": {"answer", "analysis"},               "soft": {"body", "unknown"}},
    "analysis":        {"ok": {"analysis", "answer"},               "soft": {"body", "unknown"}},
    "knowledge":       {"ok": {"knowledge", "section", "body"},     "soft": set()},
    "unknown":         {"ok": {"unknown"},                         "soft": {"body", "knowledge"}},
    "body":            {"ok": ALL_ROLES,                            "soft": set()},
}

DEFAULT_STAY_TOGETHER = {"question_group", "shared_material"}

HARD_CODES = {"OMISSION", "DUPLICATION", "GROUP_SPLIT", "TOC_AS_BODY", "BODY_AS_TOC",
              "HIERARCHY", "UNBOUND", "ROLE_MISMATCH", "MISSED_STRUCTURE",
              "PRED_ANCHOR"}


def _norm(s):
    """文本归一化：去零宽字符、压缩空白。"""
    s = s or ""
    s = s.replace("\u200b", "").replace("\ufeff", "")
    return re.sub(r"\s+", " ", s).strip()


class Issue(object):
    __slots__ = ("code", "level", "subject", "detail", "nodes")

    def __init__(self, code, level, subject, detail, nodes=None):
        self.code = code
        self.level = level
        self.subject = subject
        self.detail = detail
        self.nodes = list(nodes or [])

    def as_dict(self):
        return {"code": self.code, "level": self.level, "subject": self.subject,
                "detail": self.detail, "nodes": list(self.nodes)}


# ---------------------------------------------------------------
# 单元
# ---------------------------------------------------------------
class Unit(object):
    """gold / 程序结果 共用的内容单元。"""

    def __init__(self, spec, origin):
        self.origin = origin
        self._index = None
        self.id = str(spec.get("id") or "")
        self.role = spec.get("role") or "body"
        self.level = spec.get("level")
        self.parent = spec.get("parent")
        self.bind_to = spec.get("bind_to")
        self.scope = spec.get("scope")
        self.anchor = spec.get("anchor")
        self.end_anchor = spec.get("end_anchor")
        self.node = spec.get("node")
        self.note = spec.get("note") or ""
        if "must_stay_together" in spec:
            self.stay_together = bool(spec["must_stay_together"])
        else:
            self.stay_together = self.role in DEFAULT_STAY_TOGETHER
        raw = spec.get("spans")
        self.raw_spans = []
        if raw:
            self.raw_spans = [(a, b) for a, b in raw]
        elif spec.get("start") is not None and spec.get("end") is not None:
            self.raw_spans = [(spec["start"], spec["end"])]
        self.explicit_spans = bool(self.raw_spans)
        self.spans = []                 # 解析后的 (start_id, end_id) 片段
        self.nodes = set()              # 覆盖的内容节点集合
        self.anchor_matched = None
        self.resolve_error = None
        self._fallback_end = None

    def order_of(self, nid):
        return self._index.order_of(nid) if self._index else None

    def first_node(self):
        if not self.nodes:
            return None
        return min(self.nodes, key=lambda n: self.order_of(n) if self.order_of(n) is not None else 10 ** 9)

    def as_dict(self):
        return {"id": self.id, "role": self.role, "level": self.level,
                "parent": self.parent, "bind_to": self.bind_to,
                "spans": [list(s) for s in self.spans],
                "nodes": sorted(self.nodes,
                                key=lambda n: self.order_of(n) if self.order_of(n) is not None else 10 ** 9)}


# ---------------------------------------------------------------
# 定位解析
# ---------------------------------------------------------------
class Resolver(object):
    """把 anchor / scope / node / spans 解析成内容节点集合。"""

    def __init__(self, index):
        self.index = index
        self.cursor = 0                      # 全局文档序游标（anchor 顺序推进）

    # ---- 基础工具 ----
    def find(self, needle, container, start_order=0):
        n = _norm(needle)
        if not n:
            return None
        for nid in self.index.descendants.get(container, []):
            node = self.index.by_id[nid]
            if node.order < start_order:
                continue
            if n in _norm(node.text):
                return nid
        return None

    def prev_node(self, nid):
        o = self.index.order_of(nid)
        if o is None or o == 0:
            return None
        return self.index.nodes[o - 1].id

    def container_of(self, unit):
        if not unit.scope:
            return ROOT, None
        cid = self.index.resolve_ref(unit.scope)
        if cid is None:
            return ROOT, "scope 为空"
        if cid in self.index.containers:
            return cid, None
        n = self.index.by_id.get(cid)
        if n is not None:
            return n.container, None      # scope 写了内容节点 → 退化为其所属容器
        return None, "scope 未找到: %s" % unit.scope

    def start_node_of(self, unit):
        """预测某单元的起点节点（用于给上一个单元算缺省终点）。"""
        if unit.explicit_spans and unit.raw_spans:
            ref = self.index.resolve_ref(unit.raw_spans[0][0])
            if ref is None:
                return None
            return ref if ref in self.index.by_id else self.index.first_content(ref)
        if unit.node:
            ref = self.index.resolve_ref(unit.node)
            if ref is None:
                return None
            return ref if ref in self.index.by_id else self.index.first_content(ref)
        container, err = self.container_of(unit)
        if err:
            return None
        if unit.anchor:
            return self.find(unit.anchor, container, 0)
        return self.index.first_content(container)

    # ---- 主解析 ----
    def resolve(self, unit):
        unit._index = self.index
        if unit.explicit_spans:
            for a, b in unit.raw_spans:
                ra, rb = self.index.resolve_ref(a), self.index.resolve_ref(b)
                if ra is None or rb is None:
                    unit.resolve_error = "spans 引用非法: %r-%r" % (a, b)
                    continue
                if not self.index.exists(ra) or not self.index.exists(rb):
                    unit.resolve_error = "spans 引用不存在: %s-%s" % (ra, rb)
                    continue
                unit.nodes |= self.index.interval(ra, rb)
                unit.spans.append((ra, rb))
            if unit.raw_spans:
                self.cursor = max(self.cursor, max(
                    [self.index.order_of(n) or 0 for n in unit.nodes] or [0]) + 1)
            return

        container, err = self.container_of(unit)
        if err:
            unit.resolve_error = err
            return

        # —— 起点 ——
        if unit.node:
            # `node` 即完整范围（容器→全部后代），不再按下一单元延伸
            ref = self.index.resolve_ref(unit.node)
            if ref is None or not self.index.exists(ref):
                unit.resolve_error = "node 不存在: %s" % unit.node
                return
            unit.nodes |= self.index.expand(ref)
            if not unit.nodes:
                unit.resolve_error = "node=%s 是空容器（无内容节点）" % unit.node
                return
            first = min(unit.nodes, key=lambda n: self.index.order_of(n))
            last = max(unit.nodes, key=lambda n: self.index.order_of(n))
            unit.anchor_matched = first
            unit.spans.append((first, last))
            self.cursor = max(self.cursor, self.index.order_of(last) + 1)
            return
        if unit.anchor:
            start_from = self.cursor if container == ROOT else 0
            nid = self.find(unit.anchor, container, start_from)
            if nid is None:
                unit.resolve_error = "anchor 未找到: %r（scope=%s）" % (unit.anchor, container)
                return
            unit.anchor_matched = nid
            self.cursor = max(self.cursor, self.index.order_of(nid) + 1)
        else:
            first = self.index.first_content(container)
            if first is None:
                unit.resolve_error = "scope=%s 内没有内容节点" % container
                return
            unit.anchor_matched = first

        start_id = unit.anchor_matched

        # —— 终点 ——
        end_id = None
        if unit.end_anchor:
            nid = self.find(unit.end_anchor, container,
                            self.index.order_of(start_id) + 1)
            if nid is None:
                unit.resolve_error = "end_anchor 未找到: %r（scope=%s）" % (unit.end_anchor, container)
            else:
                end_id = self.prev_node(nid)
        if end_id is None:
            end_id = unit._fallback_end
        if end_id is None:
            end_id = self.index.nodes[-1].id if self.index.nodes else None
        if end_id is None:
            return
        unit.nodes |= self.index.interval(start_id, end_id)
        unit.spans.append((start_id, end_id))


def resolve_units(specs, index, origin):
    """解析单元列表。终点缺省 = 下一单元起点之前的那个节点。"""
    res = Resolver(index)
    units = [Unit(spec, origin) for spec in (specs or [])]
    for k, u in enumerate(units):
        if u.explicit_spans or u.end_anchor:
            continue
        for v in units[k + 1:]:
            nid = res.start_node_of(v)
            if nid is not None:
                u._fallback_end = res.prev_node(nid)
                break
    for u in units:
        res.resolve(u)
    return units


# ---------------------------------------------------------------
# 对照
# ---------------------------------------------------------------
class Comparison(object):
    def __init__(self, doc_name):
        self.doc_name = doc_name
        self.issues = []
        self.gold_units = []
        self.pred_units = []
        self.summary = {}
        self.index = None
        self.content_nodes = set()      # 有内容的节点
        self.pred_nodes = set()         # 程序覆盖的节点

    def add(self, code, level, subject, detail, nodes=None):
        self.issues.append(Issue(code, level, subject, detail, nodes))

    def by_level(self, level):
        return [i for i in self.issues if i.level == level]

    @property
    def verdict(self):
        return "PASS" if not self.by_level("error") else "FAIL"

    def as_dict(self):
        return {"doc": self.doc_name, "verdict": self.verdict,
                "summary": self.summary,
                "gold_units": [u.as_dict() for u in self.gold_units],
                "pred_units": [u.as_dict() for u in self.pred_units],
                "issues": [i.as_dict() for i in self.issues]}


def _covering_unit(units, nid):
    """覆盖该节点的最窄单元。"""
    cands = [u for u in units if nid in u.nodes]
    if not cands:
        return None
    return min(cands, key=lambda u: len(u.nodes))


def _role_verdict(gold_role, pred_role):
    rule = ROLE_RULES.get(gold_role, ROLE_RULES["body"])
    if pred_role in rule["ok"]:
        return "ok"
    if pred_role in rule["soft"]:
        return "soft"
    return "hard"


def compare(doc, gold, pred_units=None):
    """主对照入口。pred_units 为 None 时只做 gold 自审。"""
    index = NodeIndex(doc)
    cmp = Comparison(doc.name)
    cmp.index = index
    order = {n.id: n.order for n in index.nodes}

    def _o(unit):
        f = unit.first_node()
        return order.get(f, 10 ** 9) if f else 10 ** 9

    gold_units = resolve_units(gold.get("units"), index, "gold")
    for u in gold_units:
        if u.resolve_error:
            cmp.add("GOLD_ANCHOR", "info", u.id or "(无id)", u.resolve_error)
    pred_list = resolve_units(pred_units, index, "pred") if pred_units else []
    for u in pred_list:
        if u.resolve_error:
            cmp.add("PRED_ANCHOR", "error", u.id or "(无id)",
                    "程序单元定位失败：%s" % u.resolve_error)
    cmp.gold_units = gold_units
    cmp.pred_units = pred_list

    all_content = index.content_ids
    cmp.content_nodes = all_content
    for p in pred_list:
        cmp.pred_nodes |= p.nodes
    pred_covered = cmp.pred_nodes

    gold_covered = set()
    for u in gold_units:
        gold_covered |= u.nodes

    # —— gold 自检：单元重叠 ——
    g_sorted = sorted(gold_units, key=_o)
    for a, b in zip(g_sorted, g_sorted[1:]):
        inter = a.nodes & b.nodes
        if inter:
            cmp.add("GOLD_OVERLAP", "info", "%s/%s" % (a.id, b.id),
                    "gold 单元节点重叠（标注问题，非程序错误）：%d 个" % len(inter))

    # —— gold 未覆盖的内容（标注缺口）——
    gap = sorted(all_content - gold_covered, key=lambda n: order[n])
    if gap:
        cmp.add("GOLD_GAP", "info", "-",
                "gold 未覆盖 %d 个有内容的节点（标注缺口）" % len(gap), gap[:40])

    if not pred_list:
        cmp.summary = _summarize(cmp, len(gold_units), 0, len(all_content), len(gap))
        return cmp

    # 1) 内容遗漏
    for u in gold_units:
        if not u.nodes:
            continue
        miss = sorted((u.nodes & all_content) - pred_covered, key=lambda n: order[n])
        if miss:
            cmp.add("OMISSION", "error", u.id,
                    "gold 单元 %s(%s) 有 %d 个内容节点未被任何程序单元覆盖"
                    % (u.id, u.role, len(miss)), miss[:20])

    # 2) 无意重复
    for i in range(len(pred_list)):
        for j in range(i + 1, len(pred_list)):
            a, b = pred_list[i], pred_list[j]
            inter = a.nodes & b.nodes
            if inter:
                cmp.add("DUPLICATION", "error", "%s/%s" % (a.id, b.id),
                        "程序单元节点重叠 %d 个（内容会被重复输出）" % len(inter),
                        sorted(inter, key=lambda n: order[n])[:20])

    # 3) 逐 gold 单元对照
    gold_of_pred = {}
    for u in gold_units:
        if not u.nodes:
            continue
        counts = {}
        for nid in u.nodes & all_content:
            p = _covering_unit(pred_list, nid)
            if p is not None:
                counts[p.id] = counts.get(p.id, 0) + 1
        if not counts:
            cmp.add("MISSED_STRUCTURE", "error", u.id,
                    "gold 单元 %s(%s) 完全没有被程序单元覆盖" % (u.id, u.role))
            continue
        main_id = max(counts.items(), key=lambda kv: kv[1])[0]
        main = next(p for p in pred_list if p.id == main_id)
        gold_of_pred.setdefault(main_id, []).append(u)

        rv = _role_verdict(u.role, main.role)
        if rv == "hard":
            code = "TOC_AS_BODY" if (u.role == "toc" and main.role != "toc") else "ROLE_MISMATCH"
            cmp.add(code, "error", "%s->%s" % (u.id, main.id),
                    "角色冲突：gold=%s，程序=%s" % (u.role, main.role))
        elif rv == "soft" and u.role != "body":
            cmp.add("MISSED_STRUCTURE", "warn", "%s->%s" % (u.id, main.id),
                    "结构未识别：gold=%s，程序降级为 %s" % (u.role, main.role))

        # 层级
        if u.level is not None and main.level is not None and u.level != main.level:
            cmp.add("HIERARCHY", "error", "%s->%s" % (u.id, main.id),
                    "层级不一致：gold level=%s，程序 level=%s" % (u.level, main.level))
        if u.parent:
            pu = next((g for g in gold_units if g.id == u.parent), None)
            if pu is not None:
                ppid = None
                f = pu.first_node()
                if f:
                    pcov = _covering_unit(pred_list, f)
                    ppid = pcov.id if pcov is not None else None
                if ppid is None:
                    cmp.add("HIERARCHY", "error", u.id,
                            "父单元 %s 未被识别，父子关系丢失" % u.parent)
                elif main.parent:
                    if main.parent != ppid:
                        cmp.add("HIERARCHY", "error", u.id,
                                "程序声明的父单元 %s 与 gold 父单元对应物 %s 不一致"
                                % (main.parent, ppid))
                elif ppid != main.id:
                    cmp.add("HIERARCHY", "error", u.id,
                            "程序未声明 %s 的父子关系（gold 父单元 %s 对应程序单元 %s）"
                            % (u.id, u.parent, ppid))

        # 题组/材料被拆开（只对已覆盖部分判定；未覆盖交给 OMISSION）
        if u.stay_together and u.nodes:
            cov = u.nodes & pred_covered
            if cov and not any(cov <= p.nodes for p in pred_list):
                pieces = [p.id for p in pred_list if p.nodes & cov]
                cmp.add("GROUP_SPLIT", "error", u.id,
                        "gold 单元 %s(%s) 的内容被拆到 %d 个程序单元：%s"
                        % (u.id, u.role, len(pieces), pieces),
                        sorted(cov, key=lambda n: order[n])[:20])

        # 共享材料绑定
        if u.bind_to:
            mu = next((g for g in gold_units if g.id == u.bind_to), None)
            if mu is None:
                cmp.add("GOLD_ANCHOR", "info", u.id,
                        "bind_to 指向不存在的 gold 单元: %s" % u.bind_to)
            else:
                expect_m = None
                fm = mu.first_node()
                if fm:
                    mcov = _covering_unit(pred_list, fm)
                    expect_m = mcov.id if mcov is not None else None
                if main.bind_to:
                    if expect_m and main.bind_to != expect_m:
                        cmp.add("UNBOUND", "error", "%s<->%s" % (u.id, mu.id),
                                "程序声明的绑定 %s 与材料 %s 的对应物 %s 不一致"
                                % (main.bind_to, mu.id, expect_m))
                else:
                    need = u.nodes | mu.nodes
                    if not any(need <= p.nodes for p in pred_list):
                        cmp.add("UNBOUND", "error", "%s<->%s" % (u.id, mu.id),
                                "共享材料与题组被分到不同程序单元，且程序未声明绑定（解绑）",
                                sorted(need, key=lambda n: order[n])[:20])

    # 4) 合并
    for pid, gs in gold_of_pred.items():
        real = [g for g in gs if g.role != "body"]
        if len(real) >= 2:
            cmp.add("MERGE", "warn", pid,
                    "程序单元 %s 合并了 %d 个独立 gold 单元：%s"
                    % (pid, len(real), [g.id for g in real]))

    # 5) 程序多出 / 反向目录误判
    for p in pred_list:
        pcontent = p.nodes & all_content
        if not pcontent:
            continue
        gold_here = [g for g in gold_units if g.nodes & pcontent]
        if not gold_here:
            cmp.add("EXTRA_UNIT", "info", p.id,
                    "程序单元 %s 不在 gold 覆盖范围内（多出 %d 个节点）"
                    % (p.id, len(pcontent)),
                    sorted(pcontent, key=lambda n: order[n])[:12])
            continue
        if p.role == "toc" and all(g.role != "toc" for g in gold_here):
            cmp.add("BODY_AS_TOC", "error", p.id,
                    "程序把正文判成目录（gold 中该区段为 %s）"
                    % sorted({g.role for g in gold_here}))
        if p.role != "body" and all(g.role == "body" for g in gold_here):
            cmp.add("EXTRA_STRUCTURE", "warn", p.id,
                    "程序多标结构：gold 视为 body，程序标为 %s" % p.role)

    # 6) 顺序变化（按约定不判错，仅提示）
    pred_index = {p.id: k for k, p in enumerate(pred_list)}
    seq_pred = []
    for u in g_sorted:
        if u.role == "body" or not u.nodes:
            continue
        f = u.first_node()
        p = _covering_unit(pred_list, f) if f else None
        if p is not None:
            seq_pred.append(p.id)
    uniq = []
    for pid in seq_pred:
        if not uniq or uniq[-1] != pid:
            uniq.append(pid)
    if len(uniq) >= 2 and len(set(uniq)) == len(uniq):
        out_order = [pred_index[pid] for pid in uniq]
        if out_order != sorted(out_order):
            cmp.add("ORDER_CHANGE", "info", "-",
                    "程序输出顺序与文档/gold 顺序不同（按约定**不判错**，仅在实际重排时出现）："
                    "gold 顺序 %s" % " > ".join(uniq))

    cmp.summary = _summarize(cmp, len(gold_units), len(pred_list),
                             len(all_content), len(gap))
    return cmp


def _summarize(cmp, n_gold, n_pred, n_content, n_gap):
    from collections import Counter
    c = Counter(i.code for i in cmp.issues)
    c["GOLD_GAP"] = c.get("GOLD_GAP", 0)
    return {
        "gold_units": n_gold,
        "pred_units": n_pred,
        "content_nodes": n_content,
        "gold_gap_nodes": n_gap,
        "errors": len(cmp.by_level("error")),
        "warns": len(cmp.by_level("warn")),
        "infos": len(cmp.by_level("info")),
        "code_counts": dict(c),
    }


# ---------------------------------------------------------------
# 报告
# ---------------------------------------------------------------
CODE_LABEL = {
    "OMISSION": "内容遗漏",
    "DUPLICATION": "无意重复",
    "GROUP_SPLIT": "完整题组被拆开",
    "MERGE": "独立单元被合并",
    "TOC_AS_BODY": "目录误当正文",
    "BODY_AS_TOC": "正文误当目录",
    "HIERARCHY": "章节关系错误",
    "UNBOUND": "共享材料与题目解绑",
    "MISSED_STRUCTURE": "gold 有但程序未识别的结构",
    "ROLE_MISMATCH": "角色冲突",
    "PRED_ANCHOR": "程序单元定位失败",
    "GOLD_GAP": "gold 标注缺口",
    "GOLD_OVERLAP": "gold 单元重叠",
    "GOLD_ANCHOR": "gold 定位问题",
    "EXTRA_UNIT": "程序多出的单元",
    "EXTRA_STRUCTURE": "程序多标的结构",
    "ORDER_CHANGE": "顺序变化（不判错）",
}


def _snippet(index, ids, n=3):
    order = {x.id: x.order for x in index.nodes}
    out = []
    for nid in sorted(ids, key=lambda i: order.get(i, 10 ** 9))[:n]:
        t = _norm(index.text_of(nid))[:34]
        out.append("%s %s" % (nid, t or "<无文本>"))
    if len(ids) > n:
        out.append("…共 %d" % len(ids))
    return " ; ".join(out)


def _span_text(u):
    if not u.spans:
        return "-"
    if len(u.spans) == 1:
        a, b = u.spans[0]
        return "%s → %s" % (a, b)
    return "多片段 %d 段" % len(u.spans)


def render_report(doc, cmp, gold_path=None, pred_path=None):
    L = []
    A = L.append
    s = cmp.summary
    index = cmp.index
    A("# 对照报告：人工 Gold vs 程序结果")
    A("")
    A("- 文档：`%s`" % cmp.doc_name)
    if gold_path:
        A("- Gold：`%s`" % gold_path)
    A("- 程序结果：%s" % ("`%s`" % pred_path if pred_path
                        else "**未提供**（本次仅为 gold 自审）"))
    A("- 结论：**%s**　错误 %d ／ 警告 %d ／ 提示 %d"
      % (cmp.verdict, s["errors"], s["warns"], s["infos"]))
    A("")

    A("## 1. 总览")
    A("")
    A("| 指标 | 值 |")
    A("|---|---|")
    A("| gold 单元数 | %d |" % s["gold_units"])
    A("| 程序单元数 | %d |" % s["pred_units"])
    A("| 有内容的节点 | %d |" % s["content_nodes"])
    A("| gold 未覆盖的节点 | %d |" % s["gold_gap_nodes"])
    A("| 全部内容节点 | %d |" % len(index.nodes))
    A("| 容器数（body/表格/单元格） | %d |" % len(index.containers))
    A("")

    A("## 2. 问题统计")
    A("")
    if not cmp.issues:
        A("无任何问题。")
    else:
        from collections import Counter
        cnt = Counter((i.code, i.level) for i in cmp.issues)
        A("| 问题码 | 含义 | 级别 | 数量 |")
        A("|---|---|---|---|")
        for (code, level), n in sorted(cnt.items(), key=lambda kv: (kv[0][1], -kv[1])):
            A("| %s | %s | %s | %d |"
              % (code, CODE_LABEL.get(code, code),
                 {"error": "错误", "warn": "警告", "info": "提示"}[level], n))
    A("")

    A("## 3. 单元对照表")
    A("")
    if not cmp.pred_units:
        A("> 本次未提供程序结果（gold 自审）：下表只列 gold 自身的解析结果。")
        A("")
    A("| gold 单元 | 角色 | level | 节点范围 | 节点数 | 落到程序单元 | 程序角色 | 结果 |")
    A("|---|---|---|---|---|---|---|---|")
    for u in cmp.gold_units:
        pid, prole, res = "-", "-", "未识别"
        f = u.first_node()
        if f:
            p = _covering_unit(cmp.pred_units, f)
            if p is not None:
                pid, prole = p.id, p.role
                rv = _role_verdict(u.role, p.role)
                res = {"ok": "OK", "soft": "角色降级", "hard": "角色冲突"}[rv]
            if not cmp.pred_units:
                res = "已标注（自审）"
            else:
                cov = u.nodes & cmp.pred_nodes
                if (u.nodes & cmp.content_nodes) - cmp.pred_nodes:
                    res = "内容遗漏"
                elif u.stay_together and cov and not any(
                        cov <= q.nodes for q in cmp.pred_units):
                    res = "被拆开"
        A("| %s | %s | %s | %s | %d | %s | %s | %s |"
          % (u.id, u.role, u.level if u.level is not None else "-",
             _span_text(u), len(u.nodes), pid, prole, res))
    A("")

    A("## 4. 问题明细")
    A("")
    if not cmp.issues:
        A("无。")
    else:
        for level, title in (("error", "错误（必须修）"), ("warn", "警告"),
                             ("info", "提示（不判错／标注缺口）")):
            items = [i for i in cmp.issues if i.level == level]
            if not items:
                continue
            A("### %s" % title)
            A("")
            for i in items:
                A("- **%s** `%s` %s" % (CODE_LABEL.get(i.code, i.code), i.subject, i.detail))
                if i.nodes:
                    A("  - 涉及节点：%s" % _snippet(index, i.nodes))
            A("")

    A("## 5. 判分口径说明")
    A("")
    A("- **顺序变化不判错**：内容单元允许重排（例题前移、练习下沉）。")
    A("  单元用「节点集合」表示（见 struct_nodes.py），判定均为身份与关系的集合运算。")
    A("- **表格内部结构可标注**：节点 id 形如 `b12.r1c0.n3`；")
    A("  容器端点自动展开到首/末后代，因此整数区间 `[[2,7]]` 仍表示「这几块的全部内容」。")
    A("- `GROUP_SPLIT` 判据：gold 标注为整体（题组/共享材料）的节点集合，")
    A("  其**已被程序覆盖的部分**必须完全落在同一个程序单元内。")
    A("- `UNBOUND` 判据：共享材料与其绑定题组的节点并集必须落在同一个程序单元内")
    A("  （程序声明了 `bind_to` 时以声明为准校验）。")
    A("- `OMISSION` / `DUPLICATION` 只统计**有内容**的节点（文字/图片/OLE/公式）。")
    A("- `GOLD_GAP` 是标注缺口（gold 没标到的内容），**不是程序错误**。")
    A("")
    return "\n".join(L)


# ---------------------------------------------------------------
# CLI
# ---------------------------------------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser(description="Gold vs 程序结果 自动对照（只读）")
    ap.add_argument("--doc", required=True, help="讲义 docx 路径")
    ap.add_argument("--gold", required=True, help="gold label json")
    ap.add_argument("--pred", help="程序结果 json（省略则只做 gold 自审）")
    ap.add_argument("-o", "--out", help="报告输出路径（markdown）")
    ap.add_argument("--json", dest="json_out", help="结果输出路径（json）")
    args = ap.parse_args()

    doc = read_struct_doc(args.doc)
    gold = load_json(args.gold)
    pred = load_json(args.pred).get("units") if args.pred else None
    cmp = compare(doc, gold, pred)
    report = render_report(doc, cmp, args.gold, args.pred)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)
        print("报告已写出: %s" % args.out)
    else:
        print(report)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(cmp.as_dict(), fh, ensure_ascii=False, indent=2)
        print("JSON 已写出: %s" % args.json_out)
    print("结论: %s（错误 %d / 警告 %d / 提示 %d）"
          % (cmp.verdict, len(cmp.by_level("error")),
             len(cmp.by_level("warn")), len(cmp.by_level("info"))))
    return 0 if cmp.verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
