from test_pioneer.logging.loggin_instance import test_pioneer_logger, step_log_check


def download_single_file(step: dict, enable_logging: bool = False) -> bool:
    """
    Download a single file using automation_file.download_file
    使用 automation_file.download_file 下載單一檔案

    Args:
        step (dict): Dictionary containing 'download_file' (URL) and 'file_path' (local path).
                     包含 'download_file' (檔案網址) 與 'file_path' (本地路徑) 的字典
        enable_logging (bool): Whether to enable logging. 是否啟用日誌紀錄

    Returns:
        bool: True if success, False otherwise.
              成功回傳 True，失敗回傳 False
    """
    file_url = step.get("download_file")
    file_path = step.get("file_path")

    # Import inside function to avoid unnecessary global dependency
    # 在函式內部匯入，避免全域依賴
    from automation_file import download_file

    # Check required parameters
    # 檢查必要參數
    if not file_url or not file_path:
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message="Missing parameters: 'download_file' and 'file_path' are required."
        )
        return False

    # Validate parameter types
    # 驗證參數型別
    if not isinstance(file_url, str) or not isinstance(file_path, str):
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message="Both 'download_file' and 'file_path' must be of type str."
        )
        return False

    # Perform download
    # 執行下載
    download_file(file_url=file_url, file_name=file_path)
    return True


def unzip_zipfile(step: dict, enable_logging: bool = False) -> bool:
    """
    Unzip a zip file using automation_file.unzip_all
    使用 automation_file.unzip_all 解壓縮 zip 檔案

    Args:
        step (dict): Dictionary containing 'zip_file_path', optional 'password', and 'extract_path'.
                     包含 'zip_file_path'，可選 'password' 與 'extract_path' 的字典
        enable_logging (bool): Whether to enable logging. 是否啟用日誌紀錄

    Returns:
        bool: True if success, False otherwise.
              成功回傳 True，失敗回傳 False
    """
    zip_file_path = step.get("zip_file_path")
    password = step.get("password")
    extract_path = step.get("extract_path")

    # Check required parameter
    # 檢查必要參數
    if not zip_file_path:
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message="Missing parameter: 'zip_file_path' is required."
        )
        return False

    # Validate parameter type
    # 驗證參數型別
    if not isinstance(zip_file_path, str):
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message="'zip_file_path' must be of type str."
        )
        return False

    # Import inside function to avoid unnecessary global dependency
    # 在函式內部匯入，避免全域依賴
    from automation_file import unzip_all

    # Build kwargs dynamically
    # 動態建立參數字典
    kwargs = {"zip_file_path": zip_file_path}
    if password:
        kwargs["password"] = password
    if extract_path:
        kwargs["extract_path"] = extract_path

    # Perform unzip
    # 執行解壓縮
    unzip_all(**kwargs)
    return True