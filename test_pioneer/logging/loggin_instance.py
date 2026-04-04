import logging
from logging.handlers import RotatingFileHandler

# Create a named logger (avoid setting root logger level to prevent global side effects)
# 建立名為 "TestPioneer" 的 logger（避免設定 root logger 等級以防止全域副作用）
test_pioneer_logger = logging.getLogger("TestPioneer")
test_pioneer_logger.setLevel(logging.DEBUG)

# Define log format
# 定義日誌格式
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')


class TestPioneerHandler(RotatingFileHandler):
    """
    Custom log handler for TestPioneer with rotating file support.
    自訂的 TestPioneer 日誌處理器，支援檔案輪替。
    """

    def __init__(self, filename: str = "TestPioneer.log", mode: str = "w",
                 max_bytes: int = 1073741824, backup_count: int = 0):
        """
        Args:
            filename (str): Log file name. 日誌檔案名稱。
            mode (str): File open mode. 檔案開啟模式。
            max_bytes (int): Max file size before rotation. 檔案輪替前的最大大小。
            backup_count (int): Number of backup files to keep. 保留的備份檔案數量。
        """
        super().__init__(filename=filename, mode=mode, maxBytes=max_bytes, backupCount=backup_count)
        self.setFormatter(formatter)  # 設定 formatter
        self.setLevel(logging.DEBUG)  # 設定等級為 DEBUG

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record.
        輸出日誌紀錄。
        """
        super().emit(record)


def step_log_check(enable_logging: bool = False, logger: logging.Logger = None,
                   level: str = "info", message: str = None) -> None:
    """
    Log a message if logging is enabled.
    若啟用日誌，則記錄訊息。

    Args:
        enable_logging (bool): Whether to enable logging. 是否啟用日誌。
        logger (logging.Logger): Logger instance. Logger 實例。
        level (str): Log level ("info" or "error"). 日誌等級 ("info" 或 "error")。
        message (str): Log message. 日誌訊息。
    """
    if enable_logging and logger and message:
        logger_level = {
            "info": logger.info,
            "error": logger.error,
        }.get(level)
        if logger_level:
            logger_level(message)