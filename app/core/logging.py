import logging
import os
from logging.handlers import TimedRotatingFileHandler


def setup_logging(log_dir="logs", log_file="app.log", backup_count=7):
    """根据配置初始化根 logger (文件 + 控制台)。仅执行一次。"""

    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, log_file)

    # 1️文件 Handler（按天轮转）
    file_handler = TimedRotatingFileHandler(
        filename=log_path,
        when="midnight",        # 每天 0 点切一个新文件
        backupCount=backup_count,
        encoding="utf-8",       # 防止中文 / Emoji 报错
        delay=True
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s"
    ))

    # 2️控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    ))

    # 3️Logger 配置
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 防止重复添加 handler
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
