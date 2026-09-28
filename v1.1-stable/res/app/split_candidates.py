#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_candidates.py — V1.1 候选边界调试器

目标：不让离线语义模型当“大脑”，而是先用稳定规则找少量候选边界。
后续如果需要 API，只把候选边界附近的小窗口交给 API 复核。

本模块暂不接入 auto_split 主流程，先服务 CLI 测试和人工复盘。
"""
import re
from typing import Dict, List, Optional, Tuple

Para = Tuple[int, str]
Candidate = Dict[str, object]

_PRACTICE_MARKERS = [
    "基础速刷", "基础训练", "基础演练", "基础练习", "基础巩固", "基础达标",
    "对点训练", "即学即练", "真题闯关", "真题演练", "当堂检测", "随堂检测",
    "课堂练习", "达标检测", "基础篇", "A组", "即时训练",
]

_CONSOLIDATION_MARKERS = [
    "能力跃升", "能力提升", "能力进阶", "能力突破", "综合提升", "综合训练",
    "拔高训练", "拓展训练", "变式训练", "课后三阶", "素养提升", "提高篇",
    "B组", "巩固练习", "出门测试", "出门测速",
]

_KNOWLEDGE_MARKERS = [
    "知识梳理", "核心知识", "知识点", "考点", "教材精研", "典例精讲",
    "方法归纳", "归纳总结", "例题", "典例",
]

_QNUM_RE = re.compile(r"^\s*(\d{1,3})\s*[.．、)）]\s*\S")
_YEAR_MARK_RE = re.compile(r"[（(]\s*\d{4}\s*[.·年]")
_CHOICE_RE = re.compile(r"^\s*[A-D]\s*[.．、]")
_BLANK_RE = re.compile(r"[（(]\s*[）)]\s*$|__+")
_XUEKE_RE = re.compile(r"^(0[1-5])\s+(.+)$")
_TOC_DOTS_RE = re.compile(r"\.{5,}")
_READING_RE = re.compile(r"^(【真题再现】|Passage\s+\d+|Reading\s+Comprehension)", re.I)


def _short(text: str, limit: int = 80) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    if len(text) <= limit:
        return text
    return text[:limit - 1] + "…"


def _add_candidate(items: List[Candidate], kind: str, para: int, score: int,
                   reason: str, text: str, source: str) -> None:
    score = max(0, min(100, int(score)))
    items.append({
        "kind": kind,
        "para": para,
        "score": score,
        "reason": reason,
        "text": _short(text),
        "source": source,
    })


def _merge_candidates(items: List[Candidate]) -> List[Candidate]:
    """同一 kind + para 的候选合并，保留最高分并拼接理由。"""
    merged: Dict[Tuple[str, int], Candidate] = {}
    for item in items:
        key = (str(item["kind"]), int(item["para"]))
        if key not in merged:
            merged[key] = dict(item)
            continue
        old = merged[key]
        if int(item["score"]) > int(old["score"]):
            old["score"] = item["score"]
            old["text"] = item["text"]
            old["source"] = item["source"]
        reasons = str(old["reason"]).split("；")
        reason = str(item["reason"])
        if reason not in reasons:
            old["reason"] = str(old["reason"]) + "；" + reason
    return sorted(merged.values(), key=lambda x: (-int(x["score"]), int(x["para"])))


def _has_choice_near(paras: List[Para], start_para: int, window: int = 5) -> bool:
    for pidx, text in paras:
        if pidx <= start_para:
            continue
        if pidx > start_para + window:
            break
        if _CHOICE_RE.match(text.strip()):
            return True
    return False


def _looks_like_toc_xueke(paras: List[Para], para_idx: int) -> bool:
    """判断学科网 01-05 标题是否只是目录条目，而不是正文标题。"""
    nonblank = [(idx, txt.strip()) for idx, txt in paras if txt.strip()]
    pos = None
    for i, (idx, _) in enumerate(nonblank):
        if idx == para_idx:
            pos = i
            break
    if pos is None:
        return False

    idx, text = nonblank[pos]
    if not _XUEKE_RE.match(text):
        return False

    neighbors = []
    for j in range(max(0, pos - 4), min(len(nonblank), pos + 5)):
        if j == pos:
            continue
        n_idx, n_text = nonblank[j]
        if abs(n_idx - idx) <= 8 and _XUEKE_RE.match(n_text):
            neighbors.append((n_idx, n_text))

    # 目录里 04/05 常常挨在一起；正文里 04 后面应有大量内容再到 05。
    current = _XUEKE_RE.match(text).group(1)
    for n_idx, n_text in neighbors:
        sec = _XUEKE_RE.match(n_text).group(1)
        if current == "04" and sec == "05" and 0 < n_idx - idx <= 2:
            return True
        if current == "05" and sec == "04" and 0 < idx - n_idx <= 2:
            return True


    return False

def _numbered_positions(paras: List[Para]) -> List[int]:
    positions = []
    last_num = 0
    for pidx, text in paras:
        t = text.strip()
        m = _QNUM_RE.match(t)
        if not m:
            continue
        num = int(m.group(1))
        if num == last_num + 1 or (num == 1 and last_num >= 1) or num <= 2:
            positions.append(pidx)
            last_num = num
    return positions


def _question_density_candidates(paras: List[Para], items: List[Candidate]) -> None:
    """用连续编号题和选择题特征找练习区起点候选。"""
    if not paras:
        return
    first, last = paras[0][0], paras[-1][0]
    total_span = max(last - first, 1)
    numbered = _numbered_positions(paras)
    if len(numbered) < 3:
        return

    text_by_idx = {idx: text for idx, text in paras}
    for i in range(len(numbered) - 2):
        a, b, c = numbered[i], numbered[i + 1], numbered[i + 2]
        if c - a > 18:
            continue
        t = text_by_idx.get(a, "")
        pos_ratio = (a - first) / total_span
        strong = bool(_YEAR_MARK_RE.search(t) or _BLANK_RE.search(t) or _has_choice_near(paras, a))
        if strong:
            score = 86
            reason = "连续编号题且有年份/选项/填空特征"
        elif pos_ratio >= 0.25:
            score = 74
            reason = "文档中后段出现连续编号题"
        else:
            score = 62
            reason = "较早出现连续编号题，可能是知识编号，低置信"
        _add_candidate(items, "practice_start", a, score, reason, t, "question_density")
        return


def collect_boundary_candidates(paras: List[Para]) -> Dict[str, List[Candidate]]:
    """收集即时训练和巩固练习的候选起点。"""
    raw: List[Candidate] = []
    if not paras:
        return {"practice_start": [], "consolidation_start": []}

    for pidx, text in paras:
        t = text.strip()
        if not t:
            continue
        if _TOC_DOTS_RE.search(t):
            continue
        if _looks_like_toc_xueke(paras, pidx):
            continue

        m = _XUEKE_RE.match(t)
        if m:
            sec = m.group(1)
            if sec == "04":
                _add_candidate(raw, "practice_start", pidx, 96, "学科网 04 练习章节", t, "toc")
            elif sec == "05":
                _add_candidate(raw, "consolidation_start", pidx, 98, "学科网 05 课后三阶/巩固章节", t, "toc")

        for marker in _PRACTICE_MARKERS:
            if marker in t:
                score = 97 if marker in ("基础速刷", "基础训练", "真题闯关", "即时训练") else 90
                _add_candidate(raw, "practice_start", pidx, score, f"练习标记：{marker}", t, "marker")
                break

        for marker in _CONSOLIDATION_MARKERS:
            if marker in t:
                score = 98 if marker in ("能力跃升", "能力提升", "课后三阶", "巩固练习") else 91
                _add_candidate(raw, "consolidation_start", pidx, score, f"巩固标记：{marker}", t, "marker")
                break

        if _READING_RE.match(t):
            _add_candidate(raw, "practice_start", pidx, 88, "阅读理解/真题再现起点", t, "reading")

    _question_density_candidates(paras, raw)

    practice = _merge_candidates([c for c in raw if c["kind"] == "practice_start"])
    consolidation = _merge_candidates([c for c in raw if c["kind"] == "consolidation_start"])
    return {"practice_start": practice, "consolidation_start": consolidation}


def choose_boundaries(paras: List[Para], candidates: Dict[str, List[Candidate]]) -> Dict[str, Optional[Candidate]]:
    """选择最可信的两个边界。"""
    practice = candidates.get("practice_start", [])
    consolidation = candidates.get("consolidation_start", [])
    chosen_practice = practice[0] if practice else None
    chosen_cons = None

    if chosen_practice:
        p_para = int(chosen_practice["para"])
        after = [c for c in consolidation if int(c["para"]) > p_para]
        if after:
            chosen_cons = after[0]

    if chosen_practice and not chosen_cons:
        fallback = _fallback_consolidation(paras, int(chosen_practice["para"]))
        if fallback:
            chosen_cons = fallback

    return {"practice_start": chosen_practice, "consolidation_start": chosen_cons}


def _fallback_consolidation(paras: List[Para], practice_start: int) -> Optional[Candidate]:
    numbered = [p for p in _numbered_positions(paras) if p >= practice_start]
    if len(numbered) >= 4:
        cut = max(1, int(round(len(numbered) * 0.7)))
        if cut < len(numbered):
            para = numbered[cut]
            text = dict(paras).get(para, "")
            return {
                "kind": "consolidation_start",
                "para": para,
                "score": 55,
                "reason": "未发现明确巩固标记，按题目数量 70% 兜底",
                "text": _short(text),
                "source": "fallback",
            }
    if paras:
        last = paras[-1][0]
        para = practice_start + int((last - practice_start) * 0.7)
        para = max(practice_start + 1, min(para, last))
        text = dict(paras).get(para, "")
        return {
            "kind": "consolidation_start",
            "para": para,
            "score": 45,
            "reason": "未发现明确巩固标记，按段落比例 70% 兜底",
            "text": _short(text),
            "source": "fallback",
        }
    return None


def build_blocks_from_boundaries(paras: List[Para], chosen: Dict[str, Optional[Candidate]],
                                 template_type: str = "1v1") -> List[Dict[str, int]]:
    if not paras:
        return []
    first, last = paras[0][0], paras[-1][0]
    k_marker = {"1v1": "知识精讲", "class": "知识精讲&例题讲解"}.get(template_type, "知识精讲")
    p_marker = {"1v1": "六、巩固练习", "class": "六、出门测试"}.get(template_type, "六、巩固练习")

    practice = chosen.get("practice_start")
    cons = chosen.get("consolidation_start")
    if not practice:
        p_start = first + int((last - first) * 0.5)
    else:
        p_start = int(practice["para"])
    if not cons:
        c_start = p_start + int((last - p_start) * 0.7)
    else:
        c_start = int(cons["para"])

    p_start = max(first, min(p_start, last))
    c_start = max(p_start + 1, min(c_start, last)) if p_start < last else last

    return [
        {"marker": k_marker, "start": first, "end": max(first, p_start - 1)},
        {"marker": "即时训练", "start": p_start, "end": max(p_start, c_start - 1)},
        {"marker": p_marker, "start": c_start, "end": last},
    ]


def validate_blocks(blocks: List[Dict[str, int]], paras: List[Para]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not paras:
        return False, ["文档无段落"]
    first, last = paras[0][0], paras[-1][0]
    if len(blocks) != 3:
        errors.append(f"blocks 数量不是 3：{len(blocks)}")
    prev_end = None
    for i, block in enumerate(blocks):
        start = int(block.get("start", 0))
        end = int(block.get("end", 0))
        marker = block.get("marker", f"block{i + 1}")
        if start > end:
            errors.append(f"{marker} start > end：{start}>{end}")
        if start < first or end > last:
            errors.append(f"{marker} 越界：{start}-{end} 不在 {first}-{last}")
        if prev_end is not None and start <= prev_end:
            errors.append(f"{marker} 与上一块重叠：start={start}, prev_end={prev_end}")
        prev_end = end
    return not errors, errors


def analyze_candidates(paras: List[Para], template_type: str = "1v1") -> Dict[str, object]:
    candidates = collect_boundary_candidates(paras)
    chosen = choose_boundaries(paras, candidates)
    blocks = build_blocks_from_boundaries(paras, chosen, template_type)
    valid, errors = validate_blocks(blocks, paras)
    return {
        "candidates": candidates,
        "chosen": chosen,
        "blocks": blocks,
        "valid": valid,
        "errors": errors,
    }


def format_candidate_report(result: Dict[str, object], top_n: int = 6) -> str:
    lines: List[str] = []
    candidates = result["candidates"]
    chosen = result["chosen"]
    blocks = result["blocks"]

    lines.append("候选边界")
    lines.append("-" * 50)
    for kind, title in (("practice_start", "即时训练候选"), ("consolidation_start", "巩固练习候选")):
        lines.append(title)
        items = candidates.get(kind, [])[:top_n]
        if not items:
            lines.append("  （无）")
            continue
        for item in items:
            lines.append(
                f"  [{item['score']:>3}] 段落 {item['para']}: {item['reason']} | {item['text']}"
            )

    lines.append("")
    lines.append("最终选择")
    lines.append("-" * 50)
    for kind, title in (("practice_start", "即时训练开始"), ("consolidation_start", "巩固练习开始")):
        item = chosen.get(kind)
        if item:
            lines.append(f"{title}: 段落 {item['para']}，{item['reason']}，置信度 {item['score']}")
        else:
            lines.append(f"{title}: 未找到明确候选")

    lines.append("")
    lines.append("生成 blocks")
    lines.append("-" * 50)
    for block in blocks:
        lines.append(f"  {block['marker']}: {block['start']}-{block['end']}")
    lines.append(f"合法性: {'通过' if result['valid'] else '失败'}")
    for err in result.get("errors", []):
        lines.append(f"  - {err}")
    return "\n".join(lines)



