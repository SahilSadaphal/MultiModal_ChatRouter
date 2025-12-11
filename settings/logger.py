
import logging
import os
from logging.handlers import RotatingFileHandler

class Logger:
    _logger = None

    @staticmethod
    def get_logger(name: str = __name__):
        if Logger._logger:
            return Logger._logger

        os.makedirs("logs", exist_ok=True)

        # concise format: date time - filename:line - message
        log_format = "%(asctime)s - %(filename)s:%(lineno)d - %(message)s"
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(log_format)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        file_handler = RotatingFileHandler(
            "logs/app.log",
            maxBytes=5 * 1024 * 1024,   # 5 MB
            backupCount=3
        )
        file_handler.setFormatter(formatter)

        # Avoid duplicate handlers and prevent propagation to root logger
        if not logger.handlers:
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        logger.propagate = False

        Logger._logger = logger
        return logger
