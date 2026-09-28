#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hybrid_split.py  ——  T0b 混合拆分方案（规则 + 轻量 NLP）

原理：
  第一阶段：规则粗分 → 对每段打类别+置信度
  第二阶段：语义细分 → 只处理置信度 < 阈值的模糊段落
  第三阶段：后处理   → 知识点边界识别、例题配对、生成最终 blocks

特点：
  - 完全离线，不依赖 API
  - 准确率目标 85-90%（介于 T0a=95% 和 T2=80% 之间）
  - 速度 < 3s / 份讲义
"""
import os
import re
import math
from typing import List, Dict, Tuple, Optional, Any


# ============================================================
#  配置
# ============================================================

# 置信度阈值：低于此值的段落用语义模型二次判断
DEFAULT_CONFIDENCE_THRESHOLD = 70

# 知识点基础分：至少有这么多"知识特征"才能算知识点
MIN_KNOWLEDGE_SIGNALS = 1

# DBSCAN 聚类参数：位置差 <= 此值的段落看作连续
CLUSTER_EPS = 3

# DBSCAN 聚类参数：至少这么多段才算一个有效知识点
CLUSTER_MIN_SAMPLES = 3

# 例题必须在知识点后多少段内
EXAMPLE_PROXIMITY = 20


# ============================================================
#  第一阶段：规则分类器
# ============================================================

# 题型编号正则
_TYPE_NUM_RE = re.compile(r'^【?题型\s*(\d+)')
# 编号题正则（多种格式兼容）
_QNUM_RE = re.compile(r'^\s*(\d{1,3})\s*[.．、)）]\s*\S')
# 年份真题标记
_YEAR_MARK_RE = re.compile(r'[（(]\s*\d{4}\s*[.·]\s*')
# 选择题选项
_CHOICE_RE = re.compile(r'^\s*[A-D]\s*[.．、]')
# 填空括号
_BLANK_RE = re.compile(r'[（(]\s*[）)]\s*$|__+')
# 例题标记
_EXAMPLE_RE = re.compile(r'^【例\s*\d+】|^例\s*\d+\s*[.．]|^【典例】|^【典例精讲】')
# 知识点标题
_KNOWLEDGE_HEADER_RE = re.compile(
    r'^(知识点|考点|知识要点|知识梳理|核心知识|重难点)\s*\d*'
    r'|^[一二三四五六七八九十]+[、.．]\s*\D'
)
# 概念/定义信号词
_CONCEPT_KW = re.compile(r'(定义|公式|性质|定理|法则|概念|原理|规律|方法)')
# 练习区标记
_PRACTICE_HEADER_RE = re.compile(
    r'^(即时训练|巩固练习|课后作业|当堂检测|出门测速|课堂练习|'
    r'随堂检测|达标检测|真题演练|即学即练|变式训练|拓展训练|'
    r'强化训练|综合训练|模拟演练|考前冲刺|限时训练|学以致用)'
)
# 答案/解析标记（归练习区）
_ANSWER_RE = re.compile(r'^【答案与解析】|^【答案】|^【详解】|^【解析】|^【解答】')
# 章节分隔线
_SEP_RE = re.compile(r'^[~/\-_=*#]{10,}\s*$')
# 英文阅读理解标记
_READING_RE = re.compile(r'^【真题再现】')
# 学科网章节号
_XUEKE_SEC = re.compile(r'^0[123]\s+[^\s]+·[^\s]+')   # 知识区
_XUEKE_PRAC = re.compile(r'^0[45]\s+[^\s]+·[^\s]+')    # 练习区
# 短标题判断：<= 20 字且无标点
_SHORT_TITLE_RE = re.compile(r'^.{1,20}$')


def rule_classify_paragraph(text: str,
                             prev_category: str = "",
                             position_ratio: float = 0.5,
                             is_first: bool = False) -> Tuple[str, int]:
    """
    用规则对单段文本分类。

    参数：
        text: 段落文本
        prev_category: 前一段的分类（用于上下文推断）
        position_ratio: 段落位置比例（0-1，越大越靠后）
        is_first: 是否是文档第一段

    返回：
        (category, confidence)
        category: "knowledge" | "example" | "practice" | "other"
        confidence: 0-100
    """
    t = text.strip()
    confidence = 50  # 基础分

    # ── 规则 1：明确标记检测（最高置信度） ───
    # 题型标记
    if _TYPE_NUM_RE.match(t):
        return ("practice", 100)

    # 例题标记
    if _EXAMPLE_RE.search(t):
        return ("example", 100)

    # 总结/归纳标记 → 知识区
    if re.search(r'^(归纳总结|课堂启动|知识回顾|知识小结)', t):
        return ("knowledge", 95)

    # 答案/解析标记
    if _ANSWER_RE.search(t):
        return ("practice", 95)

    # 练习区标题
    if _PRACTICE_HEADER_RE.match(t):
        return ("practice", 95)

    # 知识点标题
    if _KNOWLEDGE_HEADER_RE.match(t):
        # 有概念词 → 几乎确定是知识
        if _CONCEPT_KW.search(t):
            return ("knowledge", 95)
        # 纯标题（短 + 无编号题特征）
        if len(t) < 30 and not _QNUM_RE.match(t):
            return ("knowledge", 90)

    # ── 规则 2：标题检测 ───
    if _SECTION_HEADER_RE.match(t):
        confidence += 30

    # ── 规则 3：题号检测 ───
    if _QNUM_RE.match(t):
        confidence += 30

    # ── 规则 4：选择题/填空题特征 ───
    if _CHOICE_RE.search(t):
        return ("practice", 90)

    if _BLANK_RE.search(t) or re.search(r'（填.*）', t):
        return ("practice", 85)

    # ── 规则 5：概念词密度 ───
    concept_count = len(_CONCEPT_KW.findall(t))
    if concept_count >= 2:
        confidence += 25
    elif concept_count >= 1:
        confidence += 15

    # ── 规则 6：真题年份标记 ───
    if _YEAR_MARK_RE.search(t):
        confidence -= 20  # 真题 → 更像题目

    # ── 规则 7：段落长度 ───
    if len(t) > 200:
        confidence += 10  # 长段落通常是讲解
    elif len(t) < 20:
        confidence -= 10  # 短段落可能是题号/选项

    # ── 规则 8：上下文特征 ───
    if prev_category == "knowledge":
        confidence += 10  # 前面是知识，当前也可能是
    elif prev_category == "practice":
        confidence -= 10  # 前面是练习，当前也可能是

    # ── 规则 9：位置特征 ───
    if position_ratio < 0.3:
        confidence += 5   # 前 30% 更可能是知识
    elif position_ratio > 0.7:
        confidence -= 10  # 后 30% 更可能是练习

    # ── 规则 10：分隔线 → 中立，交由后续逻辑 ───
    if _SEP_RE.match(t):
        return ("other", 100)

    # ── 规则 11：裸空段 ───
    if not t:
        return ("other", 100)

    # ── 分类决策 ───
    confidence = max(0, min(100, confidence))

    # 高位直接判定
    if confidence >= 80:
        return ("knowledge", confidence)
    elif confidence >= 60:
        # 中等置信度：看有没有题目特征
        if _QNUM_RE.match(t) or _CHOICE_RE.search(t) or _BLANK_RE.search(t):
            return ("practice", confidence)
        return ("knowledge", confidence)
    else:
        # 低位 → 模糊，让语义模型处理
        if _QNUM_RE.match(t) or _CHOICE_RE.search(t) or _BLANK_RE.search(t):
            return ("practice", confidence)
        return ("other", confidence)  # "other" = 不确定，后续语义模型处理


# 中文结构标题
_SECTION_HEADER_RE = re.compile(
    r'^[一二三四五六七八九十]+[、.．]'
    r'|^(题型|考点|知识点|专题|Part|Section|Lesson|Unit|'
    r'Read|Passage|Exercise|Practice|Test|Quiz|Cloze|Writing|Grammar)\s*\d*\s*',
    re.I
)


# ============================================================
#  第二阶段：语义细分
# ============================================================

def semantic_classify_batch(uncertain_paras: List[Tuple[int, str]]) -> Dict[int, Tuple[str, float]]:
    """
    用语义模型对一批模糊段落分类。

    参数：
        uncertain_paras: [(段落序号, 文本), ...] 置信度低的段落

    返回：
        {段落序号: (category, similarity)}
    """
    # 尝试加载语义模型
    model = _get_semantic_model()
    if model is None:
        # 降级：语义模型不可用，强行按规则判定
        return _fallback_classify(uncertain_paras)

    from sentence_model import encode_batch, get_template_embeddings, compute_similarities

    # 批量编码段落
    texts = [t for _, t in uncertain_paras]
    embeddings = encode_batch(model, texts)
    if embeddings is None:
        return _fallback_classify(uncertain_paras)

    # 获取模板向量
    tpl_embeddings = get_template_embeddings(model)
    if tpl_embeddings is None:
        return _fallback_classify(uncertain_paras)

    # 逐段计算相似度
    results: Dict[int, Tuple[str, float]] = {}
    for i, (pidx, _) in enumerate(uncertain_paras):
        emb = embeddings[i]
        sims = compute_similarities(emb, tpl_embeddings)
        # 选择最高相似度的类别
        best_cat = max(sims, key=sims.get)
        best_sim = sims[best_cat]
        results[pidx] = (best_cat, best_sim)

    return results


# ============================================================
#  降级分类器（语义模型不可用时）
# ============================================================

def _fallback_classify(uncertain_paras: List[Tuple[int, str]]) -> Dict[int, Tuple[str, float]]:
    """
    语义模型不可用时的降级方案。
    用更激进的规则判定。
    """
    results: Dict[int, Tuple[str, float]] = {}

    for pidx, text in uncertain_paras:
        t = text.strip()

        # 有题号 → 练习
        if _QNUM_RE.match(t):
            results[pidx] = ("practice", 0.8)
        # 有概念词 → 知识
        elif _CONCEPT_KW.search(t):
            results[pidx] = ("knowledge", 0.7)
        # 有选择题特征 → 练习
        elif _CHOICE_RE.search(t) or _BLANK_RE.search(t):
            results[pidx] = ("practice", 0.85)
        # 长段落 → 知识
        elif len(t) > 150:
            results[pidx] = ("knowledge", 0.6)
        # 短段落 → 不确定（根据位置信息后面处理）
        elif len(t) < 20:
            results[pidx] = ("practice", 0.55)  # 短段落更可能是题号/选项
        else:
            results[pidx] = ("knowledge", 0.5)

    return results


# ============================================================
#  语义模型辅助
# ============================================================

_semantic_model: Optional[Any] = None
_semantic_checked: bool = False


def _get_semantic_model() -> Optional[Any]:
    """懒加载语义模型"""
    global _semantic_model, _semantic_checked

    if _semantic_checked:
        return _semantic_model

    _semantic_checked = True

    try:
        from sentence_model import is_model_available, load_model
        if is_model_available():
            _semantic_model = load_model()
    except ImportError:
        pass
    except Exception as e:
        print(f"[hybrid] 语义模型加载异常: {e}")

    return _semantic_model


# ============================================================
#  第三阶段：知识点边界识别
# ============================================================

def detect_knowledge_boundaries(
    paras: List[Tuple[int, str]],
    classifications: Dict[int, Tuple[str, float]]
) -> List[Tuple[int, int]]:
    """
    识别知识点边界。

    算法：
      1. 找连续的 knowledge 段落
      2. 用 DBSCAN 聚类（基于段落位置）
      3. 过滤掉太短的（< 3 段）聚类

    参数：
        paras: [(段落序号, 文本), ...]
        classifications: {段落序号: (类别, 置信度)}

    返回：
        [(start_idx, end_idx), ...] 知识点边界
    """
    # 提取 knowledge 段落的索引（保持原始段落号顺序）
    knowledge_indices = []
    for pidx, _ in sorted(paras, key=lambda x: x[0]):
        cat, conf = classifications.get(pidx, ("other", 0))
        if cat == "knowledge":
            knowledge_indices.append(pidx)

    if len(knowledge_indices) < CLUSTER_MIN_SAMPLES:
        # 知识段落太少，直接当一个大知识块
        if knowledge_indices:
            return [(knowledge_indices[0], knowledge_indices[-1])]
        return []

    # DBSCAN 聚类（基于解析的位置差）
    clusters: List[List[int]] = []
    current_cluster: List[int] = [knowledge_indices[0]]

    for i in range(1, len(knowledge_indices)):
        gap = knowledge_indices[i] - knowledge_indices[i - 1]
        if gap <= CLUSTER_EPS:
            # 连续的知识段落
            current_cluster.append(knowledge_indices[i])
        else:
            # 断开了，新聚类开始
            if len(current_cluster) >= CLUSTER_MIN_SAMPLES:
                clusters.append(current_cluster)
            current_cluster = [knowledge_indices[i]]

    # 最后一个聚类
    if len(current_cluster) >= CLUSTER_MIN_SAMPLES:
        clusters.append(current_cluster)

    # 转换为边界
    boundaries = [(cl[0], cl[-1]) for cl in clusters]

    return boundaries


# ============================================================
#  例题配对
# ============================================================

def pair_examples_with_knowledge(
    knowledge_blocks: List[Tuple[int, int]],
    classifications: Dict[int, Tuple[str, float]],
    paras: List[Tuple[int, str]]
) -> Dict[int, Optional[int]]:
    """
    为每个知识点配对一道例题。

    配对规则：
      1. 例题必须在知识点后 EXAMPLE_PROXIMITY 段内
      2. 每个知识点最多配 1 道例题
      3. 优先配距离最近的例题

    参数：
        knowledge_blocks: 知识点边界列表
        classifications: 段落分类结果
        paras: 段落列表

    返回：
        {knowledge_block_index: example_position or None}
    """
    # 收集所有 example 段落位置
    example_positions = []
    for pidx, cat_conf in classifications.items():
        cat, _ = cat_conf
        if cat == "example":
            example_positions.append(pidx)

    example_positions.sort()

    result: Dict[int, Optional[int]] = {}
    assigned_examples: set = set()  # 已配对的例题

    for kb_idx, (kb_start, kb_end) in enumerate(knowledge_blocks):
        best_example = None
        best_distance = EXAMPLE_PROXIMITY + 1

        for ep in example_positions:
            if ep in assigned_examples:
                continue
            if ep < kb_end:
                continue  # 例题必须在知识点之后
            dist = ep - kb_end
            if dist <= EXAMPLE_PROXIMITY and dist < best_distance:
                best_example = ep
                best_distance = dist

        if best_example is not None:
            result[kb_idx] = best_example
            assigned_examples.add(best_example)
        else:
            result[kb_idx] = None

    return result


# ============================================================
#  生成最终 blocks
# ============================================================

def build_final_blocks(
    paras: List[Tuple[int, str]],
    classifications: Dict[int, Tuple[str, float]],
    knowledge_blocks: List[Tuple[int, int]],
    example_pairs: Dict[int, Optional[int]],
    template_type: str = "1v1"
) -> List[Dict]:
    """
    生成最终的 blocks 列表。

    策略：
      1. 知识精讲 = 所有 knowledge + example 段落
      2. 即时训练 = practice 的前 70%
      3. 巩固练习 = practice 的后 30%

    参数：
        paras: 段落列表
        classifications: 分类结果
        knowledge_blocks: 知识点边界
        example_pairs: 例题配对
        template_type: 模板类型

    返回：
        blocks 列表
    """
    _KM = {"1v1": "知识精讲", "class": "知识精讲&例题讲解"}
    _PM = {"1v1": "六、巩固练习", "class": "六、出门测试"}
    k_marker = _KM.get(template_type, "知识精讲")
    p_marker = _PM.get(template_type, "六、巩固练习")

    if not paras:
        return []

    first = paras[0][0]
    last = paras[-1][0]

    # ── 收集所有 practice 段落 ──
    practice_indices = []
    for pidx, cat_conf in sorted(classifications.items()):
        cat, _ = cat_conf
        if cat == "practice":
            practice_indices.append(pidx)

    # ── 收集所有 knowledge + example 段落的范围 ──
    knowledge_indices: List[int] = []
    for pidx, cat_conf in sorted(classifications.items()):
        cat, _ = cat_conf
        if cat in ("knowledge", "example"):
            knowledge_indices.append(pidx)

    # ── 确定知识精讲范围：第一个 knowledge 到最后一个 knowledge+example ──
    if knowledge_indices:
        k_start = knowledge_indices[0]
        k_end = knowledge_indices[-1]
        # 取第一个 classified 段和 knowledge_end 中较大的那个
        classified_indices = sorted(classifications.keys())
        if classified_indices:
            k_start = classified_indices[0]  # 第一段即使未分类也算
    else:
        # 没有明确的知识段落，取前 30%
        span = last - first
        k_start = first
        k_end = first + int(span * 0.3)

    # ── 确定练习区范围 ──
    if practice_indices:
        p_start = practice_indices[0]
        p_end = practice_indices[-1]
    else:
        # 没有明确练习段落，知识精讲后面就是练习
        p_start = k_end + 1
        p_end = last

    # 确保不重叠：练习区必须在知识区之后
    p_start = max(p_start, k_end + 1)
    # 如果 p_start 被推到 last 之后了，说明没有练习区，全是知识
    if p_start > last:
        p_start = last
        p_end = last
    # 如果 p_start 被调整了，p_end 也要同步
    if p_end < p_start:
        p_end = last

    # ── 题目区 70/30 切分（在 p_start/p_end 确定之后） ──
    # 只取知识区之后的 practice 段落（前面可能有少量被误判的）
    practice_after = [pi for pi in practice_indices if pi >= max(k_end + 1, first)]
    if len(practice_after) >= 3:
        n = len(practice_after)
        cut = max(1, int(round(n * 0.7)))
        if cut < n:
            train_end = practice_after[cut] - 1
        else:
            train_end = p_end
    else:
        # practice 段落太少或没有 → 从知识区之后直接按总段落数 70/30 切
        total_practice_span = last - max(k_end + 1, first)
        if total_practice_span <= 0:
            # 没有练习区可切，即时训练和巩固练习都为空
            train_end = last
            p_start = last + 1  # 确保 start > end，后面 block 变为空
            p_end = last
        else:
            train_end = max(k_end + 1, first) + int(total_practice_span * 0.7)
            train_end = min(train_end, last)
            p_start = max(k_end + 1, first)
            p_end = last

    # ── 组装 blocks ──
    blocks = []

    # 知识精讲
    if k_end >= k_start:
        blocks.append({"marker": k_marker, "start": k_start, "end": k_end})
    else:
        blocks.append({"marker": k_marker, "start": 1, "end": 0})

    # 即时训练
    train_end = min(train_end, p_end, last)  # 确保不越界
    if train_end >= p_start and p_start <= last:
        blocks.append({"marker": "即时训练", "start": p_start, "end": train_end})
    else:
        blocks.append({"marker": "即时训练", "start": 1, "end": 0})

    # 巩固练习（紧接即时训练之后，绝不重叠）
    cons_start = train_end + 1
    if cons_start <= last and cons_start > train_end:
        blocks.append({"marker": p_marker, "start": min(train_end + 1, last), "end": last})
    else:
        blocks.append({"marker": p_marker, "start": last, "end": last})

    return blocks


# ============================================================
#  主入口
# ============================================================

def hybrid_split(
    paras: List[Tuple[int, str]],
    template_type: str = "1v1",
    confidence_threshold: int = DEFAULT_CONFIDENCE_THRESHOLD
) -> Optional[List[Dict]]:
    """
    T0b 混合拆分方案。

    流程：
      第一阶段：规则粗分（对每段打类别+置信度）
      第二阶段：语义细分（只处理置信度 < 阈值的模糊段落）
      第三阶段：后处理（知识点边界 + 例题配对 + 生成 blocks）

    参数：
        paras: [(段落序号, 文本), ...]
        template_type: "1v1" 或 "class"
        confidence_threshold: 置信度阈值

    返回：
        blocks 列表，失败返回 None
    """
    total = len(paras)
    if total == 0:
        return None

    print(f"[hybrid] T0b 混合拆分启动（共 {total} 段）")

    # ── 第一阶段：规则粗分 ──
    print(f"[hybrid] 第一阶段：规则粗分...")
    rule_results: Dict[int, Tuple[str, int]] = {}
    uncertain: List[Tuple[int, str]] = []
    prev_cat = ""

    for i, (pidx, text) in enumerate(paras):
        pos_ratio = i / max(total - 1, 1)
        cat, conf = rule_classify_paragraph(
            text,
            prev_category=prev_cat,
            position_ratio=pos_ratio,
            is_first=(i == 0)
        )
        rule_results[pidx] = (cat, conf)

        if cat == "other" or conf < confidence_threshold:
            uncertain.append((pidx, text))
        else:
            prev_cat = cat

    determined = total - len(uncertain)
    print(f"[hybrid]   确定: {determined} 段, 模糊: {len(uncertain)} 段")

    # ── 第二阶段：语义细分 ──
    classifications: Dict[int, Tuple[str, float]] = {}

    # 先把确定的分类放进去
    for pidx, (cat, conf) in rule_results.items():
        if cat != "other" and conf >= confidence_threshold:
            # 转为 0-1 的置信度（原为 0-100）
            classifications[pidx] = (cat, min(1.0, conf / 100.0))

    # 对模糊段落用语义模型
    if uncertain:
        print(f"[hybrid] 第二阶段：语义细分（{len(uncertain)} 段）...")
        sem_results = semantic_classify_batch(uncertain)

        for pidx, (cat, sim) in sem_results.items():
            classifications[pidx] = (cat, sim)
    else:
        print(f"[hybrid] 第二阶段：无需语义细分（全部确定）")

    # ── 第三阶段 A：知识点边界 ──
    print(f"[hybrid] 第三阶段A：知识点边界识别...")
    knowledge_blocks = detect_knowledge_boundaries(paras, classifications)
    print(f"[hybrid]   知识点: {len(knowledge_blocks)} 个")

    # ── 第三阶段 B：例题配对 ──
    example_pairs = pair_examples_with_knowledge(
        knowledge_blocks, classifications, paras
    )
    paired = sum(1 for v in example_pairs.values() if v is not None)
    print(f"[hybrid] 第三阶段B：例题配对: {paired}/{len(example_pairs)}")

    # ── 第三阶段 C：生成最终 blocks ──
    print(f"[hybrid] 第三阶段C：生成 blocks...")
    blocks = build_final_blocks(
        paras, classifications, knowledge_blocks, example_pairs, template_type
    )

    print(f"[hybrid] ✓ T0b 混合拆分完成，生成 {len(blocks)} 个块")
    return blocks


# ============================================================
#  自测
# ============================================================

def _demo_test():
    """演示：不依赖真实 docx 文件的自测"""
    print("=== hybrid_split 演示测试 ===\n")

    # 模拟一段讲义的段落
    test_paras = [
        (1, "知识梳理"),
        (2, "1. 集合的概念：具有某种特定性质的对象的总体。"),
        (3, "2. 确定性：一个对象要么属于这个集合，要么不属于。"),
        (4, "3. 互异性：集合中的元素是互不相同的。"),
        (5, "【例1】判断以下对象能否构成集合："),
        (6, "(1) 大于3小于11的偶数；"),
        (7, "(2) 我国的小河流。"),
        (8, "【解析】(1) 能构成集合，因为元素是确定的。"),
        (9, "题型1 集合的基本概念"),
        (10, "1. （2024·北京）下列各组对象中能构成集合的是（  ）"),
        (11, "A. 著名的数学家  B. 接近0的数"),
        (12, "C. 2024年世界杯参赛队  D. 某校的高个子学生"),
        (13, "2. 若集合A={1,3}，则A的子集个数为（  ）"),
        (14, "A. 2  B. 3  C. 4  D. 8"),
        (15, "3. 设全集U={1,2,3,4,5}，集合A={1,2,3}，则∁UA=（  ）"),
        (16, "A. {4,5}  B. {1,2,3}  C. {5}  D. {1,2,3,4,5}"),
        (18, "5. 用列举法表示下列集合："),
        (19, "(1) 方程x²-3x+2=0的解集；"),
        (20, "(2) 大于0且小于10的奇数。"),
    ]

    result = hybrid_split(test_paras)

    if result:
        print(f"\n结果:")
        for blk in result:
            m = blk.get("marker", "?")
            s = blk.get("start", 0)
            e = blk.get("end", 0)
            print(f"  {m}: {s}-{e} ({e - s + 1} 段)")
    else:
        print("✗ 拆分失败")

    print(f"\n=== 演示测试完成 ===")


if __name__ == "__main__":
    _demo_test()
