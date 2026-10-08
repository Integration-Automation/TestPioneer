"""One workflow run: its ID, its artifact directory and the result being assembled.

``execute_yaml`` opens a session. The step handlers find it with ``current_session`` and report
their runner executions to it; a handler called on its own, outside ``execute_yaml``, finds no
session and behaves as it always did.

Nothing here may break a run: a directory that cannot be created or a file that cannot be
written becomes a warning on the result, never an exception.
"""
from __future__ import annotations

import os
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from pathlib import Path

from test_pioneer.artifacts.capture import tee_output
from test_pioneer.artifacts.context import (
    DEFAULT_ARTIFACTS_PATH,
    ENV_ARTIFACT_DIR,
    ENV_RUN_ID,
    KEEP_ALWAYS,
    KEEP_ON_FAILURE,
    KEEP_POLICIES,
    checked_run_id,
    new_run_id,
)
from test_pioneer.artifacts.store import ArtifactStore
from test_pioneer.logging.loggin_instance import reset_step_log_sink, set_step_log_sink
from test_pioneer.models.result import RunnerResult, RunResult, Status, StepResult, utc_now, worst_status
from test_pioneer.schema.spec import ACTION_KEYS
from test_pioneer.utils.exception.exceptions import YamlException

_RUNNER_ACTIONS = ("run", "run_folder")


@dataclass(frozen=True)
class RunOptions:
    """Settings of one run. A field left at ``None`` is read from the workflow, then defaulted.

    ``run_id`` names the run; one is generated when it is not given. ``artifacts_path`` is the
    directory that receives ``<run-id>/`` (default ``artifacts``). ``keep_artifacts`` is
    ``on_failure`` (default: a run that passed leaves nothing, a failed one keeps the artifacts
    of what failed), ``always`` or ``never``.
    """

    run_id: str | None = None
    artifacts_path: str | None = None
    keep_artifacts: str | None = None


@dataclass
class Invocation:
    """A runner execution in progress: where it may write and what its environment adds."""

    result: RunnerResult
    directory: Path | None
    environment: dict[str, str]
    started: float = field(default_factory=time.monotonic)


def _setting(chosen: str | None, yaml_data: Mapping[str, object], key: str, default: str) -> str:
    """Pick a setting: the option, else the workflow's top-level key, else the default."""
    if chosen is not None:
        return chosen
    value = yaml_data.get(key)
    if value is None:
        return default
    if not isinstance(value, str) or not value:
        raise YamlException(f"{key} must be a non-empty string, got: {value!r}")
    return value


def _action_of(step: Mapping[str, object]) -> str:
    """Name the action the executor dispatches for a step: its first action key."""
    return next((key for key in ACTION_KEYS if key in step), "none")


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


_CURRENT: ContextVar[RunSession | None] = ContextVar("test_pioneer_run_session", default=None)


def current_session() -> RunSession | None:
    """Return the session of the ``execute_yaml`` call in progress, if there is one."""
    return _CURRENT.get()


