import json
import os
import time
import webbrowser
from pathlib import Path
from typing import Tuple, Callable, Union

import yaml
from je_auto_control import RecordingThread

from test_pioneer.exception.exceptions import WrongInputException, YamlException, ExecutorException
from test_pioneer.logging.loggin_instance import TestPioneerHandler, step_log_check, test_pioneer_logger
from test_pioneer.process.execute_process import ExecuteProcess
from test_pioneer.process.process_manager import process_manager_instance


def check_with(step: dict, enable_logging: bool) -> Tuple[bool, Union[Callable, None]]:
    if step.get("with", None) is None:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"Step need with tag")
        return False, None
    with_tag = step.get("with")
    if not isinstance(with_tag, str):
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"The 'with' parameter is not an str type: {with_tag}")
        return False, None
    try:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
            message=f"Run with: {step.get('with')}, path: {step.get('run')}")
        from je_web_runner import execute_action as web_runner
        from gevent.monkey import patch_all
        patch_all()
        from je_load_density import execute_action as load_runner
        from je_auto_control import execute_action as gui_runner
        from je_api_testka import execute_action as api_runner
        execute_with = {
            "gui-runner": gui_runner,
            "web-runner": api_runner,
            "api-runner": web_runner,
            "load-runner": load_runner
        }.get(with_tag)
        if execute_with is None:
            step_log_check(
                enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                message=f"with using the wrong runner tag: {step.get('with')}")
            return False, None
    except ExecutorException as error:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"Run with: {step.get('with')}, path: {step.get('run')}, error: {repr(error)}")
        return False, None
    return True, execute_with


def execute_yaml(stream: str, yaml_type: str = "File"):
    if yaml_type == "File":
        file = open(stream, "r").read()
        yaml_data = yaml.safe_load(stream=file)
    elif yaml_type == "String":
        yaml_data = yaml.safe_load(stream=stream)
    else:
        raise WrongInputException("Wrong input: " + repr(stream))
    # Variable
    enable_logging: bool = False
    # Pre-check data structure
    if isinstance(yaml_data, dict) is False:
        raise YamlException(f"Not a dict: {yaml_data}")

    # Pre-check log or no
    if "pioneer_log" in yaml_data.keys():
        enable_logging = True
        filename = yaml_data.get("pioneer_log")
        file_handler = TestPioneerHandler(filename=filename)
        test_pioneer_logger.addHandler(file_handler)

    recoder= None
    recording: bool = False
    # Pre-check recoding or no
    if "recording_path" in yaml_data.keys():
        if isinstance(yaml_data.get("recording_path"), str) is False:
            raise ExecutorException(f"recording_path not a str: {yaml_data.get('recording_path')}")
        import sys
        if 'threading' in sys.modules:
            del sys.modules['threading']
        from gevent.monkey import patch_thread
        patch_thread()
        recording = True
        recoder = RecordingThread()
        recoder.video_name = yaml_data.get("recording_path")
        recoder.daemon = True
        recoder.start()

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

        # Pre-check name have duplicate or not
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
                check_with_data = check_with(step, enable_logging=enable_logging)
                if check_with_data[0] is False:
                    break
                else:
                    execute_with = check_with_data[1]
                file = step.get("run")
                file = str(Path(os.getcwd() + file).absolute())
                if file is None:
                    step_log_check(
                        enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                        message=f"run param need file path: {step.get('run')}")
                    break
                if (Path(file).is_file() is False and Path(file).is_dir() is False) or not Path(file).exists():
                    step_log_check(
                        enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                        message=f"not file path or dir: {step.get('run')}")
                    break
                file = json.loads(Path(file).read_text())
                execute_with(file)

            if "open_url" in step.keys():
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

            if "wait" in step.keys():
                if not isinstance(step.get("wait"), int):
                    step_log_check(
                        enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
                        message=f"The 'wait' parameter is not an int type: {step.get('wait')}")
                    break
                step_log_check(
                    enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
                    message=f"Wait seconds: {step.get('wait')}")
                time.sleep((step.get("wait")))

            if "open_program" in step.keys():
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

            if "close_program" in step.keys():
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