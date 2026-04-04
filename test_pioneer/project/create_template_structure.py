from pathlib import Path
from threading import Lock

from test_pioneer.logging.loggin_instance import test_pioneer_logger
from test_pioneer.project.template.template import template_1_str
from test_pioneer.utils.exception.exceptions import ProjectException
from test_pioneer.utils.exception.tags import cant_save_yaml_error

# Module-level lock for thread safety across calls
# 模組層級的鎖，確保跨呼叫的執行緒安全
_template_lock = Lock()


def create_dir(dir_name: str) -> None:
    """
    Create a directory with the given name.
    建立指定名稱的資料夾。

    Args:
        dir_name (str): Directory name to create. 要建立的資料夾名稱。
    """
    Path(dir_name).mkdir(parents=True, exist_ok=True)


def create_template(parent_name: str, project_path: str | None = None) -> None:
    """
    Create a template YAML file inside the given project path.
    在指定的專案路徑中建立範本 YAML 檔案。

    Args:
        parent_name (str): Parent directory name. 父資料夾名稱。
        project_path (str | None): Project path, defaults to current working directory.
                                   專案路徑，預設為目前工作目錄。
    """
    if project_path is None:
        project_path = str(Path.cwd())

    template_dir = Path(project_path) / parent_name

    if template_dir.exists() and template_dir.is_dir():
        with _template_lock:
            try:
                file_path = template_dir / f"{parent_name}.yml"
                with file_path.open("w", encoding="utf-8") as file_to_write:
                    file_to_write.write(template_1_str)
            except Exception as error:
                raise ProjectException(f"{cant_save_yaml_error}: {error}")


def create_template_dir(project_path: str | None = None, parent_name: str = ".TestPioneer") -> None:
    """
    Create a template directory and YAML file.
    建立範本資料夾與 YAML 檔案。

    Args:
        project_path (str | None): Project path, defaults to current working directory.
                                   專案路徑，預設為目前工作目錄。
        parent_name (str): Parent directory name, defaults to ".TestPioneer".
                           父資料夾名稱，預設為 ".TestPioneer"。
    """
    test_pioneer_logger.info(
        f"create_template_dir, project_path: {project_path}, parent_name: {parent_name}"
    )

    if project_path is None:
        project_path = str(Path.cwd())

    # 建立資料夾
    create_dir(str(Path(project_path) / parent_name))

    # 建立範本檔案
    create_template(parent_name, project_path)