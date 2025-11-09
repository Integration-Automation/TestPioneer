from __future__ import annotations

from typing import Set, Dict, TYPE_CHECKING
from test_pioneer.logging.loggin_instance import test_pioneer_logger

if TYPE_CHECKING:
    from test_pioneer.process.execute_process import ExecuteProcess


class ProcessManager:
    """
    Manage multiple ExecuteProcess instances.
    管理多個 ExecuteProcess 實例。
    """

    def __init__(self) -> None:
        # Set of process names
        # 儲存程序名稱的集合
        self.name_set: Set[str] = set()

        # Dictionary mapping process name to ExecuteProcess instance
        # 將程序名稱映射到 ExecuteProcess 實例的字典
        self.process_dict: Dict[str, ExecuteProcess] = {}

    def close_process(self, job_name: str) -> None:
        """
        Close a process by its job name.
        根據程序名稱關閉對應的子程序。

        Args:
            job_name (str): The name of the process to close.
                            要關閉的程序名稱。
        """
        execute_process = self.process_dict.get(job_name)
        if execute_process is None:
            test_pioneer_logger.error(f"Process not found: {job_name}")
        else:
            execute_process.exit_program()
            # 移除已關閉的程序
            self.process_dict.pop(job_name, None)
            self.name_set.discard(job_name)


# Global instance of ProcessManager
# 全域的 ProcessManager 實例
process_manager_instance = ProcessManager()