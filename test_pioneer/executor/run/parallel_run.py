"""The ``parallel_run`` step: start one runner sub-process per script and wait for all of them."""
import sys
import shutil
import time
from pathlib import Path
from typing import List, Optional, Tuple

from test_pioneer.artifacts.session import current_session
from test_pioneer.executor.run.process_manager import process_manager
from test_pioneer.executor.run.runner_process import RunnerProcess, RunnerRequest, start_runner_process
from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger
from test_pioneer.runner.adapter import ModuleRunner
from test_pioneer.runner.registry import GUI_RUNNER, OPTIONAL_RUNNERS, RUNNER_PACKAGES, find_runner
from test_pioneer.utils.package.check import is_installed


_BASE_RUNNER_COMMANDS = {
    runner: package for runner, package in RUNNER_PACKAGES.items() if runner not in OPTIONAL_RUNNERS
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
    gui_package = RUNNER_PACKAGES[GUI_RUNNER]
    gui_installed = is_installed(gui_package)
    if GUI_RUNNER in runner_list and not gui_installed:
        _log_error(enable_logging, f"Please install {GUI_RUNNER}: {gui_package}")
        return None

    runner_command_dict = dict(_BASE_RUNNER_COMMANDS)
    if gui_installed:
        runner_command_dict[GUI_RUNNER] = gui_package
    return runner_command_dict


def _resolve_executor_path(executor_path: Optional[str]) -> Optional[str]:
    """Pick a usable Python executor."""
    if not executor_path:
        executor_path = sys.executable
    if executor_path == "py.exe" or executor_path is None:
        executor_path = shutil.which("python3") or shutil.which("python")
    return executor_path


def _requests(parallel_run_dict: dict, runner_list: List[str], script_path_list: List[str]) -> List[RunnerRequest]:
    """Pair each runner with its script and with the artifacts declared at the same position."""
    declared = parallel_run_dict.get("artifacts")
    patterns = declared if isinstance(declared, list) else []
    return [
        RunnerRequest(runner, script, part, patterns[part - 1] if part <= len(patterns) else None)
        for part, (runner, script) in enumerate(zip(runner_list, script_path_list), start=1)
    ]


def _start_single_process(
    executor_path: str,
    request: RunnerRequest,
    runner_package: str,
    script_path: Path,
    enable_logging: bool,
) -> Optional[RunnerProcess]:
    adapter = find_runner(request.runner) or ModuleRunner(request.runner, runner_package)
    commands = adapter.command(executor_path, script_path)
    try:
        child = start_runner_process(commands, request)
    except OSError as error:
        _log_error(enable_logging, f"Failed to start process for {script_path}: {error}")
        return None
    process_manager.process_list.append(child.process)
    return child


def _reject(runner: str, script: str, message: str, enable_logging: bool) -> None:
    """Log why a script is skipped and, inside a run, record it as a runner error."""
    _log_error(enable_logging, message)
    session = current_session()
    if session is not None:
        session.reject(str(runner), str(script), message)


def _start_processes(
    requests: List[RunnerRequest],
    runner_command_dict: dict,
    executor_path: str,
    enable_logging: bool,
) -> List[RunnerProcess]:
    children: List[RunnerProcess] = []
    for request in requests:
        runner, script = request.runner, request.script
        runner_package = runner_command_dict.get(runner)
        if not runner_package:
            _reject(runner, script, f"Unknown runner type: {runner}", enable_logging)
            continue

        script_path = Path(script).resolve()
        if not script_path.is_file():
            _reject(runner, script, f"Script file does not exist: {script}", enable_logging)
            continue

        child = _start_single_process(executor_path, request, runner_package, script_path, enable_logging)
        if child is not None:
            children.append(child)
    return children


def _wait_for_processes(children: List[RunnerProcess]) -> None:
    pending = list(children)
    try:
        while pending:
            for child in pending:
                child.pump()
            finished = [child for child in pending if child.finished()]
            for child in finished:
                process_manager.remove_process(child.process)
                child.close()
            pending = [child for child in pending if child not in finished]
            if pending:
                time.sleep(0.1)
    finally:
        # Only non-empty when the wait was interrupted: do not leave runners behind.
        for child in pending:
            process_manager.remove_process(child.process)
            child.cancel()


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

    children = _start_processes(
        _requests(step["parallel_run"], runner_list, script_path_list),
        runner_command_dict,
        executor_path,
        enable_logging,
    )
    _wait_for_processes(children)
    return True
