# -*- coding: utf-8 -*-
"""
config.py —— 统一配置管理

职责：
  1. 集中定义应用路径常量（模板、PS1 脚本、输出目录）
  2. 读写运行配置（webapp/config.json：API Key、默认学科）

设计约定：
  - 本模块是"路径与配置的唯一事实来源"，其他模块不得自行拼路径。
  - config.json 仍在 webapp/ 下，与旧版兼容，前端设置页面读写同一文件。
"""
import os
import json

# ------------------------------------------------------------
# 路径常量
# ------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))          # res/app
CONFIG_PATH = os.path.join(APP_DIR, "webapp", "config.json")   # 运行配置

DEFAULT_TEMPLATE = os.path.join(APP_DIR, "2025+1v1讲义模板(2).docx")  # 1v1 模板
CLASS_TEMPLATE = os.path.join(APP_DIR, "2025班课模板.doc")            # 班课模板

PS_FILL_1V1 = os.path.join(APP_DIR, "_fill_com.ps1")            # 1v1 模板填充
PS_FILL_CLASS = os.path.join(APP_DIR, "_fill_class.ps1")        # 班课模板填充
PS_SCAN = os.path.join(APP_DIR, "_scan_com.ps1")                # 段落扫描
PS_ADD_BLANKS = os.path.join(APP_DIR, "_add_blanks_com.ps1")    # 简答题留白
PS_STRIP_ANSWER = os.path.join(APP_DIR, "_strip_answer_com.ps1")  # 删答案标记段
PS_EXPORT_PDF = os.path.join(APP_DIR, "_export_pdf_com.ps1")    # PDF 导出
PS_IDEALIZE = os.path.join(APP_DIR, "_idealize_com.ps1")        # 整理模式：抽例题
PS_RENUMBER = os.path.join(APP_DIR, "_renumber_com.ps1")        # 整理模式：题号重编

LOG_DIR = os.path.join(APP_DIR, "logs")                         # 统一日志目录

# ------------------------------------------------------------
# 功能开关
# ------------------------------------------------------------
# Flash 1.1：停用云端 API（DeepSeek / LLM 拆分 / AI 生成目标）。
# 全程离线运行，不上传任何文档内容。置 True 可恢复（仅用于开发调试）。
API_ENABLED = False

# ------------------------------------------------------------
# 配置读写
# ------------------------------------------------------------
DEFAULT_CONFIG = {"api_key": "", "subject": "数学"}


def load_config() -> dict:
    """读取运行配置；文件缺失/损坏时返回默认值。"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                return cfg
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    """保存运行配置。"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
