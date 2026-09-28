#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
practice_splitter.py  ——  练习题区内精确切分

在 T2 已经分出的练习区段落中，找"基础速刷/能力跃升"等成对标记，
把练习区精确切为 即时训练 + 巩固练习。

独立模块，不改动 split_engine.py 核心逻辑。
"""
import re
from typing import List, Dict, Tuple


# 成对标记：基础标记 → 即时训练，能力标记 → 巩固练习
_PRACTICE_PAIRS = [
    # (基础型, 能力型)
    ("基础速刷", "能力跃升"),
    ("基础训练", "能力提升"),
    ("基础演练", "能力进阶"),
    ("基础练习", "综合提升"),
    ("基础巩固", "拔高训练"),
    ("对点训练", "拓展训练"),
    ("即学即练", "变式训练"),
    ("真题闯关", "课后三阶"),
    ("基础达标", "素养提升"),
    ("基础篇", "提高篇"),
    ("A组", "B组"),
    ("基础过关", "能力突破"),
]

# 单独出现也可能是练习区边界的词（不看成对，直接识别）
_SOLO_PRACTICE = [
    "真题闯关", "课后三阶", "基础速刷", "能力跃升",
    "即时训练", "巩固练习", "当堂检测", "随堂练习",
]


def find_practice_boundary(paras: List[Tuple[int, str]], 
                           practice_start: int, practice_end: int) -> int:
    """
    在练习区段落中找"基础→能力"的分界点。

    返回: 巩固练习的起始段落号，找不到返回 None
    """
    # 策略1: 找成对标记中"能力型"首次出现的位置（跳过目录区）
    TOC_END = 20  # 目录区通常在文档前 20 段
    for pair in _PRACTICE_PAIRS:
        basic_found = False
        for pidx, text in paras:
            if pidx < practice_start or pidx <= TOC_END: continue
            if pidx > practice_end: break
            t = text.strip()

            # 先找基础标记
            if pair[0] in t:
                basic_found = True
            # 基础后再找能力标记
            if basic_found and pair[1] in t:
                return pidx

    # 策略2: 找独立出现的能力型标记
    ability_keywords = [p[1] for p in _PRACTICE_PAIRS]
    for pidx, text in paras:
        if pidx < practice_start or pidx <= TOC_END: continue
        if pidx > practice_end: break
        t = text.strip()
        for kw in ability_keywords:
            if kw in t:
                return pidx

    return None


def refine_practice_split(paras, blocks) -> List[Dict]:
    """
    对已有的 blocks，在练习区内部用成对标记精修。

    输入: auto_split 返回的 blocks
    输出: 精修后的 blocks
    """
    if not blocks or len(blocks) < 2:
        return blocks

    # 找到练习区（即时训练+巩固练习合并范围）
    practice_start = None
    practice_end = None
    for b in blocks:
        if b.get("marker") in ("即时训练", "六、巩固练习", "六、出门测试") and b["start"] <= b["end"]:
            if practice_start is None: practice_start = b["start"]
            practice_end = max(practice_end or 0, b["end"])

    if practice_start is None:
        return blocks

    boundary = find_practice_boundary(paras, practice_start, practice_end)

    if boundary is None or boundary <= practice_start or boundary >= practice_end:
        return blocks

    # 拆分：即时训练 = 练习区开始到能力标记前，巩固练习 = 能力标记到练习区末尾
    new_blocks = []
    for blk in blocks:
        marker = blk.get("marker", "")
        if marker == "即时训练" and blk["start"] <= blk["end"]:
            new_blocks.append({"marker": "即时训练", "start": blk["start"], "end": boundary - 1})
        elif marker in ("六、巩固练习", "六、出门测试") and blk["start"] <= blk["end"]:
            if boundary > blk["start"]:
                new_blocks.append({"marker": marker, "start": boundary, "end": blk["end"]})
            else:
                new_blocks.append(blk)
        else:
            new_blocks.append(blk)

    return new_blocks
