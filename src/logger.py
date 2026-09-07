"""Configuration du système de logs."""

import logging
from pathlib import Path

import colorlog


Path("logs").mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("pipeline")
logger.setLevel(logging.INFO)
logger.propagate = False


if not logger.handlers:

    console_handler = colorlog.StreamHandler()

    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(asctime)s %(log_color)s%(levelname)-8s%(reset)s %(name)-16.16s:%(lineno)-4.4d %(message)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red",
            },
        )
    )

    file_handler = logging.FileHandler(
        "logs/pipeline.log",
        encoding="utf-8",
    )

    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)-16.16s:%(lineno)-4.4d %(message)s"
        )
    )

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
