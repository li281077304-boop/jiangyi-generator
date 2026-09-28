#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm_split.py  ——  T0a LLM 智能拆分（基于目录分类）

新策略:
  1. 提取文档目录项（带真实段落号）
  2. 送目录标题列表给 DeepSeek，让它分类：知识/练习/巩固
  3. 用 LLM 返回的索引映射到真实段落号 → 精确分块

成本: prompt ~300字符, 一次调用 ~¥0.001
"""
import os, json, re, traceback
from typing import List, Dict, Tuple, Optional


# ============================================================
#  配置 & 日志（flash 版：统一走 logger，不再写桌面 api_debug.txt）
# ============================================================
from logger import get_logger
_log = get_logger("llm_split").info

def _get_config(key, default=None):
    if key == "api_key": return os.environ.get("DEEPSEEK_API_KEY", "")
    try:
        from config_manager import config
        return {"base_url":config.llm_base_url,"model":config.llm_model,
                "max_tokens":config.llm_max_tokens,"temperature":config.llm_temperature,
                "timeout":config.llm_timeout}.get(key, default)
    except: pass
    return {"base_url":"https://api.deepseek.com","model":"deepseek-chat",
            "max_tokens":4000,"temperature":0.1,"timeout":60}.get(key, default)


# ============================================================
#  阶段1: 提取目录
# ============================================================
_TOC_LINE = re.compile(r'^(\d{2})\s+\S+')
_KAODIAN = re.compile(r'^考点\s*(\d+)')
_JIAODU = re.compile(r'^角度\s*(\d+)')

def _extract_toc(paras):
    """
    提取目录结构。只取顶层章节（01/02/03/04/05），子章节（考点/角度）不单独列。
    返回: [(段落号, 标题), ...]
    """
    items = []
    for pidx, text in paras:
        t = text.strip()
        if not t: continue
        m = _TOC_LINE.match(t)
        if m:
            name = t[t.index(' ')+1:] if ' ' in t else t
            items.append((pidx, name))
    return items


# ============================================================
#  API 调用
# ============================================================
_llm_audit = get_logger("llm_split.audit")
def _call_deepseek(user_prompt, system_prompt="", max_tokens=200, api_key=""):
    # Flash 1.1 审计哨兵：API_ENABLED=False 时本函数不应被调用。
    # 若日志出现 "!!! LLM API 被调用"，说明有 key 泄漏进了引擎，需立即排查。
    _llm_audit.warning("!!! LLM API 被调用（Flash 1.1 应纯离线，请立即排查）")
    if not api_key: api_key = _get_config("api_key")
    if not api_key: return None
    try: import requests
    except ImportError: return None
    base_url = _get_config("base_url", "https://api.deepseek.com")
    model = _get_config("model", "deepseek-chat")
    messages = []
    if system_prompt: messages.append({"role":"system","content":system_prompt})
    messages.append({"role":"user","content":user_prompt})
    try:
        resp = requests.post(f"{base_url}/v1/chat/completions",
                             headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
                             json={"model":model,"messages":messages,"max_tokens":max_tokens,"temperature":0.05},
                             timeout=_get_config("timeout", 60))
        if resp.status_code != 200:
            _log(f"HTTP {resp.status_code}")
            return None
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        _log(f"请求失败: {e}")
        return None


# ============================================================
#  阶段2: LLM 分类目录标题
# ============================================================
def _classify_toc_with_llm(toc_names, api_key):
    """
    把目录标题列表发给 DeepSeek，返回每个标题的分类索引。
    输入: ["本节导航·目标清单", "教材精研·内容全解", "避坑指南·解题通法", "真题闯关·溯源演练", "课后三阶·精准练习"]
    输出: {"knowledge":[0,1,2],"practice":[3],"consolidation":[4]}
    """
    names_str = "\n".join(f"{i}. {n}" for i, n in enumerate(toc_names))
    
    system_prompt = f"""你是教育讲义分析专家。给定目录（共{len(toc_names)}项），用索引号分类：
- knowledge(知识精讲): 概念讲解、例题、教材精研、方法技巧、避坑
- practice(即时训练): 真题、练习题、闯关
- consolidation(巩固练习): 课后作业、综合练习、后三阶

