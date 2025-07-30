from test_pioneer.logging.loggin_instance import test_pioneer_logger, step_log_check


def download_single_file(step: dict, enable_logging: bool = False) -> bool:
    file_url = step.get("download_file")
    file_path = step.get("file_path")
    from automation_file import download_file
    if file_url is None or file_path is None:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
            message=f"Please provide the file_url and download_file")
        return False
    if isinstance(file_url, str) is False or isinstance(file_path, str) is False:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
            message=f"Both file_url and download need to be of type str")
        return False
    download_file(file_url=file_url, file_name=file_path)
    return True


def unzip_zipfile(step: dict, enable_logging: bool = False) -> bool:
    zip_file_path = step.get("zip_file_path")
    password = step.get("password")
    extract_path = step.get("extract_path")
    if zip_file_path is None:
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
            message=f"Please provide the zip_file_path")
        return False
    if not isinstance(zip_file_path, str):
        step_log_check(
            enable_logging=enable_logging, logger=test_pioneer_logger, level="info",
            message=f"zip_file_path need to be of type str")
        return False

    from automation_file import unzip_all
    kwargs = {
        "zip_file_path": zip_file_path,
    }
    if password:
        kwargs["password"] = password
    if extract_path:
        kwargs["extract_path"] = extract_path

    unzip_all(**kwargs)

    return True
