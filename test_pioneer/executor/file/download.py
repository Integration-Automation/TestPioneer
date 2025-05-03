from test_pioneer.logging.loggin_instance import test_pioneer_logger, step_log_check


def download_single_file(step: dict, name: str, enable_logging: bool = False) -> bool:
    file_url = step.get("download_file")
    file_name = step.get("file_name")
    from automation_file import download_file
    if file_url is None or file_name is None:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
            message=f"Please provide the file_url and download_file: {name}")
        return False
    if isinstance(file_url, str) is False or isinstance(file_name, str) is False:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
            message=f"Both file_url and download need to be of type str: {name}")
        return False
    download_file(file_url=file_url, file_name=file_name)
    return True
