import shlex
import subprocess
import sys
from typing import Union, Optional

import psutil


class ExecuteProcess:
    """
    A class to start and manage external processes.
    用來啟動並管理外部子程序的類別。
    """

    def __init__(
        self,
        redirect_stdout: Union[str, int] = subprocess.PIPE,
        redirect_stderr: Union[str, int] = subprocess.PIPE,
    ):
        """
        Args:
            redirect_stdout (Union[str, int]): Path to stdout file or PIPE.
                                               標準輸出重定向檔案路徑或 PIPE。
            redirect_stderr (Union[str, int]): Path to stderr file or PIPE.
                                               標準錯誤輸出重定向檔案路徑或 PIPE。
        """
        super().__init__()
        self.process: Optional[subprocess.Popen] = None
        self.redirect_stdout: Union[str, int] = redirect_stdout
        self.redirect_stderr: Union[str, int] = redirect_stderr

    def start_process(self, shell_command: str) -> None:
        """
        Start a subprocess with given shell command.
        使用指定的 shell 命令啟動子程序。

        Args:
            shell_command (str): Command to execute. 要執行的命令字串。
        """
        # Windows 平台直接使用字串，其他平台用 shlex.split
        if sys.platform in ["win32", "cygwin", "msys"]:
            args = shell_command
        else:
            args = shlex.split(shell_command)

        # 設定 stdout 重定向
        if isinstance(self.redirect_stdout, str):
            stdout_file = open(self.redirect_stdout, "w")
        else:
            stdout_file = subprocess.PIPE

        # 設定 stderr 重定向
        if isinstance(self.redirect_stderr, str):
            stderr_file = open(self.redirect_stderr, "w")
        else:
            stderr_file = subprocess.PIPE

        # 建立子程序
        self.process = subprocess.Popen(
            args=args,
            stdout=stdout_file,
            stderr=stderr_file,
            shell=True,  # 注意：使用 shell=True 可能有安全風險
        )

    def exit_program(self) -> None:
        """
        Terminate the process and all its children.
        終止子程序及其所有子程序。
        """
        if not self.process:
            return
        try:
            process = psutil.Process(self.process.pid)
            for proc in process.children(recursive=True):
                proc.kill()
            process.kill()
        except psutil.NoSuchProcess:
            pass