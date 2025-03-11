import logging
from logging.handlers import RotatingFileHandler

logging.root.setLevel(logging.DEBUG)
test_pioneer_logger = logging.getLogger("TestPioneer")
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')


class TestPioneerHandler(RotatingFileHandler):

    def __init__(self, filename: str = "TestPioneer.log", mode="w",
                 maxBytes: int = 1073741824, backupCount: int = 0):
        super().__init__(filename=filename, mode=mode, maxBytes=maxBytes, backupCount=backupCount)
        self.formatter = formatter
        self.setLevel(logging.DEBUG)

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)


def step_log_check(enable_logging: bool = False, logger: logging.Logger = None,
                   level: str = "info", message: str = None):
    if enable_logging and logger:
        logger_level = {
            "info": logger.info,
            "error": logger.error,
        }.get(level, None)
        if logger_level is not None:
            logger_level(message)
