from typing import Tuple, Union, Callable

from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger
from test_pioneer.utils.exception.exceptions import ExecutorException
from test_pioneer.utils.exception.tags import can_not_run_gui_error
from test_pioneer.utils.package.check import is_installed


def select_with_runner(step: dict, enable_logging: bool, mode: str = "run") -> Tuple[bool, Union[Callable, None]]:
    """
    Select the appropriate runner function based on 'with' tag and mode.
    根據 'with' 標籤與 mode 選擇合適的 runner 函式。

    Args:
        step (dict): Dictionary containing 'with' and optionally 'run'.
                     包含 'with' 與可選 'run' 的字典。
        enable_logging (bool): Whether to enable logging. 是否啟用日誌紀錄。
        mode (str): Runner mode, either "run" or "run_folder".
                    Runner 模式，可為 "run" 或 "run_folder"。

    Returns:
        Tuple[bool, Union[Callable, None]]:
            - bool: True if runner is selected successfully, False otherwise.
                    成功選擇 runner 回傳 True，否則 False。
            - Callable or None: The runner function, or None if not found.
                                對應的 runner 函式，若未找到則為 None。
    """

    # Validate 'with' tag
    # 驗證 'with' 標籤
    with_tag = step.get("with")
    if with_tag is None:
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message="Step requires 'with' tag"
        )
        return False, None

    if not isinstance(with_tag, str):
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message=f"The 'with' parameter must be str, got: {with_tag}"
        )
        return False, None

    try:
        # Log runner info
        # 記錄 runner 資訊
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="info",
            message=f"Run with: {with_tag}, path: {step.get('run')}"
        )

        # Prevent monkey patching in locust
        # 避免 locust monkey patch
        from os import environ
        environ["LOCUST_SKIP_MONKEY_PATCH"] = "1"

        # Import runners
        # 匯入 runner
        from je_load_density import execute_action as load_runner
        from je_web_runner import execute_action as web_runner
        from je_api_testka import execute_action as api_runner

        runner_dict = {
            "web-runner": web_runner,
            "api-runner": api_runner,
            "load-runner": load_runner
        }

        # Handle GUI runner depending on mode
        # 根據 mode 處理 GUI runner
        if mode == "run":
            if with_tag == "gui-runner" and not is_installed("je_auto_control"):
                raise ExecutorException(can_not_run_gui_error)
            if is_installed("je_auto_control"):
                from je_auto_control import execute_action as single_gui_runner
                runner_dict["gui-runner"] = single_gui_runner
            execute_with = runner_dict.get(with_tag)

        elif mode == "run_folder":
            if with_tag == "gui-runner" and not is_installed("je_auto_control"):
                raise ExecutorException(can_not_run_gui_error)
            if is_installed("je_auto_control"):
                from je_auto_control import execute_files as multi_gui_runner
                runner_dict["gui-runner"] = multi_gui_runner
            execute_with = runner_dict.get(with_tag)

        else:
            execute_with = None

        # Validate runner existence
        # 驗證 runner 是否存在
        if execute_with is None:
            step_log_check(
                enable_logging=enable_logging,
                logger=test_pioneer_logger,
                level="error",
                message=f"Invalid runner tag: {with_tag}"
            )
            return False, None

    except ExecutorException as error:
        # Handle exception
        # 處理例外
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message=f"Run with: {with_tag}, path: {step.get('run')}, error: {repr(error)}"
        )
        return False, None

    return True, execute_with