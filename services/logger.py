import sys
import logging
from logging.handlers import RotatingFileHandler

LOG_FORMAT = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("PrismAPI")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = RotatingFileHandler("prism.log", maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
