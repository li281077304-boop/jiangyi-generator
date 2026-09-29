# TOC-based section classifier for auto_split
# Extracted from handout.py to keep the function cleaner

import re

# Knowledge section keywords (from TOC/first-100-paras headers)
_KNOWLEDGE_TOC_KW = [
    '考情', '分析解读', '备考策略', '命题预测',
    '基础', '知识梳理', '知识导图', '核心梳理',
    '重难', '核心突破', '教材精研', '内容全解',
    '本节导航', '目标清单', '避坑指南', '解题通法',
    '课标单词', '目标短语', '常考句型', '重点语法', '知识清单',
    '课堂启动', '知识回顾', '归纳总结',
    '解题技巧', '考法预测', '答案与解析', '语篇导读', '长难句分析',
    '深化点拨', '典例精讲', '典型例题', '经典例题',
]

# Practice section keywords
_PRACTICE_TOC_KW = [
    '真题闯关', '溯源演练', '课后三阶', '精准练习',
    '拔高', '分层集训', '基础演练', '能力进阶',
    '即时训练', '巩固练习', '出门测试',
    '对点训练', '当堂检测', '课后作业', '巩固训练', '真题演练',
    '即学即练', '变式训练', '拓展训练',
    '完成句子', '完型填空', '阅读理解', '短文填空', '语法填空', '写作', '听力',
    '真题再现',
]


def classify_toc_line(text):
    """Classify a TOC/header line as 'knowledge', 'practice', or None"""
    t = text.strip()
    for kw in _PRACTICE_TOC_KW:
        if kw in t:
            return 'practice'
    for kw in _KNOWLEDGE_TOC_KW:
        if kw in t:
            return 'knowledge'
    # Structured numbered sections: 01-03=knowledge, 04-05=practice
    m = re.match(r'^0(\d)\s+[^\s]+·[^\s]+', t)
    if m:
        num = int(m.group(1))
        return 'knowledge' if num <= 3 else 'practice'
    return None


def detect_toc_structure(paras, max_scan=80):
    """
    Scan the first max_scan paragraphs for a table of contents.
    Returns a list of (para_idx, label, toc_text) for practice-classified entries,
    which serve as split boundaries.
    """
    toc_entries = []
    for idx, txt in paras:
        if idx > max_scan:
            break
        t = txt.strip()
        if not t or len(t) < 3:
            continue
        classification = classify_toc_line(t)
        if classification:
            # Only keep practice entries (they mark question boundaries)
            # and the LAST knowledge entry (marks end of knowledge zone)
            toc_entries.append((idx, classification, t[:60]))
    
    # Find the first practice-classified entry — that's the primary boundary
    first_practice = None
    for idx, cls, txt in toc_entries:
        if cls == 'practice':
            first_practice = idx
            break
    
    # Also collect ALL practice entries for multi-section splits
    practice_boundaries = [(idx, txt) for idx, cls, txt in toc_entries if cls == 'practice']
    
    return first_practice, practice_boundaries, toc_entries


def find_toc_in_body(paras, toc_text_hint, start_from=1, search_range=200):
    """
    Given a TOC entry text, find its occurrence in the document body.
    Returns paragraph index or None.
    Patterns from TOC are often abbreviated in body, so use fuzzy matching.
    """
    # Extract key Chinese characters (>2 chars) for matching
    key = re.sub(r'[^\u4e00-\u9fff]', '', toc_text_hint)
    if len(key) < 3:
        return None
    
    for idx, txt in paras:
        if idx < start_from:
            continue
        if idx > start_from + search_range:
            break
        t = txt.strip()
        # Fuzzy: check if most of the key chars appear in order
        if len(key) >= 3:
            # Just check if the key phrase appears
            if key[:4] in t.replace(' ', '').replace('\u0007', ''):
                return idx
    return None
