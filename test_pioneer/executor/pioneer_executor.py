import time

import yaml

from test_pioneer.exception.exceptions import WrongInputException, YamlException
from test_pioneer.executor.browser.url import open_url
from test_pioneer.executor.file.download import download_single_file
from test_pioneer.executor.run.executor_run import run
from test_pioneer.executor.run.executor_run_folder import run_folder
from test_pioneer.executor.test_recorder.logger import set_logger
from test_pioneer.executor.test_recorder.video_recoder import set_recoder
from test_pioneer.executor.time.wait import blocked_wait
from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger
from test_pioneer.process.execute_process import ExecuteProcess
from test_pioneer.process.process_manager import process_manager_instance


def execute_yaml(stream: str, yaml_type: str = "File"):
    if yaml_type == "File":
        file = open(stream, "r").read()
        yaml_data = yaml.safe_load(stream=file)
    elif yaml_type == "String":
        yaml_data = yaml.safe_load(stream=stream)
    else:
        raise WrongInputException("Wrong input: " + repr(stream))
    # Pre-check data structure
    if isinstance(yaml_data, dict) is False:
        raise YamlException(f"Not a dict: {yaml_data}")

    # Pre-check save log or not
    enable_logging = set_logger(yaml_data=yaml_data)
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
                    message=f"Step need name tag")
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
                if run(step=step, enable_logging=enable_logging) is False:
                    break

            elif "run_folder" in step.keys():
                if run_folder(step=step, enable_logging=enable_logging, mode="run_folder") is False:
                    break

            elif "open_url" in step.keys():
                if open_url(step=step, enable_logging=enable_logging):
                    break

            elif "download_file" in step.keys():
                if download_single_file(step=step, name=name, enable_logging=enable_logging):
                    break

            elif "wait" in step.keys():
                if blocked_wait(step=step, enable_logging=enable_logging) is False:
                    break

            elif "open_program" in step.keys():
                if not isinstance(step.get("open_program"), str):
                    step_log_check(
                        enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                        message=f"The 'open_program' parameter is not an str type: {step.get('open_program')}")
                    break
                step_log_check(
                    enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
                    message=f"Open program: {step.get('open_program')}")

                redirect_stdout = None
                redirect_error = None

                if "redirect_stdout" in step.keys():
                    if not isinstance(step.get("redirect_stdout"), str):
                        step_log_check(
                            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                            message=f"The 'redirect_stdout' parameter is not an str type: {step.get('redirect_stdout')}")
                        break
                    step_log_check(
                        enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
                        message=f"Redirect stdout to: {step.get('redirect_stdout')}")
                    redirect_stdout = step.get("redirect_stdout")

                if "redirect_stderr" in step.keys():
                    if not isinstance(step.get("redirect_stderr"), str):
                        step_log_check(
                            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                            message=f"The 'redirect_stderr' parameter is not an str type: {step.get('redirect_stderr')}")
                        break
                    step_log_check(
                        enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
                        message=f"Redirect stderr to: {step.get('redirect_stderr')}")
                    redirect_error = step.get("redirect_stdout")

                execute_process = ExecuteProcess()
                process_manager_instance.process_dict.update({name: execute_process})

                if redirect_error:
                    execute_process.redirect_stdout = redirect_stdout

                if redirect_error:
                    execute_process.redirect_stderr = redirect_error

                execute_process.start_process(step.get("open_program"))

            elif "close_program" in step.keys():
                if not isinstance(step.get("close_program"), str):
                    step_log_check(
                        enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                        message=f"The 'close_program' parameter is not an str type: {step.get('close_program')}")
                    break
                step_log_check(
                    enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
                    message=f"Close program: {step.get('close_program')}")
                close_program = step.get("close_program")
                process_manager_instance.close_process(close_program)

    except Exception as error:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"Error: {repr(error)}")
        if recording and recoder is not None:
            recoder.set_recoding_flag(False)
            while recoder.is_alive():
                time.sleep(0.1)
        raise error
    if recording and recoder is not None:
        recoder.set_recoding_flag(False)
        while recoder.is_alive():
            time.sleep(0.1)