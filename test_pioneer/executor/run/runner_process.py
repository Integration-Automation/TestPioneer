"""One runner sub-process of ``parallel_run`` and what is recorded about it.

Inside ``execute_yaml`` the process gets the artifact environment, writes its output to
``stdout.log`` and ``stderr.log`` in its artifact directory (still shown on the console), and its
exit code and timing go into the run result. Outside ``execute_yaml`` it is started as it always
was, with the parent's streams.
"""
from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from test_pioneer.artifacts.capture import STDERR_LOG, STDOUT_LOG, LogEcho, drop_if_empty
from test_pioneer.artifacts.session import Invocation, RunSession, current_session
from test_pioneer.logging.loggin_instance import test_pioneer_logger
from test_pioneer.models.result import Status


@dataclass(frozen=True)
class RunnerRequest:
    """One entry of a ``parallel_run`` step: a runner, its script, its position and its artifacts.

    ``script`` and ``artifacts`` are kept as the workflow wrote them.
    """

    runner: str
    script: str
    part: int
    artifacts: object = None


@dataclass(eq=False)
class RunnerProcess:
    """A started runner process with its log files and its entry in the run result."""

    process: subprocess.Popen[bytes]
    session: RunSession | None = None
    invocation: Invocation | None = None
    handles: list[BinaryIO] = field(default_factory=list)
    echoes: list[LogEcho] = field(default_factory=list)

    def pump(self) -> None:
        """Copy the output written so far onto this process's console."""
        for echo in self.echoes:
            echo.pump()

    def finished(self) -> bool:
        """True once the process has exited."""
        self.process.poll()
        return self.process.returncode is not None

    def _release(self) -> None:
        for handle in self.handles:
            handle.close()
        for echo in self.echoes:
            echo.close()
            drop_if_empty(echo.path)
        self.handles, self.echoes = [], []

    def close(self) -> None:
        """Record the exit code of a finished process: zero passed, anything else failed."""
        self._release()
        if self.session is None or self.invocation is None:
            return
        code = self.process.returncode
        if code == 0:
            self.session.end(self.invocation, Status.PASSED, exit_code=code)
        else:
            self.session.end(self.invocation, Status.FAILED, exit_code=code, message=f"exit code {code}")

    def cancel(self) -> None:
        """Stop a process that is still running because the wait was interrupted."""
        try:
            self.process.terminate()
        except OSError as error:
            test_pioneer_logger.debug("Failed to terminate process %s: %s", self.process.pid, error)
        self._release()
        if self.session is not None and self.invocation is not None:
            self.session.end(self.invocation, Status.CANCELLED, message="interrupted")


def _open_logs(directory: Path | None) -> tuple[list[BinaryIO], list[LogEcho]]:
    """Open the two log files of a sub-process and the echoes that copy them to the console."""
    if directory is None:
        return [], []
    handles: list[BinaryIO] = []
    echoes: list[LogEcho] = []
    try:
        for name, stream in ((STDOUT_LOG, sys.stdout), (STDERR_LOG, sys.stderr)):
            handles.append((directory / name).open("wb"))
            echoes.append(LogEcho(directory / name, stream))
    except OSError as error:
        test_pioneer_logger.debug("Output is not captured in %s: %s", directory, error)
        _close_all(handles, echoes)
        return [], []
    return handles, echoes


def _close_all(handles: list[BinaryIO], echoes: list[LogEcho]) -> None:
    for handle in handles:
        handle.close()
    for echo in echoes:
        echo.close()


def _spawn(commands: list[str], environment: Mapping[str, str] | None = None,
           logs: Sequence[BinaryIO] = ()) -> subprocess.Popen[bytes]:
    """Start the process; without ``logs`` and ``environment`` it inherits this process's.

    The command is an argument list, never a shell string.
    """
    stdout, stderr = logs if logs else (None, None)
    # The caller waits for the process and closes its streams, so it is not used as a context manager.
    return subprocess.Popen(  # nosec B603  # pylint: disable=consider-using-with
        commands, stdout=stdout, stderr=stderr, env=environment)


def start_runner_process(commands: list[str], request: RunnerRequest) -> RunnerProcess:
    """Start the runner of ``request`` with ``commands``. Raises ``OSError`` if it cannot start."""
    session = current_session()
    if session is None:
        return RunnerProcess(_spawn(commands))
    invocation = session.begin(request.runner, request.script, request.part, request.artifacts)
    handles, echoes = _open_logs(invocation.directory)
    try:
        process = _spawn(commands, {**os.environ, **invocation.environment}, handles)
    except OSError as error:
        _close_all(handles, echoes)
        session.end(invocation, Status.ERROR, message=f"could not start: {error}")
        raise
    return RunnerProcess(process, session, invocation, handles, echoes)
