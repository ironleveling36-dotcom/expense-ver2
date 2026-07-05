"""Centralised logging configuration."""
import logging
import sys

from config import config

_configured = False


def setup_logging():
    global _configured
    if _configured:
        return
    level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers on reload
    if not root.handlers:
        root.addHandler(handler)
    _configured = True


def get_logger(name):
    setup_logging()
    return logging.getLogger(name)
