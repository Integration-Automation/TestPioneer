from typing import List
import subprocess

from test_pioneer.logging.loggin_instance import test_pioneer_logger


class ProcessManager:
    """
    A simple process manager to track and manage subprocesses.
    簡單的程序管理器，用來追蹤與管理子程序。
    """

    def __init__(self) -> None:
        # List to store subprocess.Popen objects
        # 用來存放 subprocess.Popen 物件的清單
        self.process_list: List[subprocess.Popen] = []

    def add_process(self, process: subprocess.Popen) -> None:
        """
        Add a subprocess to the manager.
        將子程序加入管理器。
        """
        self.process_list.append(process)

    def remove_process(self, process: subprocess.Popen) -> None:
        """
        Remove a subprocess from the manager.
        從管理器移除子程序。
        """
        if process in self.process_list:
            self.process_list.remove(process)

    def cleanup_finished(self) -> None:
        """
        Remove finished processes from the list.
        移除已結束的子程序。
        """
        for proc in list(self.process_list):  # 使用 list 避免迭代時修改
            proc.poll()
            if proc.returncode is not None:
                self.process_list.remove(proc)

    def terminate_all(self) -> None:
        """
        Terminate all running processes.
        終止所有正在執行的子程序。
        """
        for proc in self.process_list:
            try:
                proc.terminate()
            except OSError as exc:
                test_pioneer_logger.debug("Failed to terminate process %s: %s", proc.pid, exc)
        self.process_list.clear()


# Global instance of ProcessManager
# 全域的 ProcessManager 實例
process_manager = ProcessManager()