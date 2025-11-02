import time

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


def execute_yaml(stream: str, yaml_type: str = "File"):
    recording = None
    recoder = None
    if yaml_type == "File":
        file = open(stream, "r").read()
        yaml_data = yaml.safe_load(stream=file)
    elif yaml_type == "String":
        yaml_data = yaml.safe_load(stream=stream)
    else:
        raise WrongInputException("Wrong input: " + repr(stream))
    # Pre-check data structure
    if not isinstance(yaml_data, dict):
        raise YamlException(f"Not a dict: {yaml_data}")

    # Pre-check save log or not
    enable_logging = set_logger(yaml_data=yaml_data)
    if is_installed(package_name="je_auto_control"):
        from test_pioneer.executor.test_recorder.video_recoder import set_recoder
        # Pre-check recording or not
        recording, recoder = set_recoder(yaml_data=yaml_data)

    try:
        # Pre-check jobs
        if "jobs" not in yaml_data.keys():
            raise YamlException("No jobs tag")
        if isinstance(yaml_data.get("jobs"), dict) is False:
            raise YamlException("jobs not a dict")

        # Pre-check steps
        steps = yaml_data.get("jobs").get("steps", None)
        if steps is None or len(steps) <= 0:
            raise YamlException("Steps tag is empty")

        pre_check_failed: bool = False

        # Pre-check the job name has a duplicate or not
        for step in steps:
            if step.get("name", None) is None:
                step_log_check(
                    enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                    message="Step need name tag")
                break
            name = step.get("name")
            if name in process_manager_instance.name_set:
                step_log_check(
                    enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                    message=f"job name duplicated: {name}")
                pre_check_failed = True
                break
            else:
                process_manager_instance.name_set.add(name)

        # Execute step action
        for step in steps:
            if pre_check_failed:
                break
            name = step.get("name")

            if "run" in step.keys():
                if not run(step=step, enable_logging=enable_logging):
                    break

            elif "run_folder" in step.keys():
                if not run_folder(step=step, enable_logging=enable_logging, mode="run_folder") is False:
                    break

            elif "open_url" in step.keys():
                if not open_url(step=step, enable_logging=enable_logging):
                    break

            elif "download_file" in step.keys():
                if not download_single_file(step=step, enable_logging=enable_logging):
                    break

            elif "wait" in step.keys():
                if not blocked_wait(step=step, enable_logging=enable_logging):
                    break

            elif "open_program" in step.keys():
                if not open_program(step=step, name=name, enable_logging=enable_logging):
                    break

            elif "close_program" in step.keys():
                if not close_program(step=step, enable_logging=enable_logging):
                    break

            elif "unzip_zipfile" in step.keys():
                if not unzip_zipfile(step=step, enable_logging=enable_logging):
                    break

            elif "parallel_run" in step.keys():
                if not parallel_run(step=step, enable_logging=enable_logging):
                    break

    except Exception as error:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"Error: {repr(error)}")
        if is_installed(package_name="je_auto_control"):
            if recording and recoder is not None:
                recoder.set_recoding_flag(False)
                while recoder.is_alive():
                    time.sleep(0.1)
        raise error
    if is_installed(package_name="je_auto_control"):
        if recording and recoder is not None:
            recoder.set_recoding_flag(False)
            while recoder.is_alive():
                time.sleep(0.1)
