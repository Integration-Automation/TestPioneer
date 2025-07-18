import webbrowser

from test_pioneer.utils.exception.exceptions import ExecutorException
from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger


def open_url(step: dict, enable_logging: bool = False) -> bool:
    if not isinstance(step.get("open_url"), str):
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"The 'open_url' parameter is not an str type: {step.get('open_url')}")
        return False
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
            return False
        url_open_method(url=open_url)
    except ExecutorException as error:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"Open URL {step.get('open_url')}, error: {repr(error)}")
    return True