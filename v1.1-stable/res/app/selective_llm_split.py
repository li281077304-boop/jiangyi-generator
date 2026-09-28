#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selective_llm_split.py — V1.1 小窗口 API 复核

只在离线候选边界不确定时调用 API，并且只发送候选边界附近的小窗口。
它不替代 T0a 全文分块，也暂不接入 auto_split 主流程。
"""
import json
import re
from typing import Dict, List, Optional, Tuple

from split_candidates import analyze_candidates, build_blocks_from_boundaries, validate_blocks

Para = Tuple[int, str]
Candidate = Dict[str, object]
CandidateResult = Dict[str, object]


def _short(text: str, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    if len(text) <= limit:
        return text
    return text[:limit - 1] + "…"


def needs_api_review(result: CandidateResult) -> Tuple[bool, str]:
    """判断候选边界是否需要 API 复核。"""
    chosen = result.get("chosen", {})
    practice = chosen.get("practice_start") if isinstance(chosen, dict) else None
    cons = chosen.get("consolidation_start") if isinstance(chosen, dict) else None
    if not practice:
        return True, "缺少即时训练候选"
    if not cons:
        return True, "缺少巩固练习候选"

    p_score = int(practice.get("score", 0))
    c_score = int(cons.get("score", 0))
    if p_score < 80:
        return True, f"即时训练候选置信度偏低：{p_score}"
    if c_score < 80:
        return True, f"巩固练习候选置信度偏低：{c_score}"
    if practice.get("source") == "fallback" or cons.get("source") == "fallback":
        return True, "至少一个边界来自兜底比例"

    candidates = result.get("candidates", {})
    if isinstance(candidates, dict):
        for kind, label in (("practice_start", "即时训练"), ("consolidation_start", "巩固练习")):
            items = candidates.get(kind, []) or []
            if len(items) >= 2:
                top = int(items[0].get("score", 0))
                second = int(items[1].get("score", 0))
                gap = abs(int(items[0].get("para", 0)) - int(items[1].get("para", 0)))
                if top - second <= 5 and gap >= 20:
                    return True, f"{label}存在多个高分候选"

    return False, "离线候选足够明确"


def _allowed_candidate_map(result: CandidateResult) -> Dict[str, Dict[int, Candidate]]:
    allowed: Dict[str, Dict[int, Candidate]] = {"practice_start": {}, "consolidation_start": {}}
    candidates = result.get("candidates", {})
    if isinstance(candidates, dict):
        for kind in allowed:
            for item in candidates.get(kind, []) or []:
                allowed[kind][int(item["para"])] = dict(item)
    chosen = result.get("chosen", {})
    if isinstance(chosen, dict):
        for kind in allowed:
            item = chosen.get(kind)
            if item:
                allowed[kind][int(item["para"])] = dict(item)
    return allowed


def _snap_to_allowed(kind: str, para: int, allowed: Dict[str, Dict[int, Candidate]]) -> Optional[Candidate]:
    """API 只能选择候选段落；非候选段落一律拒绝。"""
    items = allowed.get(kind, {})
    return items.get(para)


def _context_lines(paras: List[Para], centers: List[int], window: int) -> List[str]:
    by_idx = {idx: text for idx, text in paras}
    selected = set()
    for center in centers:
        for idx, _ in paras:
            if center - window <= idx <= center + window:
                selected.add(idx)
    lines = []
    for idx in sorted(selected):
        text = by_idx.get(idx, "")
        if text.strip():
            lines.append(f"[{idx}] {_short(text)}")
    return lines


def build_selective_prompt(paras: List[Para], result: CandidateResult,
                           title: str = "", window: int = 10) -> Tuple[str, str, Dict[str, object]]:
    """构造只包含候选边界和附近上下文的 API prompt。"""
    candidates = result.get("candidates", {})
    chosen = result.get("chosen", {})
    centers: List[int] = []
    candidate_lines: List[str] = []

    if isinstance(candidates, dict):
        for kind, label in (("practice_start", "即时训练开始"), ("consolidation_start", "巩固练习开始")):
            candidate_lines.append(f"{label}候选：")
            items = candidates.get(kind, []) or []
            if not items:
                candidate_lines.append("- 无明确候选")
                continue
            for item in items[:5]:
                para = int(item["para"])
                centers.append(para)
                candidate_lines.append(
                    f"- 段落 {para}，分数 {item['score']}，原因：{item['reason']}，文本：{item['text']}"
                )

    if isinstance(chosen, dict):
        for item in chosen.values():
            if item:
                centers.append(int(item["para"]))

    context = _context_lines(paras, sorted(set(centers)), window)
    system_prompt = """你是讲义结构分析助手。你只能在给定候选边界中选择，不要自由创造段落号。
