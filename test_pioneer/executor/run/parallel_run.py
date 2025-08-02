import json
import subprocess
import sys
from pathlib import Path

from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger
from test_pioneer.utils.exception.exceptions import ExecutorException
from test_pioneer.utils.exception.tags import can_not_run_gui_error
from test_pioneer.utils.package.check import is_installed


def parallel_run(step: dict, enable_logging: bool = False) -> bool:
    runner_list = step.get("runners", [])
    script_path_list = step.get("scripts", [])
    executor_path = step.get("executor_path", None)
    if len(runner_list) != len(script_path_list):
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message="The number of runners and scripts is not equal")
        return False
    else:
        runner_command_dict = {
            "web-runner": "je_web_runner",
            "api-runner": "je_api_testka",
            "load-runner": "je_load_density"
        }

        if not is_installed(package_name="je_auto_control") and "gui-runner" in runner_list:
            raise ExecutorException(can_not_run_gui_error)
        if is_installed(package_name="je_auto_control"):
            runner_command_dict.update({"gui-runner": "je_auto_control"})

        if executor_path is None:
            executor_path = sys.executable

        if executor_path == "py.exe" or executor_path is None:
            import shutil
            executor_path = shutil.which("python3") or shutil.which("python")

        for runner, script in zip(runner_list, script_path_list):
            runner_package = runner_command_dict.get(runner)
            script_text = json.loads(Path(script).read_text())
            print(executor_path, runner_package, script_text)
            subprocess.Popen(args=[executor_path, "-m", runner_package, "--execute_str", script_text])

    return True
