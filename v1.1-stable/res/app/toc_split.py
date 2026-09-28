# TOC-based section splitter — HIGHEST PRIORITY for auto_split
# Completely rewritten to properly isolate TOC region, extract clean names,
# classify them, and match them to body positions.

import re

# Practice section keywords (for classification of CLEAN TOC names).
# T1 should not guess practice splits by ratio when the navigation already
# names the two exercise blocks. Keep a finer role internally:
#   basic_practice    -> 即时训练
#   advanced_practice -> 六、巩固练习 / 出门测试
_BASIC_PRACTICE_TOC_KW = [
    '基础训练', '基础巩固', '基础过关', '基础达标', '基础速刷',
    '基础演练', '基础练习', '基础篇', '对点训练', '即学即练',
    '当堂检测', '随堂检测', '课堂练习', '达标检测',
    '真题闯关', '溯源演练', '真题演练', '真题再现', '真题',
    '即时训练',
]

_ADVANCED_PRACTICE_TOC_KW = [
    '培优训练', '培优提升', '培优', '提优训练', '提优',
    '能力提升', '能力跃升', '能力进阶', '能力突破',
    '综合提升', '综合训练', '综合应用', '拔高训练', '拔高',
    '拓展训练', '拓展提升', '拓展延伸', '变式训练',
    '课后三阶', '精准练习', '分层集训', '巩固练习', '巩固训练',
    '出门测试', '素养提升', '提高篇', 'B组',
]

_PRACTICE_TOC_KW = _BASIC_PRACTICE_TOC_KW + _ADVANCED_PRACTICE_TOC_KW + [
    '完成句子', '完型填空', '阅读理解', '短文填空', '语法填空', '写作', '听力',
    '模拟', '强化演练',
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
    role = classify_toc_role(name)
    if role in ('basic_practice', 'advanced_practice', 'practice'):
        return 'practice'
    if role == 'knowledge':
        return 'knowledge'
    return None


def classify_toc_role(name):
    """Return a finer TOC role: knowledge/basic_practice/advanced_practice/practice."""
    for kw in _ADVANCED_PRACTICE_TOC_KW:
        if kw in name:
            return 'advanced_practice'
    for kw in _BASIC_PRACTICE_TOC_KW:
        if kw in name:
            return 'basic_practice'
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
        if num <= 3:
            return 'knowledge'
        return 'basic_practice' if num == 4 else 'advanced_practice'
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
                cls = classify_toc_role(name)
                if cls:
                    entries.append((idx, cls, name))
        elif len(t) < 60:
            # Some handouts use a visual TOC without dot leaders but keep short
            # text entries. Only accept known section names; otherwise treat as
            # possible body start.
            name = _clean_toc_name(t)
            cls = classify_toc_role(name)
            if cls:
                entries.append((idx, cls, name))
                continue
            if toc_started and len(entries) >= 1:
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
    # Match explicit body headers: 基础训练 / 培优训练, plus ·-pattern headers.
    HEADER = re.compile(
        r'^(考情|基础|重难|拔高|真题|进阶|能力|综合|素养|方法|技巧|知识|考点|命题|考向)[·・]'
        r'|^(基础训练|基础巩固|基础过关|基础达标|基础速刷|基础演练|基础练习|对点训练|即学即练|即时训练)$'
        r'|^(培优训练|培优提升|提优训练|能力提升|能力跃升|能力进阶|能力突破|综合提升|拔高训练|拓展训练|课后三阶|巩固练习)$'
    )
    entries = []
    seen_names = set()
    
    for idx, txt in paras:
        t = txt.strip()
        # Many platform exports decorate headers with symbols, emoji, or bullets:
        # "⚡基础速刷", "🚀能力跃升", "【基础训练】". Strip those wrappers only
        # for header detection; keep the original text for matching/reporting.
        header_text = re.sub(r'^[^\u4e00-\u9fffA-Za-z0-9]+', '', t)
        header_text = header_text.strip('【】[]（）()：: ')
        header_text = re.sub(r'^[一二三四五六七八九十]+[、.．]\s*', '', header_text)
        m = HEADER.match(t)
        if not m:
            m = HEADER.match(header_text)
        if not m:
            continue
        # Extract clean name (remove parenthetical if present, but keep for classification)
        name = re.sub(r'[（(][^）)]*[）)]', '', header_text or t).strip()
        if not name or len(name) < 3:
            continue
        if name in seen_names:
            continue
        seen_names.add(name)
        
        cls = classify_toc_role(t)  # use full text for classification (includes parenthetical)
        if not cls:
            cls = classify_toc_role(name)  # retry with clean name
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
    if len([e for e in entries if e[1] in ('knowledge', 'basic_practice', 'advanced_practice', 'practice')]) < 2:
        entries = _detect_section_headers_as_nav(paras)
        toc_end = None

    practice_roles = ('basic_practice', 'advanced_practice', 'practice')

    # Separate knowledge and practice entries.
    p_entries = [(idx, cls, name) for idx, cls, name in entries if cls in practice_roles]

    if not p_entries:
        return None  # no practice sections — can't split

    # Map practice entries to body positions
    body_positions = []
    if toc_end is None:
        # Fallback mode: entries are already body paragraph indices
        body_positions = [(idx, cls, name) for idx, cls, name in entries if cls in practice_roles]
    else:
        # Traditional TOC: map TOC entries to body positions
        search_start = toc_end
        for toc_idx, cls, name in p_entries:
            body_idx = find_toc_in_body(paras, name, start_from=search_start)
            if body_idx:
                body_positions.append((body_idx, cls, name))
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

    # Practice blocks: named sections win. Do not split a single practice section
    # by ratio; that was the source of many structure-damaging cuts.
    basic_positions = [p for p in body_positions if p[1] == 'basic_practice']
    advanced_positions = [p for p in body_positions if p[1] == 'advanced_practice']

    if basic_positions and advanced_positions:
        basic_start = basic_positions[0][0]
        advanced_after_basic = [p for p in advanced_positions if p[0] > basic_start]
        if advanced_after_basic:
            advanced_start = advanced_after_basic[0][0]
            blocks.append({"marker": "即时训练", "start": basic_start, "end": advanced_start - 1})
            blocks.append({"marker": p_marker, "start": advanced_start, "end": last_para})
            return blocks

    # Fallback for generic practice sections or only one named exercise block:
    # knowledge + one exercise block. The template can leave the other exercise
    # anchor empty; preserving source structure is more important than forcing
    # three blocks.
    first_role = body_positions[0][1]
    marker = p_marker if first_role == 'advanced_practice' else "即时训练"
    blocks.append({"marker": marker, "start": first_practice_body, "end": last_para})

    return blocks