class RunSession:
    """Collects what happens between the start and the end of one ``execute_yaml`` call."""

    def __init__(self, yaml_data: Mapping[str, object], options: RunOptions | None = None,
                 workflow: str | None = None) -> None:
        options = options or RunOptions()
        self._keep = _setting(options.keep_artifacts, yaml_data, "keep_artifacts", KEEP_ON_FAILURE)
        if self._keep not in KEEP_POLICIES:
            raise YamlException(f"keep_artifacts must be one of {', '.join(KEEP_POLICIES)}, got: {self._keep!r}")
        run_id = checked_run_id(options.run_id) if options.run_id is not None else new_run_id()
        root = _setting(options.artifacts_path, yaml_data, "artifacts_path", DEFAULT_ARTIFACTS_PATH)
        self.result = RunResult(run_id=run_id, workflow=workflow)
        self._store: ArtifactStore | None = ArtifactStore(Path(root), run_id)
        self._started = time.monotonic()
        self._step: StepResult | None = None
        self._errors: list[str] = []
        self._tokens: tuple[Token[RunSession | None], Token[Callable[[str, str], None] | None]] | None = None

    def __enter__(self) -> None:
        self.result.started_at = utc_now()
        self._started = time.monotonic()
        self._open_store()
        self._tokens = (_CURRENT.set(self), set_step_log_sink(self.log))
        self.log("info", f"Run {self.result.run_id} started: {self.result.workflow or 'inline YAML'}")

    def __exit__(self, exc_type: object, error: BaseException | None, traceback: object) -> None:
        if isinstance(error, KeyboardInterrupt):
            self.result.message = "interrupted"
            self.result.status = Status.CANCELLED
        elif error is not None:
            self.fail(repr(error))
        if self._tokens is not None:
            _CURRENT.reset(self._tokens[0])
            reset_step_log_sink(self._tokens[1])
            self._tokens = None
        self._close()

    def _warn(self, message: str) -> None:
        self.result.warnings.append(message)

    def _open_store(self) -> None:
        if self._store is None:
            return
        try:
            self._store.create()
        except OSError as error:
            self._warn(f"artifacts are not collected: {error}")
            self._store = None

    def log(self, level: str, message: str) -> None:
        """Add a line to the run's execution log; an error also becomes part of the step's message."""
        if level == "error":
            self._errors.append(message)
        if self._store is None:
            return
        try:
            self._store.log(f"{utc_now()} | {level.upper()} | {message}")
        except OSError as error:
            self._warn(f"the execution log stopped: {error}")
            self._stop_log(self._store)

    def _stop_log(self, store: ArtifactStore) -> None:
        try:
            store.close_log()
        except OSError as error:
            self._warn(f"the execution log was not closed cleanly: {error}")

    def fail(self, message: str | None = None) -> None:
        """Mark the run as failed for a reason that belongs to no step.

        Without a message the reason is the error that was logged last.
        """
        if message is None:
            message = self._errors[-1] if self._errors else "the run failed"
        else:
            self.log("error", message)
        if self.result.message is None:
            self.result.message = message
        self.result.status = Status.ERROR

    def run_step(self, step: Mapping[str, object], call: Callable[[], bool]) -> bool:
        """Run one step through ``call`` and record its outcome; an exception passes through."""
        record = StepResult(str(step.get("name")), _action_of(step), Status.PASSED, started_at=utc_now())
        self.result.steps.append(record)
        self._step, self._errors = record, []
        first_runner = len(self.result.runners)
        started = time.monotonic()
        self.log("info", f"Step {record.name!r} ({record.action}) started")
        try:
            succeeded = call()
            record.status = Status.PASSED if succeeded else Status.FAILED
            if not succeeded and first_runner == len(self.result.runners):
                self._add_runner_that_never_started(step, record)
        except KeyboardInterrupt:
            record.status = Status.CANCELLED
            raise
        except Exception as error:
            record.status = Status.ERROR
            self._errors.append(repr(error))
            raise
        finally:
            self._end_step(record, started, self.result.runners[first_runner:])
        return succeeded

    def _add_runner_that_never_started(self, step: Mapping[str, object], record: StepResult) -> None:
        """Give a ``run``/``run_folder`` step that was refused its runner entry, as an error."""
        if record.action not in _RUNNER_ACTIONS:
            return
        now = utc_now()
        self.result.runners.append(RunnerResult(
            runner=str(step.get("with")), script=str(step.get(record.action)), step=record.name,
            status=Status.ERROR, started_at=record.started_at, finished_at=now,
            message="; ".join(self._errors) or "the runner was not started"))

    def _end_step(self, record: StepResult, started: float, runners: list[RunnerResult]) -> None:
        record.status = worst_status([record.status, *(runner.status for runner in runners)])
        record.finished_at = utc_now()
        record.duration_ms = _elapsed_ms(started)
        if record.status is not Status.PASSED:
            record.message = "; ".join(self._errors) or None
        self._step = None
        self.log("info", f"Step {record.name!r} finished: {record.status.value} in {record.duration_ms} ms")

    def cancel(self, steps: Iterable[Mapping[str, object]]) -> None:
        """Record the steps that never ran because the run stopped before them."""
        for step in steps:
            self.result.steps.append(StepResult(str(step.get("name")), _action_of(step), Status.CANCELLED))

    def begin(self, runner: str, script: str, part: int | None = None) -> Invocation:
        """Start recording a runner execution and give it a directory of its own.

        ``part`` numbers the entries of one ``parallel_run`` step.
        """
        step = self._step.name if self._step is not None else ""
        record = RunnerResult(runner, script, step, Status.ERROR, started_at=utc_now())
        directory = self._new_runner_dir(runner, step if part is None else f"{step}-{part}")
        environment = {ENV_RUN_ID: self.result.run_id}
        if directory is not None and self._store is not None:
            record.artifact_dir = self._store.relative(directory)
            environment[ENV_ARTIFACT_DIR] = str(directory.resolve())
        self.result.runners.append(record)
        return Invocation(record, directory, environment)

    def _new_runner_dir(self, runner: str, label: str) -> Path | None:
        if self._store is None:
            return None
        try:
            return self._store.new_runner_dir(runner, label)
        except OSError as error:
            self._warn(f"no artifact directory for {runner}: {error}")
            return None

    def end(self, invocation: Invocation, status: Status, exit_code: int | None = None,
            message: str | None = None) -> None:
        """Finish recording a runner execution."""
        record = invocation.result
        record.status, record.exit_code, record.message = status, exit_code, message
        record.finished_at = utc_now()
        record.duration_ms = _elapsed_ms(invocation.started)
        level = "info" if status is Status.PASSED else "error"
        detail = f": {message}" if message else ""
        self.log(level, f"Runner {record.runner} ({record.script}) {status.value}{detail}")

    def reject(self, runner: str, script: str, message: str) -> None:
        """Record a runner execution that could not start; the caller has already logged why."""
        now = utc_now()
        step = self._step.name if self._step is not None else ""
        self.result.runners.append(RunnerResult(
            runner, script, step, Status.ERROR, started_at=now, finished_at=now, message=message))

    def _close(self) -> None:
        result = self.result
        # result.status already holds what fail() or an interruption set; the steps can only worsen it.
        result.status = worst_status([result.status, *(step.status for step in result.steps)])
        result.finished_at = utc_now()
        result.duration_ms = _elapsed_ms(self._started)
        self.log("info", f"Run {result.run_id} finished: {result.status.value}")
        if self._store is not None:
            self._stop_log(self._store)
            self._settle_artifacts(self._store)

    def _settle_artifacts(self, store: ArtifactStore) -> None:
        """Apply the keep policy, list what is kept and write the manifest."""
        failed = self.result.status is not Status.PASSED
        keep_run = self._keep == KEEP_ALWAYS or (self._keep == KEEP_ON_FAILURE and failed)
        try:
            if not keep_run:
                for runner in self.result.runners:
                    runner.artifact_dir = None
                store.remove_run()
                return
            for runner in self.result.runners:
                self._settle_runner(store, runner)
            self.result.artifact_dir = str(store.run_dir)
            store.write_manifest(self.result)
        except OSError as error:
            self._warn(f"artifact collection failed: {error}")

    def _settle_runner(self, store: ArtifactStore, runner: RunnerResult) -> None:
        if runner.artifact_dir is None:
            return
        directory = store.run_dir / runner.artifact_dir
        try:
            if self._keep == KEEP_ALWAYS or runner.status is not Status.PASSED:
                runner.artifacts = store.collect(directory)
            else:
                store.remove(directory)
                runner.artifact_dir = None
        except OSError as error:
            self._warn(f"artifact collection failed for {runner.runner} ({runner.script}): {error}")


@contextmanager
def _environment(values: Mapping[str, str]) -> Iterator[None]:
    """Set environment variables for the length of the block, then put the old values back."""
    previous = {name: os.environ.get(name) for name in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for name, old in previous.items():
            if old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old


@contextmanager
def in_process_runner(runner: str, script: str) -> Iterator[None]:
    """Record a runner call made in this process: its timing, its outcome and what it prints.

    The runner sees ``TEST_PIONEER_RUN_ID`` and ``TEST_PIONEER_ARTIFACT_DIR`` while it runs.
    Outside ``execute_yaml`` this does nothing.
    """
    session = current_session()
    if session is None:
        yield
        return
    invocation = session.begin(runner, script)
    try:
        with _environment(invocation.environment), tee_output(invocation.directory):
            yield
    except KeyboardInterrupt:
        session.end(invocation, Status.CANCELLED)
        raise
    except Exception as error:
        # The runners report a failed action in their own records, not by raising, so an
        # exception here means the call could not be completed.
        session.end(invocation, Status.ERROR, message=repr(error))
        raise
    session.end(invocation, Status.PASSED)
