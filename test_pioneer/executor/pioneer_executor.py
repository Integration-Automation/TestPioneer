import time
from pathlib import Path

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


def execute_yaml(stream: str, yaml_type: str = "File"):
    recording = False
    recorder = None

    yaml_data = _load_yaml(stream, yaml_type)

    # Pre-check save log or not
    enable_logging = set_logger(yaml_data=yaml_data)
    if is_installed(package_name="je_auto_control"):
        from test_pioneer.executor.test_recorder.video_recoder import set_recorder
        recording, recorder = set_recorder(yaml_data=yaml_data)

    try:
        # Pre-check jobs
        if "jobs" not in yaml_data:
            raise YamlException("No jobs tag")
        if not isinstance(yaml_data.get("jobs"), dict):
            raise YamlException("jobs not a dict")

        # Pre-check steps
        steps = yaml_data["jobs"].get("steps")
        if not steps:
            raise YamlException("Steps tag is empty")

        if not _validate_steps(steps, enable_logging):
            return

        # Execute step actions
        for step in steps:
            name = step.get("name")
            for step_type, handler in _STEP_HANDLERS.items():
                if step_type in step:
                    if not handler(step, name, enable_logging):
                        return
                    break

    except Exception as error:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"Error: {repr(error)}")
        raise error
    finally:
        if is_installed(package_name="je_auto_control"):
            _stop_recorder(recording, recorder)
