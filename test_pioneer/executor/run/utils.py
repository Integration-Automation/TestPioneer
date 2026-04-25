from typing import Tuple, Union, Callable, Optional

from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger
from test_pioneer.utils.exception.exceptions import ExecutorException
from test_pioneer.utils.exception.tags import can_not_run_gui_error
from test_pioneer.utils.package.check import is_installed


def _log_error(enable_logging: bool, message: str) -> None:
    step_log_check(
        enable_logging=enable_logging,
        logger=test_pioneer_logger,
        level="error",
        message=message,
    )


def _resolve_with_tag(step: dict, enable_logging: bool) -> Optional[str]:
    """Validate and return the 'with' tag, or None if invalid."""
    with_tag = step.get("with")
    if with_tag is None:
        _log_error(enable_logging, "Step requires 'with' tag")
        return None
    if not isinstance(with_tag, str):
        _log_error(enable_logging, f"The 'with' parameter must be str, got: {with_tag}")
        return None
    return with_tag


def _build_runner_dict(mode: str, with_tag: str) -> dict:
    """Build the runner registry for the given mode. Raises if GUI is required but missing."""
    # Prevent monkey patching in locust
    # 避免 locust monkey patch
    from os import environ
    environ["LOCUST_SKIP_MONKEY_PATCH"] = "1"

    from je_load_density import execute_action as load_runner
    from je_web_runner import execute_action as web_runner
    from je_api_testka import execute_action as api_runner

    runner_dict = {
        "web-runner": web_runner,
        "api-runner": api_runner,
        "load-runner": load_runner,
    }

    if mode not in ("run", "run_folder"):
        return runner_dict

    if with_tag == "gui-runner" and not is_installed("je_auto_control"):
        raise ExecutorException(can_not_run_gui_error)
    if is_installed("je_auto_control"):
        if mode == "run":
            from je_auto_control import execute_action as single_gui_runner
            runner_dict["gui-runner"] = single_gui_runner
        else:
            from je_auto_control import execute_files as multi_gui_runner
            runner_dict["gui-runner"] = multi_gui_runner
    return runner_dict


def select_with_runner(step: dict, enable_logging: bool, mode: str = "run") -> Tuple[bool, Union[Callable, None]]:
    """
    Select the appropriate runner function based on 'with' tag and mode.
    根據 'with' 標籤與 mode 選擇合適的 runner 函式。

    Returns:
        Tuple[bool, Union[Callable, None]]:
            - bool: True if a runner was resolved.
            - Callable or None: The runner function, or None if not found.
    """
    with_tag = _resolve_with_tag(step, enable_logging)
    if with_tag is None:
        return False, None

    try:
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="info",
            message=f"Run with: {with_tag}, path: {step.get('run')}",
        )
        runner_dict = _build_runner_dict(mode, with_tag)
        execute_with = runner_dict.get(with_tag) if mode in ("run", "run_folder") else None
    except ExecutorException as error:
        _log_error(
            enable_logging,
            f"Run with: {with_tag}, path: {step.get('run')}, error: {repr(error)}",
        )
        return False, None

    if execute_with is None:
        _log_error(enable_logging, f"Invalid runner tag: {with_tag}")
        return False, None
    return True, execute_with
