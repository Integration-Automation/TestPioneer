import time
from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger


def blocked_wait(step: dict, enable_logging: bool = False) -> bool:
    """
    Block execution for a given number of seconds.
    根據 step 中的 'wait' 參數阻塞執行指定秒數。

    Args:
        step (dict): Dictionary containing 'wait' key (int).
                     包含 'wait' 鍵（整數秒數）的字典。
        enable_logging (bool): Whether to enable logging. 是否啟用日誌紀錄。

    Returns:
        bool: True if wait executed successfully, False otherwise.
              成功執行等待回傳 True，否則 False。
    """

    wait_time = step.get("wait")

    # Validate parameter type
    # 驗證參數型別
    if not isinstance(wait_time, int):
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",  # 改為 error 更符合語義
            message=f"The 'wait' parameter must be int, got: {wait_time}"
        )
        return False

    # Log wait time
    # 記錄等待秒數
    step_log_check(
        enable_logging=enable_logging,
        logger=test_pioneer_logger,
        level="info",
        message=f"Wait seconds: {wait_time}"
    )

    # Perform blocking wait
    # 執行阻塞等待
    time.sleep(wait_time)
    return True