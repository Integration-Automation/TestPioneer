from pathlib import Path
from threading import Lock

from test_pioneer.exception.exceptions import ProjectException
from test_pioneer.exception.tags import cant_save_yaml_error
from test_pioneer.logging.loggin_instance import test_pioneer_logger
from test_pioneer.project.template.template import template_1_str


def create_dir(dir_name: str) -> None:
    """
    :param dir_name: create dir use dir name
    :return: None
    """
    Path(dir_name).mkdir(
        parents=True,
        exist_ok=True
    )


def create_template(parent_name: str, project_path: str = None) -> None:
    if project_path is None:
        project_path: str = str(Path.cwd())
    template_dir = Path(project_path + "/" + parent_name)
    lock = Lock()
    if template_dir.exists() and template_dir.is_dir():
        lock.acquire()
        try:
            with open(str(template_dir) + "/" + parent_name + ".yml", "w+") as file_to_write:
                file_to_write.write(template_1_str)
        except ProjectException:
            raise ProjectException(cant_save_yaml_error)
        finally:
            lock.release()


def create_template_dir(project_path: str = None, parent_name: str = ".TestPioneer") -> None:
    test_pioneer_logger.info(f"create_template_dir, project_path: {project_path}, parent_name: {parent_name}")
    if project_path is None:
        project_path: str = str(Path.cwd())
    create_dir(project_path + "/" + parent_name)
    create_template(parent_name)
