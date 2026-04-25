import time
from pathlib import Path
from typing import Optional, Tuple

import yaml

from test_pioneer.executor.browser.url import open_url
from test_pioneer.executor.file.file_processing import download_single_file, unzip_zipfile
from test_pioneer.executor.program.external_program import open_program, close_program
from test_pioneer.executor.run.executor_run import run
from test_pioneer.executor.run.executor_run_folder import run_folder
from test_pioneer.executor.run.parallel_run import parallel_run
from test_pioneer.executor.test_recorder.logger import set_logger
from test_pioneer.executor.time.wait import blocked_wait
from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger
from test_pioneer.process.process_manager import process_manager_instance
from test_pioneer.utils.exception.exceptions import WrongInputException, YamlException
from test_pioneer.utils.package.check import is_installed

# Step type to handler mapping
# 步驟類型對應的處理函式
_STEP_HANDLERS = {
    "run": lambda step, name, enable_logging: run(step=step, enable_logging=enable_logging),
    "run_folder": lambda step, name, enable_logging: run_folder(step=step, enable_logging=enable_logging, mode="run_folder"),
    "open_url": lambda step, name, enable_logging: open_url(step=step, enable_logging=enable_logging),
    "download_file": lambda step, name, enable_logging: download_single_file(step=step, enable_logging=enable_logging),
    "wait": lambda step, name, enable_logging: blocked_wait(step=step, enable_logging=enable_logging),
    "open_program": lambda step, name, enable_logging: open_program(step=step, name=name, enable_logging=enable_logging),
    "close_program": lambda step, name, enable_logging: close_program(step=step, enable_logging=enable_logging),
    "unzip_zipfile": lambda step, name, enable_logging: unzip_zipfile(step=step, enable_logging=enable_logging),
    "parallel_run": lambda step, name, enable_logging: parallel_run(step=step, enable_logging=enable_logging),
}


def _stop_recorder(recording: bool, recorder) -> None:
    """Stop the recording thread if active."""
    if recording and recorder is not None:
        recorder.set_recording_flag(False)
        while recorder.is_alive():
            time.sleep(0.1)


def _load_yaml(stream: str, yaml_type: str) -> dict:
    """Load and validate YAML data from file or string."""
    if yaml_type == "File":
        yaml_data = yaml.safe_load(Path(stream).read_text(encoding="utf-8"))
    elif yaml_type == "String":
        yaml_data = yaml.safe_load(stream=stream)
    else:
        raise WrongInputException("Wrong input: " + repr(stream))

    if not isinstance(yaml_data, dict):
        raise YamlException(f"Not a dict: {yaml_data}")
    return yaml_data


def _validate_steps(steps: list, enable_logging: bool) -> bool:
    """Validate step names for duplicates. Returns True if valid."""
    for step in steps:
        if step.get("name") is None:
            step_log_check(
                enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                message="Step need name tag")
            return False
        name = step.get("name")
        if name in process_manager_instance.name_set:
            step_log_check(
                enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                message=f"job name duplicated: {name}")
            return False
        process_manager_instance.name_set.add(name)
    return True


def _setup_recorder(yaml_data: dict) -> Tuple[bool, object]:
    """Initialize the recorder when je_auto_control is available."""
    if not is_installed(package_name="je_auto_control"):
        return False, None
    try:
        from test_pioneer.executor.test_recorder.video_recoder import set_recorder
        return set_recorder(yaml_data=yaml_data)
    except ImportError:
        return False, None


def _extract_steps(yaml_data: dict) -> list:
    """Validate top-level YAML structure and return the steps list."""
    if "jobs" not in yaml_data:
        raise YamlException("No jobs tag")
    if not isinstance(yaml_data.get("jobs"), dict):
        raise YamlException("jobs not a dict")
    steps = yaml_data["jobs"].get("steps")
    if not steps:
        raise YamlException("Steps tag is empty")
    return steps


def _dispatch_step(step: dict, name: Optional[str], enable_logging: bool) -> bool:
    """Run the first matching handler for a step. Returns False to stop execution."""
    for step_type, handler in _STEP_HANDLERS.items():
        if step_type in step:
            return bool(handler(step, name, enable_logging))
    return True


def _run_steps(steps: list, enable_logging: bool) -> None:
    for step in steps:
        if not _dispatch_step(step, step.get("name"), enable_logging):
            return


def execute_yaml(stream: str, yaml_type: str = "File"):
    yaml_data = _load_yaml(stream, yaml_type)

    enable_logging = set_logger(yaml_data=yaml_data)
    recording, recorder = _setup_recorder(yaml_data)

    try:
        steps = _extract_steps(yaml_data)
        if not _validate_steps(steps, enable_logging):
            return
        _run_steps(steps, enable_logging)
    except Exception as error:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"Error: {repr(error)}")
        raise error
    finally:
        _stop_recorder(recording, recorder)
