# -*- coding: utf-8 -*-
"""
objectives.py —— 教学目标与重难点生成

两条路径：
  1. AI 生成（gen_objectives）：配置了 DeepSeek API Key 时使用，基于文档内容摘要
  2. 离线模板（gen_objectives_local）：不联网，从段落里提取知识章节/题型/题数，
     生成有针对性而非纯套话的目标

统一入口：make_objectives(subject, topic, api_key, paras, use_local=True)
"""
import re

from split_engine import (
    TYPE_RE, NUM_RE, _KNOWLEDGE_SECTION_RE, _ORDERED_HEADER_RE,
)
import logger

log = logger.get_logger("objectives")


def gen_objectives(subject, topic, api_key, paras=None):
    """有 API Key 时调 DeepSeek 生成教学目标+重难点（基于文档实际内容）"""
    if not api_key:
        return "", ""

    # 取前 150 段作为内容样本
    sample = ""
    if paras:
        lines = []
        for idx, txt in paras[:150]:
            t = txt.strip()[:100]
            if t:
                lines.append(t)
        sample = "\n".join(lines)

    prompt = f"""为{subject}专题「{topic}」的讲义写教学目标与重难点。请根据以下文档内容摘要，生成有针对性的描述。

文档内容摘要：
{sample[:3000]}

要求（严格按格式输出）：
【教学目标】
①（明确的知识目标，基于文档内容描述）
②（能力目标，基于文档中的题型和训练要求）
③（素养目标）

【重点难点】
重点：...
难点：..."""

    try:
        import requests
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 500, "temperature": 0.3},
            timeout=30)
        if resp.status_code != 200:
            log.warning("API 错误: %s", resp.status_code)
            return "", ""
        text = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.warning("AI 生成失败: %s", e)
        return "", ""

    obj = re.search(r'【教学目标】\s*(.*?)(?=【|$)', text, re.S)
    diff = re.search(r'【重点难点】\s*(.*)', text, re.S)
    return (obj.group(1).strip() if obj else ""), (diff.group(1).strip() if diff else "")


def gen_objectives_local(subject, topic, paras=None):
    """
    离线生成教学目标+重难点（不联网、不需 API）。

    算法：
      1) 扫描段落提取三类信息：知识章节标题 / 题型标题 / 编号题目数
      2) 用知识章节丰富"学什么"描述
      3) 用题型标题+题目总数丰富"练什么"描述
    """
    knowledge_titles = []   # 知识章节名（如"集合的定义"）
    type_titles = []        # 题型名（如"集合的判定"）
    practice_tags = []      # 实践板块标记（基础速刷/能力跃升等，仅备用）
    question_count = 0      # 编号题目总数
    example_count = 0       # 例题数（例1、例2…）
    seen_q1 = False

    if paras:
        for _, txt in paras:
            t = txt.strip()
            if not t:
                continue

            # ——题型标题——（剥掉【题型N】前缀与括号，只留核心名，如"求一个数的算术平方根"）
            m = TYPE_RE.match(t)
            if m:
                name = re.sub(r'^【?\s*题型\s*\d+\s*】?\s*', '', t).strip('【】').strip()
                if name and len(name) < 30 and name not in type_titles:
                    type_titles.append(name)
                continue

            # ——知识章节标题——
            m = _KNOWLEDGE_SECTION_RE.match(t)
            if m:
                name = _KNOWLEDGE_SECTION_RE.sub('', t).strip().lstrip('：:、 ')
                if name and len(name) < 30 and name not in knowledge_titles:
                    knowledge_titles.append(name)
                continue

            # ——有序号知识标题（一、xxx），排除题型/练习区——
            m2 = _ORDERED_HEADER_RE.match(t)
            if m2:
                name = m2.group(1).strip()
                exclude_kw = ('题型', '练习', '训练', '巩固', '测试')
                if name and not any(kw in name for kw in exclude_kw):
                    if len(name) < 30 and name not in knowledge_titles:
                        knowledge_titles.append(name)
                continue

            # ——编号题目统计——
            m3 = NUM_RE.match(t)
            if m3:
                num = int(m3.group(1))
                if num == 1 and not seen_q1:
                    seen_q1 = True
                    question_count += 1
                elif num == question_count + 1:
                    question_count += 1
                continue

            # ——例题统计——
            if re.match(r'^例\s*\d+', t):
                example_count += 1

            # ——v1.0: 实践板块标记（基础速刷/能力跃升/真题闯关等）——仅备用，不混入题型名
            practice_markers = ['基础速刷', '能力跃升', '能力提升', '提优训练', '拔高训练',
                              '真题闯关', '课后三阶', '对点训练', '即学即练', '变式训练',
                              '拓展训练', '强化训练', '综合训练', '模拟演练']
            for pm in practice_markers:
                if pm in t:
                    if pm not in practice_tags:
                        practice_tags.append(pm)
                    break

    # 去重 & 限数量（凝练版：知识 3 个、题型 3 个，控制总字数）
    knowledge_titles = list(dict.fromkeys(knowledge_titles))[:3]
    type_titles = list(dict.fromkeys(type_titles))[:3]
    practice_tags = list(dict.fromkeys(practice_tags))[:2]

    # ———— 生成教学目标（每条 ≤ 45 字，总 ≤ 130 字） ————

    # ① 知识目标
    if knowledge_titles:
        obj1 = f"①掌握{topic}核心知识：{'、'.join(knowledge_titles)}等；"
    else:
        obj1 = f"①掌握{topic}的核心概念与基本方法；"

    # ② 能力目标（题型只列前 3；用"掌握…解法"避免与题型名开头的"求"字重复）
    q_names = type_titles or practice_tags
    if q_names:
        q_part = "、".join(q_names) + "等"
    else:
        q_part = "本专题典型问题"
    if question_count > 0:
        obj2 = f"②掌握{q_part}题型的解法，共{question_count}道题；"
    else:
        obj2 = f"②掌握{q_part}题型的解法，熟练求解；"

    # ③ 综合素养
    obj3 = "③培养运算与推理能力，形成知识体系。"

    objectives = "\n".join([obj1, obj2, obj3])

    # ———— 生成重点难点（各 ≤ 45 字） ————
    if knowledge_titles:
        diff_key = f"重点：{topic}核心概念（{'、'.join(knowledge_titles[:2])}）的理解与应用；"
    else:
        diff_key = f"重点：{topic}核心知识点与基本方法；"
    if q_names:
        diff_hard = f"难点：{q_part}的综合运用与易错点辨析。"
    else:
        diff_hard = "难点：知识的综合运用与易错点辨析。"

    difficulties = f"{diff_key}\n{diff_hard}"

    return objectives, difficulties


def make_objectives(subject, topic, api_key="", paras=None, use_local=True):
    """统一入口：有 Key 用 AI；否则（且 use_local）用离线模板；都不满足则留白"""
    if api_key:
        obj, diff = gen_objectives(subject, topic, api_key, paras=paras)
        if obj or diff:
            return obj, diff
    if use_local:
        return gen_objectives_local(subject, topic, paras)
    return "", ""
