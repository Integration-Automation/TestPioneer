from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger
from test_pioneer.process.execute_process import ExecuteProcess
from test_pioneer.process.process_manager import process_manager_instance


def open_program(step: dict, name: str, enable_logging: bool = False) -> bool:
    """
    Open a program using ExecuteProcess and register it in process_manager_instance.
    使用 ExecuteProcess 開啟程式並註冊到 process_manager_instance。

    Args:
        step (dict): Dictionary containing 'open_program' and optional 'redirect_stdout', 'redirect_stderr'.
                     包含 'open_program' 以及可選的 'redirect_stdout', 'redirect_stderr' 的字典。
        name (str): The key name to register the process in process_manager_instance.
                    在 process_manager_instance 中註冊的名稱。
        enable_logging (bool): Whether to enable logging. 是否啟用日誌紀錄。

    Returns:
        bool: True if success, False otherwise.
              成功回傳 True，失敗回傳 False。
    """
    program = step.get("open_program")
    if not isinstance(program, str):
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message=f"The 'open_program' parameter must be str, got: {program}"
        )
        return False

    step_log_check(
        enable_logging=enable_logging,
        logger=test_pioneer_logger,
        level="info",
        message=f"Open program: {program}"
    )

    # Initialize redirect paths
    # 初始化輸出重定向路徑
    redirect_stdout = None
    redirect_stderr = None

    # Handle stdout redirection
    # 處理標準輸出重定向
    if "redirect_stdout" in step:
        stdout_path = step.get("redirect_stdout")
        if not isinstance(stdout_path, str):
            step_log_check(
                enable_logging=enable_logging,
                logger=test_pioneer_logger,
                level="error",
                message=f"The 'redirect_stdout' parameter must be str, got: {stdout_path}"
            )
            return False
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="info",
            message=f"Redirect stdout to: {stdout_path}"
        )
        redirect_stdout = stdout_path

    # Handle stderr redirection
    # 處理標準錯誤輸出重定向
    if "redirect_stderr" in step:
        stderr_path = step.get("redirect_stderr")
        if not isinstance(stderr_path, str):
            step_log_check(
                enable_logging=enable_logging,
                logger=test_pioneer_logger,
                level="error",
                message=f"The 'redirect_stderr' parameter must be str, got: {stderr_path}"
            )
            return False
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="info",
            message=f"Redirect stderr to: {stderr_path}"
        )
        redirect_stderr = stderr_path

    # Create and register process
    # 建立並註冊程序
    execute_process = ExecuteProcess()
    process_manager_instance.process_dict[name] = execute_process

    # Assign redirections if provided
    # 若有設定則指定重定向
    if redirect_stdout:
        execute_process.redirect_stdout = redirect_stdout
    if redirect_stderr:
        execute_process.redirect_stderr = redirect_stderr

    # Start the process
    # 啟動程式
    execute_process.start_process(program)
    return True


def close_program(step: dict, enable_logging: bool = False) -> bool:
    """
    Close a program using process_manager_instance.
    使用 process_manager_instance 關閉程式。

    Args:
        step (dict): Dictionary containing 'close_program'.
                     包含 'close_program' 的字典。
        enable_logging (bool): Whether to enable logging. 是否啟用日誌紀錄。

    Returns:
        bool: True if success, False otherwise.
              成功回傳 True，失敗回傳 False。
    """
    program = step.get("close_program")
    if not isinstance(program, str):
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message=f"The 'close_program' parameter must be str, got: {program}"
        )
        return False

    step_log_check(
        enable_logging=enable_logging,
        logger=test_pioneer_logger,
        level="info",
        message=f"Close program: {program}"
    )

    # Close the process
    # 關閉程式
    process_manager_instance.close_process(program)
    return True