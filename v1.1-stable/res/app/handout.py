#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
handout.py —— 讲义生成器 · 命令行入口

三种用法：

1) 简单模式：整份源文档全贴进「知识精讲」，其余留空
   python handout.py simple 教师版.docx 学生版.docx "专题名"

2) 方案模式：执行 plan.json（支持任意学科/任意分块）
   python handout.py plan plan.json

3) 扫描模式：查看一份文档的段落结构（供决定分块范围）
   python handout.py scan 某文档.docx
   python handout.py scan 某文档.docx --grep "题型|Lesson|Unit"

──────────────────────────────────────────────
模块职责一览（flash 版重构后）：
  config.py       路径与配置唯一事实来源
  logger.py       统一日志（logs/ 目录，不再写桌面）
  docutils.py     段落扫描 / 主题提取 / 文件名
  objectives.py   教学目标与重难点生成
  student_ops.py  学生版加工（去红色答案/删标记/留白）
  runner.py       PowerShell 执行 + 生成编排
  split_engine.py 智能拆分引擎（四层降级）
  webapp/         Flask 后端（app.py 路由 + jobs.py 任务）
"""
import argparse
import os
import re
import sys
import json

import config
import docutils
import objectives
import runner
import student_ops
import logger

log = logger.get_logger("handout")

# ------------------------------------------------------------
# 兼容导出（供 webapp 及外部脚本使用旧接口）
# ------------------------------------------------------------
DEFAULT_TEMPLATE = config.DEFAULT_TEMPLATE
CLASS_TEMPLATE = config.CLASS_TEMPLATE
make_objectives = objectives.make_objectives
make_student = student_ops.make_student
_body_paragraphs = docutils.body_paragraphs    # 旧名兼容
extract_topic = docutils.extract_topic
build_filename = docutils.build_filename
run_plan = runner.run_plan
build_version = runner.build_version


# ============================================================
#  模式 1：简单（全贴知识精讲）
# ============================================================
def cmd_simple(args):
    template = config.DEFAULT_TEMPLATE
    versions = []
    for label, src in [("教师版", args.teacher), ("学生版", args.student)]:
        src = os.path.abspath(src)
        if not os.path.exists(src):
            sys.exit(f"[错误] 缺文件: {src}")
        total = docutils.para_count(src)
        versions.append({
            "label": label, "source": src,
            "output": os.path.join(args.out_dir, f"{args.topic}-{label}.docx"),
            "topic": args.topic, "objectives": args.objectives, "difficulties": args.difficulties,
            "blocks": [{"marker": "知识精讲", "start": 1, "end": total}],
        })
        print(f"[{label}] 段落总数 {total} → 全部进知识精讲")
    run_plan({"versions": versions}, template)
    _report(versions)


# ============================================================
#  模式 2：方案（plan.json）
# ============================================================
def cmd_plan(args):
    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)
    template = plan.get("template", config.DEFAULT_TEMPLATE)
    if not os.path.isabs(template):
        template = os.path.join(config.APP_DIR, template)
    run_plan(plan, template)
    _report(plan["versions"])


# ============================================================
#  模式 3：扫描结构
# ============================================================
def cmd_scan(args):
    paras = docutils.body_paragraphs(args.docx)
    print(f"总段落: {len(paras)}")
    pat = re.compile(args.grep) if args.grep else None
    for idx, txt in paras:
        if pat:
            if pat.search(txt):
                print(f"[{idx}] {txt[:80]}")
        elif txt:
            if idx <= args.head or len(txt) < 50:
                print(f"[{idx}] {txt[:80]}")


def _report(versions):
    print("\n完成:")
    for v in versions:
        out = os.path.abspath(v["output"])
        mb = os.path.getsize(out) / 1024**2 if os.path.exists(out) else 0
        print(f"  {os.path.basename(out)}  {mb:.1f}MB")


def main():
    ap = argparse.ArgumentParser(description="讲义生成执行器")
    sub = ap.add_subparsers(dest="mode", required=True)

    s = sub.add_parser("simple", help="整份贴进知识精讲")
    s.add_argument("teacher"); s.add_argument("student"); s.add_argument("topic")
    s.add_argument("--objectives", default=""); s.add_argument("--difficulties", default="")
    s.add_argument("--out-dir", default=config.APP_DIR)
    s.set_defaults(func=cmd_simple)

    p = sub.add_parser("plan", help="执行 plan.json")
    p.add_argument("plan")
    p.set_defaults(func=cmd_plan)

    c = sub.add_parser("scan", help="查看文档段落结构")
    c.add_argument("docx"); c.add_argument("--grep", default="")
    c.add_argument("--head", type=int, default=0)
    c.set_defaults(func=cmd_scan)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
