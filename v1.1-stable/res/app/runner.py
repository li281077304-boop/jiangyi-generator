# -*- coding: utf-8 -*-
"""
runner.py —— PowerShell 执行器 + 讲义生成编排

职责：
  1. _run_version：把一份 version 配置序列化为 JSON，交给对应 PS1 脚本执行
  2. run_plan：按顺序执行 plan.json 里的多个版本
  3. build_version：单份讲义的完整编排（拆分 → 目标 → 填充模板 → 输出）
"""
import os
import json
import re
import time
import tempfile
import subprocess
import locale

from docutils import POWERSHELL, body_paragraphs, scan_paragraphs
from objectives import make_objectives
from split_engine import auto_split, _protect_reading_spans
import config
import logger

log = logger.get_logger("runner")

# 纯装饰段：空或只有 / ~ - _ = * 等符号（图片标题常落在这种段落里）
_DECOR_RE = re.compile(r'^[/\\~\-_=*#\s·.。、，,|]*$')


def _adjust_image_blocks(blocks: list, full: list) -> list:
    """
    图片标题归属修正（不依赖 OCR，用位置启发式）：
    紧贴块边界的「纯图片/装饰段」（文本为空或纯符号、且段落含图片）划入下一块，
    避免图片标题残留在上一块末尾（例如"课后三阶 精准练习"标题图落在知识区）。

    只回溯最多 2 段，且只在遇到"有内容的段落"时停止；
    正文中的公式/示意图（嵌在文本段内，非纯装饰）不受影响。
    full: [(idx, text, has_img), ...]
    """
    idx_map = {i: (t, h) for i, t, h in full}
    for k in range(len(blocks) - 1):
        cur = blocks[k]
        nxt = blocks[k + 1]
        cut = None
        lo = max(nxt["start"] - 3, cur.get("start", 1))
        for j in range(nxt["start"] - 1, lo - 1, -1):
            item = idx_map.get(j)
            if not item:
                break
            t, h = item
            if h and _DECOR_RE.match(t):
                cut = j          # 纯图片装饰段 → 并入下一块
            else:
                break            # 遇到有内容段即停
        if cut is not None:
            new_end = cut - 1
            if new_end >= cur.get("start", 1) - 1:
                cur["end"] = new_end
            nxt["start"] = cut
    return blocks


def _run_version(v: dict, template: str):
    """把一份 version 配置交给 PowerShell 填充模板，返回 PS 输出文本。"""
    template_type = v.get("template_type", "1v1")
    ps_script = config.PS_FILL_CLASS if template_type == "class" else config.PS_FILL_1V1
    params = {
        "label":        v["label"],
        "source_doc":   os.path.abspath(v["source"]),
        "template":     os.path.abspath(template),
        "output_doc":   os.path.abspath(v["output"]),
        "topic_name":   v.get("topic", ""),
        "objectives":   v.get("objectives", ""),
        "difficulties": v.get("difficulties", ""),
        "blocks":       v["blocks"],
        "fmt":          v.get("fmt", False),
        "template_type": v.get("template_type", "1v1"),
        "grade":        v.get("grade", ""),
        "subject":      v.get("subject", ""),
        "handout_type": v.get("handout_type", ""),
        "trim_blanks":  v.get("trim_blanks", True),
    }
    fd, pj = tempfile.mkstemp(suffix=".json", prefix="params_")
    os.close(fd)
    with open(pj, "w", encoding="utf-8") as f:
        json.dump(params, f, ensure_ascii=False)
    try:
        r = subprocess.run(
            [POWERSHELL, "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", ps_script, "-ParamsJson", pj],
            capture_output=True, text=True, encoding=locale.getpreferredencoding(),
            errors="replace", timeout=180)
        if r.returncode not in (0, 1) and r.stderr.strip():
            # PowerShell diagnostics from legacy documents can contain U+FFFD.
            # Keep diagnostics from turning a completed COM operation into a
            # GBK-console encoding exception.
            console_encoding = locale.getpreferredencoding()
            safe_stderr = r.stderr[:600].encode(
                console_encoding, errors="replace").decode(console_encoding)
            print("[PS stderr]", safe_stderr)
        return r.stdout
    finally:
        if os.path.exists(pj):
            os.remove(pj)


