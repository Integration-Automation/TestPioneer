import webbrowser

from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger
from test_pioneer.utils.exception.exceptions import ExecutorException


def open_url(step: dict, enable_logging: bool = False) -> bool:
    """
    Open a URL using Python's webbrowser module.
    使用 Python 的 webbrowser 模組開啟網址。

    Args:
        step (dict): A dictionary containing 'open_url' and optional 'url_open_method'.
                     包含 'open_url' 與可選的 'url_open_method' 的字典。
        enable_logging (bool): Whether to enable logging. 是否啟用日誌紀錄。

    Returns:
        bool: True if success, False otherwise.
              成功回傳 True，失敗回傳 False。
    """

    url = step.get("open_url")
    if not isinstance(url, str):
        # Log error if 'open_url' is not a string
        # 若 'open_url' 不是字串，記錄錯誤
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message=f"The 'open_url' parameter is not a str type: {url}"
        )
        return False

    # Log the URL to be opened
    # 記錄即將開啟的網址
    step_log_check(
        enable_logging=enable_logging,
        logger=test_pioneer_logger,
        level="info",
        message=f"Open URL: {url}"
    )

    try:
        # Map available open methods
        # 定義可用的開啟方式
        method_map = {
            "open": webbrowser.open,
            "open_new": webbrowser.open_new,
            "open_new_tab": webbrowser.open_new_tab,
        }

        method_key = step.get("url_open_method", "open")  # 預設使用 "open"
        url_open_method = method_map.get(method_key)

        if url_open_method is None:
            # Log error if method is invalid
            # 若方法無效，記錄錯誤
            step_log_check(
                enable_logging=enable_logging,
                logger=test_pioneer_logger,
                level="error",
                message=f"Invalid url_open_method: {method_key}"
            )
            return False

        # Execute the chosen method
        # 執行對應的開啟方式
        url_open_method(url=url)

    except ExecutorException as error:
        # Log exception if occurs
        # 若發生例外，記錄錯誤
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message=f"Failed to open URL {url}, error: {repr(error)}"
        )
        return False

    return True