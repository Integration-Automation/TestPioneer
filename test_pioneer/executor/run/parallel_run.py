import subprocess
import sys
from pathlib import Path

from test_pioneer.executor.run.process_manager import process_manager
from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger
from test_pioneer.utils.package.check import is_installed


def parallel_run(step: dict, enable_logging: bool = False) -> bool:
    parallel_run_dict = step.get("parallel_run")
    if parallel_run_dict is None:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message="parallel_run tag needs to be defined as an argument")
        return False
    runner_list = parallel_run_dict.get("runners", [])
    script_path_list = parallel_run_dict.get("scripts", [])
    executor_path = parallel_run_dict.get("executor_path", None)
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
            step_log_check(
                enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                message="Please install gui-runner: je_auto_control")
        if is_installed(package_name="je_auto_control"):
            runner_command_dict.update({"gui-runner": "je_auto_control"})

        if executor_path is None:
            executor_path = sys.executable

        if executor_path == "py.exe" or executor_path is None:
            import shutil
            executor_path = shutil.which("python3") or shutil.which("python")

        for runner, script in zip(runner_list, script_path_list):
            runner_package = runner_command_dict.get(runner)
            script_text = Path(script)
            commands = " ".join([f"{executor_path}", "-m", f"{runner_package}", "--execute_file", f"{script_text}"])
            current_process: subprocess.Popen = subprocess.Popen(commands)
            process_manager.process_list.append(current_process)

        while True:
            if process_manager.process_list is None or len(process_manager.process_list) == 0:
                break
            for process in process_manager.process_list:
                process.poll()
                if process.returncode is not None:
                    process_manager.process_list.remove(process)

    return True

