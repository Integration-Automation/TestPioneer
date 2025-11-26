import importlib.util


def is_installed(package_name: str) -> bool:
    """
    Check if a Python package is installed.
    檢查指定的 Python 套件是否已安裝。

    Args:
        package_name (str): The name of the package to check.
                            要檢查的套件名稱。

    Returns:
        bool: True if the package is installed, False otherwise.
              若套件已安裝回傳 True，否則回傳 False。
    """
    spec = importlib.util.find_spec(package_name)
    return spec is not None