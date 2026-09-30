# TOC-based section splitter — HIGHEST PRIORITY for auto_split
# Completely rewritten to properly isolate TOC region, extract clean names,
# classify them, and match them to body positions.

import re

# Practice section keywords (for classification of CLEAN TOC names)
_PRACTICE_TOC_KW = [
    '真题闯关', '溯源演练', '课后三阶', '精准练习',
    '拔高', '分层集训', '基础演练', '能力进阶',
    '即时训练', '巩固练习', '出门测试',
    '对点训练', '当堂检测', '课后作业', '巩固训练', '真题演练',
    '即学即练', '变式训练', '拓展训练',
    '完成句子', '完型填空', '阅读理解', '短文填空', '语法填空', '写作', '听力',
    '真题再现', '真题', '模拟', '强化演练',
]

# Knowledge section keywords
_KNOWLEDGE_TOC_KW = [
    '考情', '分析解读', '备考策略', '命题预测',
    '基础', '知识梳理', '知识导图', '核心梳理',
    '重难', '核心突破', '教材精研', '内容全解',
    '本节导航', '目标清单', '避坑指南', '解题通法',
    '课标单词', '目标短语', '常考句型', '重点语法', '知识清单',
    '课堂启动', '知识回顾', '归纳总结',
    '解题技巧', '考法预测', '答案与解析', '语篇导读', '长难句分析',
    '深化点拨', '典例精讲', '典型例题', '经典例题', '例题讲解',
]

# TOC entry pattern: text followed by 5+ dots and optional page number
_TOC_LINE_RE = re.compile(r'^(.+?)\s*\.{5,}\s*\d*\s*$')

# Dots-only TOC line detection
_HAS_TOC_DOTS = re.compile(r'\.{5,}')


def _clean_toc_name(raw_text):
    """Extract clean section name from a TOC line.
    '真题·命题感知..................................................... 30' → '真题·命题感知'
    """
    t = raw_text.strip()
    # Try TOC dotted-line pattern first
    m = _TOC_LINE_RE.match(t)
    if m:
        return m.group(1).strip()
    # Fallback: remove trailing dots and numbers
    t = re.sub(r'\.{3,}\s*\d*$', '', t).strip()
    return t


def classify_toc_name(name):
    """Classify a CLEAN section name as 'knowledge', 'practice', or None.
    Only call this on extracted TOC names, not raw paragraphs."""
    for kw in _PRACTICE_TOC_KW:
        if kw in name:
            return 'practice'
    for kw in _KNOWLEDGE_TOC_KW:
        if kw in name:
            return 'knowledge'
    # Structured numbered sections: 01-03=knowledge, 04-05=practice
    m = re.match(r'^0(\d)\s+[^\s]+·[^\s]+', name)
    if m:
        num = int(m.group(1))
        return 'knowledge' if num <= 3 else 'practice'
    # Chinese numbered: 第X部分 / 专题X
    if re.match(r'^(第[一二三四五六七八九十\d]+[部分章节课时单元模块]|专题\s*\d+|考点\s*\d+)', name):
        return 'practice'  # numbered sections are typically exercise zones
    return None


def detect_toc_structure(paras, max_scan=100):
    """
    Find the TOC region and extract clean section names.
    Returns (entries, toc_end_idx) where:
      entries = [(toc_para_idx, type, clean_name), ...]
      toc_end_idx = paragraph index where TOC region ends (or None)
    Only paragraphs with TOC dot-patterns are treated as TOC entries.
    """
    entries = []
    toc_started = False
    toc_end_idx = None

    for idx, txt in paras:
        if idx > max_scan:
            break
        t = txt.strip()
        if not t:
            if toc_started:
                toc_end_idx = idx  # blank line after TOC = TOC end
                break
            continue

        # Detect TOC start: "目录" or "Contents" as a standalone short line
        if not toc_started and t in ('目录', 'Contents', 'CONTENTS', '目  录'):
            toc_started = True
            continue

        if not toc_started:
            continue

        # In TOC region: only recognize dotted-line entries
        if _HAS_TOC_DOTS.search(t):
            name = _clean_toc_name(t)
            if name and len(name) >= 2:
                cls = classify_toc_name(name)
                if cls:
                    entries.append((idx, cls, name))
        elif len(t) < 40:
            # Non-dotted short line in TOC region → might be TOC end or non-entry
            # Check if it looks like body content (not TOC)
            if not _HAS_TOC_DOTS.search(t) and toc_started and len(entries) >= 1:
                toc_end_idx = idx
                break

    if toc_started and toc_end_idx is None:
        toc_end_idx = max((e[0] for e in entries), default=max_scan) + 1

    return entries, toc_end_idx


def find_toc_in_body(paras, toc_name, start_from=1, search_range=300):
    """
    Find a TOC section name in the document body.
    Uses exact match → substring match → fuzzy match fallback.
    """
    if not toc_name or len(toc_name) < 2:
        return None

    name_clean = toc_name.strip()

    # Pass 1: exact match
    for idx, txt in paras:
        if idx < start_from:
            continue
        if idx > start_from + search_range:
            break
        if txt.strip() == name_clean:
            return idx

    # Pass 2: line starts with the name
    for idx, txt in paras:
        if idx < start_from:
            continue
        if idx > start_from + search_range:
            break
        if txt.strip().startswith(name_clean):
            return idx

    # Pass 3: name appears as contiguous substring
    for idx, txt in paras:
        if idx < start_from:
            continue
        if idx > start_from + search_range:
            break
        if name_clean in txt.strip():
            return idx

    # Pass 4: fuzzy — remove all non-letter chars and try again
    fuzzy = re.sub(r'[^\u4e00-\u9fff\w]', '', name_clean)
    if len(fuzzy) >= 3:
        for idx, txt in paras:
            if idx < start_from:
                continue
            if idx > start_from + search_range:
                break
            body_fuzzy = re.sub(r'[^\u4e00-\u9fff\w]', '', txt.strip())
            if fuzzy in body_fuzzy:
                return idx

    return None


