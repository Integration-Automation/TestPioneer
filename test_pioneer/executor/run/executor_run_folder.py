import os
from pathlib import Path

from test_pioneer.executor.run.utils import select_with_runner
from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger


def run_folder(step: dict, enable_logging: bool = False, mode: str = "run_folder") -> bool:
    """
    Run all JSON files inside a specified folder using a selected runner.
    使用指定的 runner 執行資料夾中的所有 JSON 檔案。

    Args:
        step (dict): Dictionary containing 'run_folder' (folder path).
                     包含 'run_folder' (資料夾路徑) 的字典。
        enable_logging (bool): Whether to enable logging. 是否啟用日誌紀錄。
        mode (str): Runner mode, default is "run_folder".
                    Runner 模式，預設為 "run_folder"。

    Returns:
        bool: True if success, False otherwise.
              成功回傳 True，失敗回傳 False。
    """

    # Select runner with validation
    # 選擇 runner 並檢查是否有效
    check_with_data = select_with_runner(step, enable_logging=enable_logging, mode=mode)
    if not check_with_data[0]:
        return False
    execute_with = check_with_data[1]

    # Get folder path
    # 取得資料夾路徑
    folder_path = step.get("run_folder")
    if not isinstance(folder_path, str):
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message=f"'run_folder' parameter must be a string, got: {folder_path}"
        )
        return False

    # Build absolute path safely
    # 安全地建立絕對路徑
    abs_folder_path = Path(os.getcwd()) / folder_path
    abs_folder_path = abs_folder_path.resolve()

    # Validate folder existence
    # 驗證資料夾是否存在
    if not abs_folder_path.is_dir():
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message=f"Folder does not exist: {folder_path}"
        )
        return False

    # Find JSON files
    # 搜尋 JSON 檔案
    json_files = list(abs_folder_path.glob("*.json"))
    if not json_files:
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message=f"Folder is empty or contains no JSON files: {folder_path}"
        )
        return False

    # Execute runner with JSON files
    # 使用 runner 執行 JSON 檔案
    execute_with(json_files)
    return True