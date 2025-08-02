import json
import os
from pathlib import Path

from test_pioneer.executor.run.utils import select_with_runner
from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger


def run(step: dict, enable_logging: bool) -> bool:
    check_with_data = select_with_runner(step, enable_logging=enable_logging, mode="run")
    if not check_with_data[0]:
        return False
    else:
        execute_with = check_with_data[1]
    file = step.get("run")
    file = str(Path(os.getcwd() + file).absolute())
    if file is None:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"run param need file path: {step.get('run')}")
        return False
    if (Path(file).is_file() is False) or not Path(file).exists():
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"This file not exists: {step.get('run')}")
        return False
    try:
        file = json.loads(Path(file).read_text())
    except Exception as error:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"load json failed: {error}")
    execute_with(file)
    return True