def run_plan(plan: dict, template: str):
    """顺序执行 plan 里所有版本，逐个填充模板。"""
    for i, v in enumerate(plan["versions"]):
        if i > 0:
            time.sleep(2)   # 等上一个 Word 进程退出
        print(f"[{v['label']}] 执行...")
        _run_version(v, template)


def _write_split_debug(output_path: str, text: str) -> str:
    """把候选分块复盘写到输出文件旁边，失败不影响讲义生成。"""
    try:
        base, _ = os.path.splitext(output_path)
        debug_path = base + "_split_debug.txt"
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(text)
        return debug_path
    except Exception as e:
        log.warning("split_debug 写入失败: %s", e)
        return ""


def _ideal_blocks(paras: list, block_size: int = 10) -> list:
    """
    ideal 模式（题型清单式文档专用，供"例题提取+重编号"后的源使用）。

    分区优先：若题型区之后出现「提升专练 / 真题感知」分区标题，则
      知识精讲 = 开头 .. 题型1 前（知识点/考点区）
      即时训练 = 题型1 .. 分区标题前（必考题型区）
      巩固练习 = 分区标题 .. 文末（提升专练 + 真题感知）
    无分区标题时退回按题量分块：
      即时训练 = 题型1 .. 第 block_size 题，巩固练习 = 剩余。
    不分难度，纯按分区/题量切块。无题型结构时返回 None（交给 smart 降级）。
    """
    QNUM = re.compile(r'^\s*(\d{1,3})\s*[.．、]\s*[（(]\s*(20\d\d|\d{2}-)')
    TYPE = re.compile(r'^【题型\s*\d+')
    SECT = re.compile(r'提升专练|真题感知')
    first_type = None
    sect_pos = None
    qnums = []
    first_idx = paras[0][0] if paras else 1
    for idx, t in paras:
        s = t.strip()
        if first_type is None and TYPE.match(s):
            first_type = idx
        m = QNUM.match(s)
        if m:
            qnums.append(idx)
    # 分区标题只认题型1 之后的（导航区"复习提升：真题感知+提升专练"会误中）
    if first_type is not None:
        for idx, t in paras:
            if idx < first_type:
                continue
            if SECT.search(t.strip()):
                sect_pos = idx
                break
    if first_type is None or not qnums or len(qnums) < 2:
        return None
    last = paras[-1][0]
    blocks = [{"marker": "知识精讲", "start": first_idx, "end": first_type - 1}]
    if sect_pos:
        blocks.append({"marker": "即时训练", "start": first_type, "end": sect_pos - 1})
        blocks.append({"marker": "六、巩固练习", "start": sect_pos, "end": last})
    else:
        cut_idx = qnums[min(block_size, len(qnums)) - 1]       # 第 block_size 题的段落号
        if len(qnums) > block_size:
            end1 = qnums[block_size] - 1                       # 第 block_size+1 题前
        else:
            end1 = last
        blocks.append({"marker": "即时训练", "start": first_type, "end": end1})
        if len(qnums) > block_size:
            blocks.append({"marker": "六、巩固练习", "start": qnums[block_size], "end": last})
    return blocks


