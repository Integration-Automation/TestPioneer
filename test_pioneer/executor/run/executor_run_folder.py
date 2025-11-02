import os
from pathlib import Path

from test_pioneer.executor.run.utils import select_with_runner
from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger


def run_folder(step: dict, enable_logging: bool = False, mode: str = "run_folder"):
    check_with_data = select_with_runner(step, enable_logging=enable_logging, mode=mode)
    if check_with_data[0] is False:
        return False
    else:
        execute_with = check_with_data[1]
    folder = step.get("run_folder")
    folder = str(Path(os.getcwd() + folder).absolute())
    if folder is None:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"run param need folder path: {step.get('run_folder')}")
        return False
    if (Path(folder).is_dir() is False) or not Path(folder).exists():
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"This folder not exists: {step.get('run_folder')}")
        return False
    folder = Path(folder)
    json_files = list(folder.glob('*.json'))
    if len(json_files) > 0:
        execute_with(json_files)
    else:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"Folder is empty: {step.get('run_folder')}")
        return False
    return True
