import time
import webbrowser

import yaml
from je_auto_control import RecordingThread

from test_pioneer.exception.exceptions import WrongInputException, YamlException, ExecutorException
from test_pioneer.executor.run.executor_run import run
from test_pioneer.executor.run.executor_run_folder import run_folder
from test_pioneer.executor.test_recorder.logger import set_logger
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
    recording, recoder = set_logger(yaml_data=yaml_data)

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

        # Pre-check the jobs name has duplicate or not
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
                if run(step, enable_logging=enable_logging) is False:
                    break

            elif "run_folder" in step.keys():
                if run_folder(step, enable_logging=enable_logging, mode="run_folder") is False:
                    break

            elif "open_url" in step.keys():
                if not isinstance(step.get("open_url"), str):
                    step_log_check(
                        enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                        message=f"The 'open_url' parameter is not an str type: {step.get('open_url')}")
                    break
                step_log_check(
                    enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
                    message=f"Open url: {step.get('open_url')}")
                try:
                    open_url = step.get("open_url")
                    url_open_method = step.get("url_open_method")
                    url_open_method = {
                        "open": webbrowser.open,
                        "open_new": webbrowser.open_new,
                        "open_new_tab": webbrowser.open_new_tab,
                    }.get(url_open_method)
                    if url_open_method is None:
                        step_log_check(
                            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                            message=f"Using wrong url_open_method tag: {step.get('with')}")
                        break
                    url_open_method(url=open_url)
                except ExecutorException as error:
                    step_log_check(
                        enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                        message=f"Open URL {step.get('open_url')}, error: {repr(error)}")

            elif "download_file" in step.keys():
                file_url = step.get("download_file")
                file_name = step.get("file_name")
                from automation_file import download_file
                if file_url is None or file_name is None:
                    step_log_check(
                        enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
                        message=f"Please provide the file_url and download_file: {name}")
                    break
                if isinstance(file_url, str) is False or isinstance(file_name, str) is False:
                    step_log_check(
                        enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
                        message=f"Both file_url and download need to be of type str: {name}")
                    break
                download_file(file_url=file_url, file_name=file_name)

            elif "wait" in step.keys():
                if not isinstance(step.get("wait"), int):
                    step_log_check(
                        enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
                        message=f"The 'wait' parameter is not an int type: {step.get('wait')}")
                    break
                step_log_check(
                    enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
                    message=f"Wait seconds: {step.get('wait')}")
                time.sleep((step.get("wait")))

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