def _split_blocks(paras, split_mode, api_key, topic, source, output, template_type):
    """
    按 split_mode 计算分块：
      full      → 全部贴进「知识精讲」
      ideal     → 例题提取+重编号后的题型清单文档：知识区 + 按 10 题切两个题块
      candidate → T0c 候选边界混合分块（省 API，可选 LLM 复核）
      smart     → 四层降级（LLM → 混合 → TOC → 启发式）
    返回 (blocks, split_debug_path, debug_lines)
    """
    first = paras[0][0] if paras else 1
    if split_mode == "full":
        total = len(paras)
        blocks = [{"marker": "知识精讲", "start": first,
                   "end": paras[-1][0] if paras else total}]
        return blocks, "", []

    if split_mode == "ideal":
        blocks = _ideal_blocks(paras, block_size=10)
        if blocks:
            return blocks, "", []
        # 无题型结构 → 降级 smart

    if split_mode == "candidate":
        from split_candidates import analyze_candidates, format_candidate_report
        from selective_llm_split import needs_api_review, selective_llm_review

        result = analyze_candidates(paras, template_type=template_type)
        need_api, api_reason = needs_api_review(result)
        review = selective_llm_review(
            paras, result=result, template_type=template_type,
            api_key=api_key, title=topic,
        )
        debug_lines = [
            f"文件: {os.path.basename(source)}",
            f"专题: {topic}",
            f"版本: {os.path.basename(output)}",
            "模式: candidate / T0c 候选边界混合分块",
            "",
            format_candidate_report(result),
            "",
            "API复核判断",
            "-" * 50,
            f"是否需要 API: {'是' if need_api else '否'}",
            f"原因: {api_reason}",
        ]
        if review and review.get("blocks"):
            blocks = review["blocks"]
            if review.get("skipped"):
                debug_lines.append(f"API未调用: {review.get('reason', '')}")
            else:
                debug_lines.append(f"API复核理由: {review.get('reason', '')}")
        else:
            blocks = result["blocks"]
            debug_lines.append("API复核结果: 未调用、失败或返回非法，采用离线候选结果。")
        blocks = _protect_reading_spans(blocks, paras, first)
        debug_lines.extend(["", "最终用于生成的 blocks", "-" * 50])
        for blk in blocks:
            debug_lines.append(f"{blk.get('marker')}: {blk.get('start')}-{blk.get('end')}")
        split_debug_path = _write_split_debug(output, "\n".join(debug_lines))
        return blocks, split_debug_path, debug_lines

    # smart 模式
    if api_key:
        blocks = auto_split(paras, template_type=template_type,
                            enable_llm=True, enable_hybrid=True, api_key=api_key)
    else:
        blocks = auto_split(paras, template_type=template_type,
                            enable_llm=False, enable_hybrid=False)
        # 练习区内部精修（基础→能力成对标记切分）
        try:
            from practice_splitter import refine_practice_split
            blocks = refine_practice_split(paras, blocks)
        except ImportError:
            pass
    return blocks, "", []


def build_version(label, source, output, topic, paras=None,
                  objectives="", difficulties="", template=config.DEFAULT_TEMPLATE,
                  fmt=True, template_type="1v1", grade="", subject="", handout_type="",
                  split_mode="smart", api_key=""):
    """生成单份讲义。返回 (version_dict, ps_output)。

    paras 兼容两种格式：
      - [(idx, text)]          旧格式（纯文本，不做图片归属修正）
      - [(idx, text, has_img)] 完整格式（docutils.scan_paragraphs），
        拆分后做"图片标题归属修正"：紧贴边界的纯图片装饰段划入下一块。
    """
    if paras is None:
        paras = scan_paragraphs(source)
    if paras and isinstance(paras[0], tuple) and len(paras[0]) >= 3:
        full_paras = paras
        text_paras = [(i, t) for i, t, _ in full_paras]
    else:
        full_paras = None
        text_paras = paras

    blocks, split_debug_path, _ = _split_blocks(
        text_paras, split_mode, api_key, topic, source, output, template_type)

    if full_paras:
        blocks = _adjust_image_blocks(blocks, full_paras)

    v = {"label": label, "source": source, "output": output,
         "topic": topic, "objectives": objectives, "difficulties": difficulties,
         "blocks": blocks, "fmt": fmt,
         "template_type": template_type, "grade": grade, "subject": subject,
         "handout_type": handout_type, "split_debug_path": split_debug_path}
    log_out = _run_version(v, template)
    return v, log_out