任务：判断 knowledge/practice/consolidation 三块边界。
输出只允许 JSON，不要解释性正文。"""
    user_prompt = f"""文档标题：{title or '未提供'}
总段落数：{len(paras)}

候选边界：
{chr(10).join(candidate_lines)}

候选边界附近上下文：
{chr(10).join(context)}

请只输出 JSON：
{{
  "practice_start": 123,
  "consolidation_start": 456,
  "reason": "简短说明为什么选择这些候选"
}}
"""
    meta = {
        "candidate_chars": len("\n".join(candidate_lines)),
        "context_chars": len("\n".join(context)),
        "total_prompt_chars": len(user_prompt),
        "centers": sorted(set(centers)),
    }
    return system_prompt, user_prompt, meta


def parse_selective_response(response: str, paras: List[Para], result: CandidateResult) -> Optional[Dict[str, object]]:
    """解析并校验 API 返回。非法返回 None。"""
    if not response:
        return None
    try:
        m = re.search(r"\{.*\}", response, re.DOTALL)
        data = json.loads(m.group(0) if m else response)
    except Exception:
        return None

    try:
        practice_para = int(data.get("practice_start"))
        cons_para = int(data.get("consolidation_start"))
    except Exception:
        return None

    if not paras:
        return None
    first, last = paras[0][0], paras[-1][0]
    if not (first <= practice_para < cons_para <= last):
        return None

    allowed = _allowed_candidate_map(result)
    practice = _snap_to_allowed("practice_start", practice_para, allowed)
    cons = _snap_to_allowed("consolidation_start", cons_para, allowed)
    if not practice or not cons:
        return None

    reason = str(data.get("reason", "API 复核选择候选边界")).strip()
    return {
        "chosen": {"practice_start": practice, "consolidation_start": cons},
        "reason": reason,
    }


def blocks_from_review(paras: List[Para], review: Dict[str, object], template_type: str = "1v1") -> Optional[List[Dict[str, int]]]:
    chosen = review.get("chosen")
    if not isinstance(chosen, dict):
        return None
    blocks = build_blocks_from_boundaries(paras, chosen, template_type)
    valid, errors = validate_blocks(blocks, paras)
    if not valid:
        return None
    return blocks


def selective_llm_review(paras: List[Para], result: Optional[CandidateResult] = None,
                         template_type: str = "1v1", api_key: str = "",
                         title: str = "", force: bool = False) -> Optional[Dict[str, object]]:
    """执行小窗口 API 复核。无 key 或无需复核时返回 None。"""
    if result is None:
        result = analyze_candidates(paras, template_type)
    need, why = needs_api_review(result)
    if not force and not need:
        return {"skipped": True, "reason": why, "blocks": result.get("blocks")}
    if not api_key:
        return None

    system_prompt, user_prompt, meta = build_selective_prompt(paras, result, title=title)
    try:
        from llm_split import _call_deepseek
        response = _call_deepseek(user_prompt, system_prompt, max_tokens=220, api_key=api_key)
    except Exception:
        return None
    review = parse_selective_response(response or "", paras, result)
    if not review:
        return None
    blocks = blocks_from_review(paras, review, template_type)
    if not blocks:
        return None
    review["blocks"] = blocks
    review["prompt_meta"] = meta
    return review

