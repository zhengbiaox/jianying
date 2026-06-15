import logging
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logger(folder: str | None = None) -> logging.Logger:
    logger = logging.getLogger("photopicker")
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(sh)
    if folder:
        log_dir = Path(folder) / ".photopicker_cache"
        log_dir.mkdir(exist_ok=True)
        fh = RotatingFileHandler(
            log_dir / "photopicker.log",
            maxBytes=2_000_000,
            backupCount=2,
            encoding="utf-8"
        )
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(fh)
    return logger

def get_logger() -> logging.Logger:
    return logging.getLogger("photopicker")
