from test_pioneer.logging.loggin_instance import TestPioneerHandler, test_pioneer_logger


def set_logger(yaml_data: dict) -> bool:
    """
    Set up a logger handler based on yaml_data configuration.
    根據 yaml_data 的設定建立並加入 logger handler。

    Args:
        yaml_data (dict): Dictionary containing 'pioneer_log' key for log file path.
                          包含 'pioneer_log' 鍵（指定日誌檔案路徑）的字典。

    Returns:
        bool: True if handler is added successfully, False otherwise.
              成功加入 handler 回傳 True，否則 False。
    """
    # Check if yaml_data contains pioneer_log key
    # 檢查 yaml_data 是否包含 pioneer_log 鍵
    filename = yaml_data.get("pioneer_log")
    if filename:
        # Create handler with given filename
        # 使用指定檔名建立 handler
        file_handler = TestPioneerHandler(filename=filename)

        # Add handler to logger
        # 將 handler 加入 logger
        test_pioneer_logger.addHandler(file_handler)
        return True

    # No pioneer_log key found
    # 若未找到 pioneer_log 鍵
    return False