输出格式（仅JSON）：
{{"knowledge":[0,1,2],"practice":[3],"consolidation":[4]}}
索引号必须覆盖所有{len(toc_names)}项，不重不漏。"""
    
    user_prompt = f"请分类以下目录：\n{names_str}\n\n输出JSON。"
    
    _log(f"发送目录分类: {len(toc_names)}项")
    response = _call_deepseek(user_prompt, system_prompt, max_tokens=200, api_key=api_key)
    if response:
        _log(f"LLM返回: {response[:300]}")
    return response


def _parse_indices(response, n_items):
    """解析 LLM 返回的索引列表，映射到段落号"""
    try:
        m = re.search(r'\{.*\}', response, re.DOTALL)
        data = json.loads(m.group(0)) if m else json.loads(response)
    except:
        return None
    
    result = {}
    for cat in ("knowledge", "practice", "consolidation"):
        indices = data.get(cat, [])
        if isinstance(indices, list):
            result[cat] = [i for i in indices if isinstance(i, int) and 0 <= i < n_items]
    
    # 验证不重不漏
    all_idx = []
    for indices in result.values():
        all_idx.extend(indices)
    if sorted(set(all_idx)) != list(range(n_items)):
        _log(f"索引不完整: 期望0~{n_items-1}，得到{sorted(all_idx)}")
        return None
    
    return result


# ============================================================
#  主入口
# ============================================================
def llm_split(paras, template_type="1v1", api_key=""):
    try: return _impl(paras, template_type, api_key)
    except Exception as e:
        _log(f"✗ 异常: {e}\n{traceback.format_exc()}")
        return None


def _impl(paras, template_type, api_key):
    if not api_key: api_key = _get_config("api_key")
    if not api_key: return None
    
    total = len(paras)
    first = paras[0][0] if paras else 1
    last = paras[-1][0] if paras else 1
    _log(f"全量策略: {total}段 ({first}~{last})")

    # 构建全量文本（每段截150字）
    context = "\n".join(f"[{idx}] {txt[:150]}{'...' if len(txt)>150 else ''}" for idx, txt in paras)
    
    system_prompt = """你是教育讲义分析专家。分析全文，找到知识点讲解区和练习题区的分界点，按标准三块输出。

输出格式（只输出JSON，不要任何解释）：
{
  "blocks": [
    {"type": "knowledge", "start_para": 1},
    {"type": "practice", "start_para": 500},
    {"type": "consolidation", "start_para": 800}
  ]
}

关键识别规则：
1. knowledge(知识精讲): 概念定义、公式定理、例题示范(【例1】等)、考点、角度、方法讲解、教材精研
2. practice(即时训练): 基础训练、基础速刷、真题闯关、对点训练等成对出现的基础练习标记起始处
3. consolidation(巩固练习): 能力跃升、能力提升、提优训练、拔高训练、综合练习、课后三阶等成对出现的能力进阶标记起始处
4. 基础/能力成对标记是关键分界信号——基础标记→即时训练，能力标记→巩固练习
5. 三块按段落号从小到大，start_para必须在文档范围内"""

    user_prompt = f"请分析以下{total}段讲义文档，给出最优的分块方案。\n\n全文:\n{context}\n\n请输出JSON分块方案。"
    
    _log(f"发送全量请求 ({len(user_prompt)}字符)")
    response = _call_deepseek(user_prompt, system_prompt, max_tokens=300, api_key=api_key)
    if not response:
        _log("API未返回")
        return None
    
    _log(f"LLM返回: {response[:300]}")
    
    try:
        m = re.search(r'\{.*\}', response, re.DOTALL)
        data = json.loads(m.group(0)) if m else json.loads(response)
        blocks_raw = data.get("blocks", [])
    except:
        _log("JSON解析失败")
        return None
    
    type_starts = {}
    for b in blocks_raw:
        t, sp = b.get("type"), b.get("start_para")
        if t and sp and isinstance(sp, int):
            type_starts[t] = sp
    _log(f"start_para: {type_starts}")
    
    if len(type_starts) < 2:
        return None
    
    ordered = sorted(type_starts.items(), key=lambda x: x[1])
    ranges = {}
    for i, (bt, sp) in enumerate(ordered):
        ep = ordered[i+1][1]-1 if i+1 < len(ordered) else last
        ranges[bt] = (sp, ep)
    
    _KM = {"1v1": "知识精讲", "class": "知识精讲&例题讲解"}
    _PM = {"1v1": "六、巩固练习", "class": "六、出门测试"}
    
    blocks = []
    for cat, marker in [("knowledge", _KM.get(template_type, "知识精讲")),
                         ("practice", "即时训练"),
                         ("consolidation", _PM.get(template_type, "六、巩固练习"))]:
        if cat in ranges:
            s, e = ranges[cat]
            if e >= s:
                blocks.append({"marker": marker, "start": s, "end": e})
                _log(f"  {marker}: [{s}, {e}]")
    
    _log(f"✓ 完成: {len(blocks)}块")
    return blocks if blocks else None
