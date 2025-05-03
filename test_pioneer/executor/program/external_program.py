from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger
from test_pioneer.process.execute_process import ExecuteProcess
from test_pioneer.process.process_manager import process_manager_instance


def open_program(step: dict, name: str, enable_logging: bool = False) -> bool:
    if not isinstance(step.get("open_program"), str):
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"The 'open_program' parameter is not an str type: {step.get('open_program')}")
        return False
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
            return False
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
            message=f"Redirect stdout to: {step.get('redirect_stdout')}")
        redirect_stdout = step.get("redirect_stdout")

    if "redirect_stderr" in step.keys():
        if not isinstance(step.get("redirect_stderr"), str):
            step_log_check(
                enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
                message=f"The 'redirect_stderr' parameter is not an str type: {step.get('redirect_stderr')}")
            return False
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
    return True


def close_program(step: dict, enable_logging: bool = False) -> bool:
    if not isinstance(step.get("close_program"), str):
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="error",
            message=f"The 'close_program' parameter is not an str type: {step.get('close_program')}")
        return False
    step_log_check(
        enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
        message=f"Close program: {step.get('close_program')}")
    program_that_need_close = step.get("close_program")
    process_manager_instance.close_process(program_that_need_close)
    return True
