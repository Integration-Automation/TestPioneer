import time

from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger


def blocked_wait(step: dict, enable_logging: bool, ) -> bool:
    if not isinstance(step.get("wait"), int):
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
            message=f"The 'wait' parameter is not an int type: {step.get('wait')}")
        return False
    step_log_check(
        enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
        message=f"Wait seconds: {step.get('wait')}")
    time.sleep((step.get("wait")))
    return True