def _detect_section_headers_as_nav(paras):
    """
    Fallback: when no dotted-line TOC exists, scan all paragraphs for
    ·-pattern section headers and use them as navigation structure.
    Returns (entries, None) matching detect_toc_structure format.
    """
    # Match ·-pattern headers: 考情·X / 基础·X / 重难·X / 拔高·X etc.
    DOT_HEADER = re.compile(r'^(考情|基础|重难|拔高|真题|进阶|能力|综合|素养|方法|技巧|知识|考点|命题|考向)[·・]')
    entries = []
    seen_names = set()
    
    for idx, txt in paras:
        t = txt.strip()
        m = DOT_HEADER.match(t)
        if not m:
            continue
        # Extract clean name (remove parenthetical if present, but keep for classification)
        name = re.sub(r'[（(][^）)]*[）)]', '', t).strip()
        if not name or len(name) < 3:
            continue
        if name in seen_names:
            continue
        seen_names.add(name)
        
        cls = classify_toc_name(t)  # use full text for classification (includes parenthetical)
        if not cls:
            cls = classify_toc_name(name)  # retry with clean name
        if cls:
            entries.append((idx, cls, name))
    
    return entries


def build_toc_blocks(paras, first_para, last_para, template_type="1v1"):
    """
    FULL TOC-DRIVEN SPLIT: use ALL TOC entries to create blocks.
    This is the authoritative split when TOC is available.

    Priority:
      1) Traditional dotted-line TOC (目录 + ..... 点线)
      2) Fallback: ·-pattern section headers as navigation

    Returns list of blocks, or None if TOC can't produce a valid split.
    """
    entries, toc_end = detect_toc_structure(paras)

    # Fallback: if no dotted-line TOC, try ·-pattern section headers
    if len([e for e in entries if e[1] in ('knowledge', 'practice')]) < 2:
        entries = _detect_section_headers_as_nav(paras)
        toc_end = None

    # Need at least 2 classified entries for a meaningful split
    if len([e for e in entries if e[1] in ('knowledge', 'practice')]) < 2:
        return None

    # Separate knowledge and practice entries
    k_entries = [(idx, name) for idx, cls, name in entries if cls == 'knowledge']
    p_entries = [(idx, name) for idx, cls, name in entries if cls == 'practice']

    if not p_entries:
        return None  # no practice sections — can't split

    # Map practice entries to body positions
    body_positions = []
    if toc_end is None:
        # Fallback mode: entries are already body paragraph indices
        body_positions = [(idx, name) for idx, cls, name in entries if cls == 'practice']
    else:
        # Traditional TOC: map TOC entries to body positions
        search_start = toc_end
        for toc_idx, name in p_entries:
            body_idx = find_toc_in_body(paras, name, start_from=search_start)
            if body_idx:
                body_positions.append((body_idx, name))
            if body_idx:
                search_start = body_idx + 1

    if len(body_positions) < 1:
        return None  # can't map to body

    # Sort by body position
    body_positions.sort(key=lambda x: x[0])

    # Template markers
    _KM = {"1v1": "知识精讲", "class": "知识精讲&例题讲解"}
    _PM = {"1v1": "六、巩固练习", "class": "六、出门测试"}
    k_marker = _KM.get(template_type, "知识精讲")
    p_marker = _PM.get(template_type, "六、巩固练习")

    blocks = []

    # Knowledge block: from first para to just before first practice section
    first_practice_body = body_positions[0][0]
    if first_practice_body > first_para:
        blocks.append({"marker": k_marker, "start": first_para, "end": first_practice_body - 1})
    else:
        blocks.append({"marker": k_marker, "start": 1, "end": 0})

    # Practice blocks: split remaining practice sections into 即时训练 + 巩固练习
    if len(body_positions) >= 2:
        # Use 70/30 split on practice sections
        n = len(body_positions)
        cut = max(1, int(round(n * 0.7)))
        train_sections = body_positions[:cut]
        practice_sections = body_positions[cut:]

        # 即时训练: from first practice to end of last training section
        train_end = practice_sections[0][0] - 1 if practice_sections else last_para
        blocks.append({"marker": "即时训练", "start": first_practice_body, "end": train_end})

        # 巩固练习: remaining practice sections
        if practice_sections:
            blocks.append({"marker": p_marker, "start": practice_sections[0][0], "end": last_para})
        else:
            blocks.append({"marker": p_marker, "start": train_end + 1, "end": last_para})
    else:
        # Only 1 practice section: split by proportion within it
        q_span = last_para - first_practice_body
        train_cut = first_practice_body + int(q_span * 0.7)
        blocks.append({"marker": "即时训练", "start": first_practice_body, "end": train_cut})
        blocks.append({"marker": p_marker, "start": train_cut + 1, "end": last_para})

    return blocks
