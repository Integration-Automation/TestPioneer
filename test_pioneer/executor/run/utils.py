from typing import Tuple, Union, Callable

from test_pioneer.exception.exceptions import ExecutorException
from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger


def select_with_runner(step: dict, enable_logging: bool, mode: str = "run") -> Tuple[bool, Union[Callable, None]]:
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
        from os import environ
        environ["LOCUST_SKIP_MONKEY_PATCH"] = "1"
        if mode == "run":
            from je_load_density import execute_action as single_load_runner
            from je_web_runner import execute_action as single_web_runner
            from je_auto_control import execute_action as single_gui_runner
            from je_api_testka import execute_action as single_api_runner
            execute_with = {
                "gui-runner": single_gui_runner,
                "web-runner": single_api_runner,
                "api-runner": single_web_runner,
                "load-runner": single_load_runner
            }.get(with_tag)
        elif mode == "run_folder":
            from je_load_density import execute_files as multi_load_runner
            from je_web_runner import execute_files as multi_web_runner
            from je_auto_control import execute_files as multi_gui_runner
            from je_api_testka import execute_files as multi_api_runner
            execute_with = {
                "gui-runner": multi_gui_runner,
                "web-runner": multi_web_runner,
                "api-runner": multi_api_runner,
                "load-runner": multi_load_runner
            }.get(with_tag)
        else:
            execute_with = None
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