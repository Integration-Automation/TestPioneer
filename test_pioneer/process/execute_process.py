import shlex
import subprocess
import sys
from typing import Union, Optional, List

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
        self._stdout_file = None
        self._stderr_file = None

    def start_process(self, shell_command: Union[str, List[str]]) -> None:
        """
        Start a subprocess with given command.
        使用指定的命令啟動子程序。

        Args:
            shell_command (Union[str, List[str]]): Command to execute as string or argument list.
                                                   要執行的命令字串或參數列表。
        """
        # Always pass argument list to subprocess; never use shell=True (command injection risk).
        # On Windows, split with posix=False to preserve backslash paths.
        if isinstance(shell_command, list):
            args = shell_command
        else:
            is_windows = sys.platform in ("win32", "cygwin", "msys")
            args = shlex.split(shell_command, posix=not is_windows)

        # 設定 stdout 重定向
        if isinstance(self.redirect_stdout, str):
            self._stdout_file = open(self.redirect_stdout, "w")
            stdout_target = self._stdout_file
        else:
            stdout_target = subprocess.PIPE

        # 設定 stderr 重定向
        if isinstance(self.redirect_stderr, str):
            self._stderr_file = open(self.redirect_stderr, "w")
            stderr_target = self._stderr_file
        else:
            stderr_target = subprocess.PIPE

        # 建立子程序
        self.process = subprocess.Popen(
            args=args,
            stdout=stdout_target,
            stderr=stderr_target,
            shell=False,
        )

    def exit_program(self) -> None:
        """
        Terminate the process and all its children, then close redirected file handles.
        終止子程序及其所有子程序，並關閉重定向的檔案處理器。
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
        finally:
            # Close redirected file handles
            # 關閉重定向的檔案處理器
            for f in (getattr(self, "_stdout_file", None), getattr(self, "_stderr_file", None)):
                if f is not None:
                    try:
                        f.close()
                    except OSError:
                        pass