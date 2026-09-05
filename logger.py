import logging
from pathlib import Path

LOG_FILE_PATH = Path("logs") / "bot.log"
LOGGER_NAME = "telegram_signal_bot"


def configurar_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    LOG_FILE_PATH.parent.mkdir(exist_ok=True)

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


logger = logging.getLogger(LOGGER_NAME)
