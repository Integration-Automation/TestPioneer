from test_pioneer.logging.loggin_instance import TestPioneerHandler, test_pioneer_logger


def set_logger(yaml_data: dict) -> bool:
    if "pioneer_log" in yaml_data.keys():
        enable_logging = True
        filename = yaml_data.get("pioneer_log")
        file_handler = TestPioneerHandler(filename=filename)
        test_pioneer_logger.addHandler(file_handler)
        return True
    return False