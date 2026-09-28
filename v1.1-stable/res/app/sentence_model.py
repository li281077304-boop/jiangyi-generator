#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sentence_model.py  ——  语义模型封装（T0b 混合拆分组件）

功能：
  - 加载 sentence-transformers 模型
  - 文本编码（向量化）
  - 相似度计算
  - 模型可用性检查

模型：
  paraphrase-multilingual-MiniLM-L12-v2（120MB, 支持中文）
  首次使用自动下载到 ~/.cache/torch/sentence_transformers/
"""
import os
from typing import Optional, Any, List

# numpy 延迟导入（避免模块级加载失败阻塞整个模块）
_np = None

def _get_np():
    """延迟加载 numpy"""
    global _np
    if _np is not None:
        return _np
    try:
        import numpy as _numpy
        _np = _numpy
        return _np
    except ImportError as e:
        print(f"[model] numpy 不可用: {e}")
        return None


# ============================================================
#  模型配置
# ============================================================
DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# 预定义分类模板（用于语义匹配）
CATEGORY_TEMPLATES = {
    "knowledge": [
        "这是一个数学概念的定义",
        "下面介绍公式和性质",
        "知识点讲解和说明",
        "定理的证明过程",
        "基本概念和原理",
        "知识梳理和总结",
        "考点分析和归纳",
    ],
    "example": [
        "这是一道例题",
        "典型例题的解答过程",
        "实际应用举例",
        "例题分析和讲解",
        "示范题目和详解",
        "典例精讲",
    ],
    "practice": [
        "这是一道练习题",
        "巩固训练题目",
        "课后习题和测试",
        "真题演练",
        "随堂检测题目",
        "选择题和填空题",
    ],
}

# 全局模型缓存（单例）
_model_cache: Optional[Any] = None
_model_available: Optional[bool] = None  # None=未检测, True/False


# ============================================================
#  模型管理
# ============================================================

def is_model_available() -> bool:
    """
    检查 sentence-transformers 模型是否可用。

    返回：
        True: 模型已安装且可加载
        False: 模型不可用
    """
    global _model_available
    if _model_available is not None:
        return _model_available

    try:
        import sentence_transformers
        # 尝试加载模型（不缓存，只检测）
        _model_available = True
    except ImportError:
        _model_available = False
        print("[model] sentence-transformers 未安装，语义模型不可用（可 pip install sentence-transformers）")

    return _model_available


def load_model(model_name: Optional[str] = None) -> Optional[Any]:
    """
    加载 sentence-transformers 模型。

    参数：
        model_name: 模型名称，None 使用默认模型

    返回：
        模型对象，失败返回 None
    """
    global _model_cache

    if _model_cache is not None:
        return _model_cache

    if not is_model_available():
        return None

    name = model_name or DEFAULT_MODEL_NAME

    try:
        from sentence_transformers import SentenceTransformer
        print(f"[model] 正在加载语义模型: {name}（首次使用会下载 ~120MB）...")
        _model_cache = SentenceTransformer(name)
        print(f"[model] ✓ 语义模型加载成功")
        return _model_cache
    except Exception as e:
        print(f"[model] 模型加载失败: {e}")
        _model_available_val: bool = False
        return None


def get_model() -> Optional[Any]:
    """获取缓存的模型，未加载则加载"""
    if _model_cache is not None:
        return _model_cache
    return load_model()


# ============================================================
#  文本编码
# ============================================================

def encode_text(model: Any, text: str) -> Optional[Any]:
    """
    将文本编码为向量。

    参数：
        model: sentence-transformers 模型
        text: 需要编码的文本

    返回：
        768 维向量（numpy array），失败返回 None
    """
    if model is None:
        return None
    try:
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding
    except Exception as e:
        print(f"[model] 编码失败: {e}")
        return None


def encode_batch(model: Any, texts: List[str]) -> Optional[Any]:
    """
    批量编码文本（比逐条编码快）。

    参数：
        model: sentence-transformers 模型
        texts: 文本列表

    返回：
        (N, 768) 的向量矩阵，失败返回 None
    """
    if model is None:
        return None
    try:
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings
    except Exception as e:
        print(f"[model] 批量编码失败: {e}")
        return None


# ============================================================
#  相似度计算
# ============================================================

def cosine_similarity(vec1, vec2) -> float:
    """
    计算两个向量的余弦相似度。

    参数：
        vec1: 向量 1（768 维，numpy array 或 torch tensor）
        vec2: 向量 2（768 维）

    返回：
        0-1 的相似度（越接近 1 越相似）
    """
    try:
        from sentence_transformers import util
        # util.cos_sim 返回 torch.Tensor（2D），取 [0,0] 元素
        sim = util.cos_sim(vec1, vec2)
        if hasattr(sim, 'item'):
            val = float(sim.item())
        else:
            val = float(sim[0][0]) if len(sim.shape) > 1 else float(sim)
        return max(0.0, min(1.0, val))  # 确保在 [0, 1] 范围内
    except Exception:
        # 降级到 numpy 手动计算
        np = _get_np()
        if np is None:
            return 0.0
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(max(0.0, dot / (norm1 * norm2)))


def compute_similarities(embedding, template_embeddings: dict) -> dict:
    """
    计算文本向量与各类模板的最大相似度。

    参数：
        embedding: 文本的 768 维向量
        template_embeddings: {"knowledge": [vec1, vec2, ...], "example": [...], ...}

    返回：
        {"knowledge": 0.85, "example": 0.32, "practice": 0.45}
    """
    result = {}
    for category, tpl_vecs in template_embeddings.items():
        if not tpl_vecs:
            result[category] = 0.0
            continue
        # 取与所有模板中最大的相似度
        sims = [cosine_similarity(embedding, tv) for tv in tpl_vecs]
        result[category] = max(sims) if sims else 0.0
    return result


# ============================================================
#  模板编码（预计算，一次编码重复使用）
# ============================================================

_template_embeddings_cache: Optional[dict] = None


def get_template_embeddings(model: Any) -> Optional[dict]:
    """
    获取预编码的分类模板向量。
    首次调用编码，后续从缓存读取。

    返回：
        {"knowledge": [vec1, vec2, ...], "example": [...], "practice": [...]}
    """
    global _template_embeddings_cache

    if _template_embeddings_cache is not None:
        return _template_embeddings_cache

    if model is None:
        return None

    print("[model] 预编码分类模板...")
    _template_embeddings_cache = {}

    for category, templates in CATEGORY_TEMPLATES.items():
        vecs = []
        for t in templates:
            v = encode_text(model, t)
            if v is not None:
                vecs.append(v)
        _template_embeddings_cache[category] = vecs
        print(f"[model]   {category}: {len(vecs)} 条模板")

    return _template_embeddings_cache


# ============================================================
#  便捷接口
# ============================================================

def classify_by_semantic(text: str, model: Any = None) -> Optional[tuple]:
    """
    用语义模型对单段文本分类。

    参数：
        text: 段落文本
        model: 模型对象（可选，None 自动加载）

    返回：
        (category, similarity)
        category: "knowledge" | "example" | "practice"
        similarity: 0-1 的相似度
        失败返回 None
    """
    m = model or get_model()
    if m is None:
        return None

    # 编码文本
    embedding = encode_text(m, text)
    if embedding is None:
        return None

    # 获取模板向量
    tpl_embeddings = get_template_embeddings(m)
    if tpl_embeddings is None:
        return None

    # 计算相似度
    sims = compute_similarities(embedding, tpl_embeddings)

    # 选择最高相似度的类别
    best_category = max(sims, key=sims.get)
    best_similarity = sims[best_category]

    return (best_category, best_similarity)


# ============================================================
#  自测
# ============================================================

def _self_test():
    """自测语义模型功能"""
    print("=== sentence_model 自测 ===\n")

    # 1) 检查可用性
    print(f"1. 模型可用: {is_model_available()}")

    if not is_model_available():
        print("   [跳过] 模型未安装，执行 pip install sentence-transformers")
        return

    # 2) 加载模型
    model = load_model()
    print(f"2. 模型加载: {'✓' if model else '✗'}")

    if model is None:
        return

    # 3) 编码测试
    texts = [
        "集合的定义：具有某种特定性质的对象的总体",
        "例1. 判断以下对象能否构成集合",
        "1. （2024·北京）设集合 A = {1,2,3}，则 A 的子集个数是",
    ]

    print(f"3. 编码测试:")
    for text in texts:
        vec = encode_text(model, text)
        print(f"   [{len(text)}字] shape={vec.shape if vec is not None else 'None'}")

    # 4) 分类测试
    print(f"\n4. 分类测试:")
    for text in texts:
        result = classify_by_semantic(text, model)
        if result:
            cat, sim = result
            print(f"   [{cat:12s}] sim={sim:.3f} | {text[:40]}...")
        else:
            print(f"   [失败] {text[:40]}...")

    # 5) 模板预编码
    print(f"\n5. 模板预编码:")
    tpl = get_template_embeddings(model)
    if tpl:
        for cat, vecs in tpl.items():
            print(f"   {cat}: {len(vecs)} 条模板")

    print(f"\n=== 自测完成 ===")


if __name__ == "__main__":
    _self_test()
