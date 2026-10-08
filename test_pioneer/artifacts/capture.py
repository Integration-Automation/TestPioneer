"""Keep a runner's console output as a log file without taking it off the console.

An in-process runner prints through ``sys.stdout``/``sys.stderr``, so those are wrapped for the
length of the call. A runner sub-process writes straight to its log files, and the lines are
copied onto this process's streams while it is waited for. Neither way uses a thread.
"""
from __future__ import annotations

import codecs
import locale
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, TextIO

from test_pioneer.logging.loggin_instance import test_pioneer_logger

STDOUT_LOG = "stdout.log"
STDERR_LOG = "stderr.log"


class _Tee:
    """A text stream that also appends what is written to a log file."""

    def __init__(self, stream: TextIO, log: TextIO) -> None:
        self._stream = stream
        self._log = log

    def write(self, text: str) -> int:
        """Write to the original stream, and to the log while it is still open."""
        # A logging handler created during the call may keep this object after the log is closed.
        if not self._log.closed:
            self._log.write(text)
        return self._stream.write(text)

    def flush(self) -> None:
        """Flush both destinations."""
        if not self._log.closed:
            self._log.flush()
        self._stream.flush()

    def __getattr__(self, name: str) -> object:
        # Everything else (encoding, isatty, fileno, buffer) is the original stream's.
        return getattr(self._stream, name)


def drop_if_empty(path: Path) -> None:
    """Remove a log file that received nothing."""
    try:
        if path.stat().st_size == 0:
            path.unlink()
    except OSError as error:
        test_pioneer_logger.debug("Could not remove the empty log %s: %s", path, error)


def _open_logs(directory: Path | None) -> tuple[TextIO, TextIO] | None:
    """Open ``stdout.log`` and ``stderr.log`` in ``directory``; ``None`` when that is not possible."""
    if directory is None:
        return None
    try:
        out_log = (directory / STDOUT_LOG).open("w", encoding="utf-8", errors="backslashreplace")
    except OSError as error:
        test_pioneer_logger.debug("Output is not captured in %s: %s", directory, error)
        return None
    try:
        err_log = (directory / STDERR_LOG).open("w", encoding="utf-8", errors="backslashreplace")
    except OSError as error:
        out_log.close()
        test_pioneer_logger.debug("Output is not captured in %s: %s", directory, error)
        return None
    return out_log, err_log


@contextmanager
def tee_output(directory: Path | None) -> Iterator[None]:
    """Copy ``sys.stdout`` and ``sys.stderr`` into ``stdout.log`` and ``stderr.log`` of ``directory``.

    With no directory nothing is captured.
    """
    logs = _open_logs(directory)
    if logs is None:
        yield
        return
    original = sys.stdout, sys.stderr
    tees = _Tee(sys.stdout, logs[0]), _Tee(sys.stderr, logs[1])
    sys.stdout, sys.stderr = tees
    try:
        yield
    finally:
        # Restore only what is still ours: the call may have replaced a stream itself.
        if sys.stdout is tees[0]:
            sys.stdout = original[0]
        if sys.stderr is tees[1]:
            sys.stderr = original[1]
        for log in logs:
            log.close()
            drop_if_empty(Path(log.name))


class LogEcho:
    """Copies what a sub-process appends to its log file onto one of this process's streams."""

    def __init__(self, path: Path, stream: TextIO) -> None:
        self.path = path
        self._handle: BinaryIO = path.open("rb")
        self._stream = stream
        self._decoder = codecs.getincrementaldecoder(locale.getpreferredencoding(False))(errors="replace")

    def pump(self) -> None:
        """Copy the bytes written since the last call."""
        data = self._handle.read()
        if not data:
            return
        binary = getattr(self._stream, "buffer", None)
        if binary is not None:
            # Byte for byte, as if the sub-process had inherited the stream.
            self._stream.flush()
            binary.write(data)
            binary.flush()
        else:
            self._stream.write(self._decoder.decode(data))
            self._stream.flush()

    def close(self) -> None:
        """Copy what is left and release the file."""
        self.pump()
        self._handle.close()
