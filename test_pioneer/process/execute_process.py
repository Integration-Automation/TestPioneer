import shlex
import subprocess
import sys
from typing import Union

import psutil


class ExecuteProcess(object):
    def __init__(
            self,
            redirect_stdout: Union[str, subprocess.PIPE] = subprocess.PIPE,
            redirect_stderr: Union[str, subprocess.PIPE] = subprocess.PIPE,
    ):
        super().__init__()
        self.process: [subprocess.Popen, None] = None
        self.redirect_stdout: str = redirect_stdout
        self.redirect_stderr: str = redirect_stderr

    def start_process(self, shell_command):
        if sys.platform in ["win32", "cygwin", "msys"]:
            args = shell_command
        else:
            args = shlex.split(shell_command)
        if self.redirect_stdout:
            stdout_file = open(self.redirect_stdout, "w")
        else:
            stdout_file = subprocess.PIPE
        if self.redirect_stderr:
            stderr_file = open(self.redirect_stderr, "w")
        else:
            stderr_file = subprocess.PIPE
        self.process = subprocess.Popen(
            args=args,
            stdout=stdout_file,
            stderr=stderr_file,
            shell=True,
        )

    # exit program change run flag to false and clean read thread and queue and process
    def exit_program(self):
        try:
            process = psutil.Process(self.process.pid)
            for proc in process.children(recursive=True):
                proc.kill()
            process.kill()
        except psutil.NoSuchProcess:
            pass
