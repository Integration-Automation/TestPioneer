import json
import os
from pathlib import Path

from test_pioneer.executor.run.utils import select_with_runner
from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger


def run(step: dict, enable_logging: bool = False) -> bool:
    """
    Run a JSON-based task file using a selected runner.
    使用指定的 runner 執行 JSON 格式的任務檔案。

    Args:
        step (dict): Dictionary containing 'run' (file path).
                     包含 'run' (檔案路徑) 的字典。
        enable_logging (bool): Whether to enable logging. 是否啟用日誌紀錄。

    Returns:
        bool: True if success, False otherwise.
              成功回傳 True，失敗回傳 False。
    """

    # Select runner with validation
    # 選擇 runner 並檢查是否有效
    check_with_data = select_with_runner(step, enable_logging=enable_logging, mode="run")
    if not check_with_data[0]:
        return False
    execute_with = check_with_data[1]

    # Get file path
    # 取得檔案路徑
    file_path = step.get("run")
    if not isinstance(file_path, str):
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message=f"'run' parameter must be a string, got: {file_path}"
        )
        return False

    # Build absolute path safely
    # 安全地建立絕對路徑
    abs_file_path = Path(os.getcwd()) / file_path
    abs_file_path = abs_file_path.resolve()

    # Validate file existence
    # 驗證檔案是否存在
    if not abs_file_path.is_file():
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message=f"File does not exist: {file_path}"
        )
        return False

    # Load JSON content
    # 載入 JSON 內容
    try:
        file_content = json.loads(abs_file_path.read_text(encoding="utf-8"))
    except Exception as error:
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message=f"Failed to load JSON file {file_path}, error: {error}"
        )
        return False

    # Execute with runner
    # 使用 runner 執行
    execute_with(file_content)
    return True