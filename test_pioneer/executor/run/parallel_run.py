import subprocess
import sys
import shutil
import time
from pathlib import Path
from typing import List, Optional, Tuple

from test_pioneer.executor.run.process_manager import process_manager
from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger
from test_pioneer.utils.package.check import is_installed


_BASE_RUNNER_COMMANDS = {
    "web-runner": "je_web_runner",
    "api-runner": "je_api_testka",
    "load-runner": "je_load_density",
}


def _log_error(enable_logging: bool, message: str) -> None:
    step_log_check(
        enable_logging=enable_logging,
        logger=test_pioneer_logger,
        level="error",
        message=message,
    )


def _validate_parallel_inputs(
    parallel_run_dict: Optional[dict],
    enable_logging: bool,
) -> Optional[Tuple[List[str], List[str], Optional[str]]]:
    """Return (runners, scripts, executor_path) if valid, else None."""
    if parallel_run_dict is None:
        _log_error(enable_logging, "parallel_run tag needs to be defined as an argument")
        return None

    runner_list = parallel_run_dict.get("runners", [])
    script_path_list = parallel_run_dict.get("scripts", [])
    if len(runner_list) != len(script_path_list):
        _log_error(enable_logging, "The number of runners and scripts is not equal")
        return None

    return runner_list, script_path_list, parallel_run_dict.get("executor_path")


def _build_runner_command_dict(
    runner_list: List[str],
    enable_logging: bool,
) -> Optional[dict]:
    """Return the runner→package map, or None if a required dependency is missing."""
    gui_installed = is_installed("je_auto_control")
    if "gui-runner" in runner_list and not gui_installed:
        _log_error(enable_logging, "Please install gui-runner: je_auto_control")
        return None

    runner_command_dict = dict(_BASE_RUNNER_COMMANDS)
    if gui_installed:
        runner_command_dict["gui-runner"] = "je_auto_control"
    return runner_command_dict


def _resolve_executor_path(executor_path: Optional[str]) -> Optional[str]:
    """Pick a usable Python executor."""
    if not executor_path:
        executor_path = sys.executable
    if executor_path == "py.exe" or executor_path is None:
        executor_path = shutil.which("python3") or shutil.which("python")
    return executor_path


def _start_single_process(
    executor_path: str,
    runner_package: str,
    script_path: Path,
    enable_logging: bool,
) -> None:
    commands = [
        executor_path,
        "-m", runner_package,
        "--execute_file", str(script_path),
    ]
    try:
        current_process = subprocess.Popen(commands)
        process_manager.process_list.append(current_process)
    except OSError as error:
        _log_error(enable_logging, f"Failed to start process for {script_path}: {error}")


def _start_processes(
    runner_list: List[str],
    script_path_list: List[str],
    runner_command_dict: dict,
    executor_path: str,
    enable_logging: bool,
) -> None:
    for runner, script in zip(runner_list, script_path_list):
        runner_package = runner_command_dict.get(runner)
        if not runner_package:
            _log_error(enable_logging, f"Unknown runner type: {runner}")
            continue

        script_path = Path(script).resolve()
        if not script_path.is_file():
            _log_error(enable_logging, f"Script file does not exist: {script}")
            continue

        _start_single_process(executor_path, runner_package, script_path, enable_logging)


def _wait_for_processes() -> None:
    while process_manager.process_list:
        process_manager.cleanup_finished()
        if process_manager.process_list:
            time.sleep(0.1)


def parallel_run(step: dict, enable_logging: bool = False) -> bool:
    """
    Run multiple scripts in parallel using different runners.
    使用不同的 runner 平行執行多個腳本。

    Args:
        step (dict): Dictionary containing 'parallel_run' with keys:
                     包含 'parallel_run' 的字典，需包含以下鍵：
                     - runners (list[str]): Runner types 執行器類型
                     - scripts (list[str]): Script paths 腳本路徑
                     - executor_path (str, optional): Python executor path Python 執行器路徑
        enable_logging (bool): Whether to enable logging. 是否啟用日誌紀錄

    Returns:
        bool: True if success, False otherwise.
              成功回傳 True，失敗回傳 False
    """
    validated = _validate_parallel_inputs(step.get("parallel_run"), enable_logging)
    if validated is None:
        return False
    runner_list, script_path_list, executor_path = validated

    runner_command_dict = _build_runner_command_dict(runner_list, enable_logging)
    if runner_command_dict is None:
        return False

    executor_path = _resolve_executor_path(executor_path)

    _start_processes(
        runner_list,
        script_path_list,
        runner_command_dict,
        executor_path,
        enable_logging,
    )
    _wait_for_processes()
    return True
