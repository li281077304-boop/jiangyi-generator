# -*- coding: utf-8 -*-
"""
logger.py —— 统一日志

旧版问题：app.py / llm_split.py 各自往「桌面 api_debug.txt」写调试日志，
桌面被污染，且不同模块日志格式不统一。

本模块：所有模块统一走 get_logger()，输出到 res/app/logs/ 下的滚动文件，
同时打印到控制台。不再向桌面写任何文件。
"""
import os
import logging
from logging.handlers import RotatingFileHandler

import config

_configured = False


def _setup_root():
    """初始化根日志器：控制台 + 滚动文件（10MB x 3），只执行一次。"""
    global _configured
    if _configured:
        return
    _configured = True

    os.makedirs(config.LOG_DIR, exist_ok=True)
    log_file = os.path.join(config.LOG_DIR, "handout.log")

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)


def get_logger(name: str = "app") -> logging.Logger:
    """获取带模块名的日志器。首次调用时自动完成全局初始化。"""
    _setup_root()
    return logging.getLogger(name)
