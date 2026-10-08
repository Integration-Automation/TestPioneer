"""Semantic rules for a workflow: what the JSON Schema cannot express.

An error is something the executor would stop on, or an action that can never run as written.
A warning depends on the machine (a missing script, a runner package that is not installed) or
is a leftover that the executor ignores.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from test_pioneer.artifacts.collect import pattern_refusal
from test_pioneer.logging.loggin_instance import test_pioneer_logger
from test_pioneer.models.diagnostic import Diagnostic, Severity, YamlPath, format_path
from test_pioneer.runner.registry import OPTIONAL_RUNNERS, RUNNER_PACKAGES
from test_pioneer.schema.spec import (
    ACTION_BY_KEY,
    ACTION_KEYS,
    JOBS_KEYS,
    PARALLEL_RUN_KEYS,
    STEP_FIELDS,
    STEP_KEYS,
    TOP_LEVEL_KEYS,
    ActionSpec,
)
from test_pioneer.utils.package.check import is_installed
from test_pioneer.validation.schema_validator import suggestion
from test_pioneer.validation.yaml_loader import YamlDocument

STEPS_PATH: YamlPath = ("jobs", "steps")


@dataclass(frozen=True)
class LintOptions:
    """Settings of the rules that look at the machine instead of the text.

    ``base_dir`` is where relative script paths are resolved, as the working directory is when
    the workflow runs; it defaults to the current directory. ``check_files`` turns the
    missing-file rule off, for a workflow that is checked away from its scripts.
    """

    base_dir: Path | None = None
    check_files: bool = True


@dataclass(frozen=True)
class _Step:
    """One mapping of ``jobs.steps`` together with its YAML path."""

    data: Mapping[object, object]
    path: YamlPath

    def text(self, key: str) -> str | None:
        """Return the value of ``key`` when it is a non-empty string."""
        value = self.data.get(key)
        return value if isinstance(value, str) and value else None

    def at(self, *parts: str | int) -> YamlPath:
        """Return the YAML path of something inside this step."""
        return self.path + parts


@dataclass
class _Seen:
    """What earlier steps declared, for the rules that span steps."""

    names: dict[str, YamlPath] = field(default_factory=dict)
    programs: set[str] = field(default_factory=set)
    files: set[Path] = field(default_factory=set)
    folders: list[Path] = field(default_factory=list)
    reported_runners: set[str] = field(default_factory=set)


class _Linter:  # pylint: disable=too-few-public-methods  # one entry point over shared state
    """Runs every rule over one document and collects the diagnostics."""

    def __init__(self, document: YamlDocument, options: LintOptions) -> None:
        self._document = document
        self._base_dir = (options.base_dir or Path.cwd()).resolve()
        self._check_files = options.check_files
        self._seen = _Seen()
        self._found: list[Diagnostic] = []
        self._rules: Mapping[str, Callable[[_Step], None]] = {
            "run": self._lint_run,
            "run_folder": self._lint_run_folder,
            "parallel_run": self._lint_parallel_run,
            "open_program": self._lint_open_program,
            "close_program": self._lint_close_program,
            "download_file": self._note_download,
            "unzip_zipfile": self._note_unzip,
        }

    def run(self) -> list[Diagnostic]:
        """Return the diagnostics of the whole document."""
        data = self._document.data
        if not isinstance(data, dict):
            return []
        self._unknown_keys(data, TOP_LEVEL_KEYS, ())
        jobs = data.get("jobs")
        if not isinstance(jobs, dict):
            return self._found
        self._unknown_keys(jobs, JOBS_KEYS, ("jobs",))
        steps = jobs.get("steps")
        for index, step in enumerate(steps if isinstance(steps, list) else ()):
            if isinstance(step, dict):
                self._lint_step(_Step(step, STEPS_PATH + (index,)))
        return self._found

    def _error(self, code: str, message: str, path: YamlPath, on_key: bool = False) -> None:
        line, column = self._document.position(path, on_key)
        self._found.append(Diagnostic(Severity.ERROR, code, message, path, line, column))

    def _warning(self, code: str, message: str, path: YamlPath, on_key: bool = False) -> None:
        line, column = self._document.position(path, on_key)
        self._found.append(Diagnostic(Severity.WARNING, code, message, path, line, column))

    def _unknown_keys(self, mapping: Mapping[object, object], known: Iterable[str], path: YamlPath) -> None:
        names = list(known)
        for key in mapping:
            name = str(key)
            if name not in names:
                self._warning("unknown-key", f"unknown key '{name}' is ignored.{suggestion(name, names)}",
                              path + (name,), on_key=True)

    def _lint_step(self, step: _Step) -> None:
        self._unknown_keys(step.data, STEP_KEYS, step.path)
        self._check_name(step)
        action = self._action_of(step)
        if action is None:
            return
        self._check_fields(step, action)
        rule = self._rules.get(action.key)
        if rule is not None:
            rule(step)

    def _check_name(self, step: _Step) -> None:
        name = step.text("name")
        if name is None:
            return
        first = self._seen.names.setdefault(name, step.path)
        if first != step.path:
            self._error("duplicate-step-name",
                        f"step name '{name}' is already used by {format_path(first)}", step.at("name"))

    def _action_of(self, step: _Step) -> ActionSpec | None:
        present = [key for key in ACTION_KEYS if key in step.data]
        if not present:
            self._error("missing-action",
                        f"step has no action key; expected one of: {', '.join(ACTION_KEYS)}", step.path)
            return None
        if len(present) > 1:
            self._error("conflicting-actions",
                        f"step has several action keys ({', '.join(present)}); only '{present[0]}' would run",
                        step.at(present[1]), on_key=True)
        return ACTION_BY_KEY[present[0]]

    def _check_fields(self, step: _Step, action: ActionSpec) -> None:
        for name in action.required:
            if name not in step.data:
                self._error("missing-required-field", f"a '{action.key}' step needs '{name}'",
                            step.at(action.key), on_key=True)
        for name in STEP_FIELDS:
            if name in step.data and name not in action.fields:
                self._warning("unused-field", f"'{name}' has no effect on a '{action.key}' step",
                              step.at(name), on_key=True)

    def _lint_run(self, step: _Step) -> None:
        self._check_runner(step.data.get("with"), step.at("with"))
        self._check_path(step.text("run"), step.at("run"), folder=False)
        self._check_patterns(step.data.get("artifacts"), step.at("artifacts"))

    def _lint_run_folder(self, step: _Step) -> None:
        self._check_runner(step.data.get("with"), step.at("with"))
        self._check_path(step.text("run_folder"), step.at("run_folder"), folder=True)
        self._check_patterns(step.data.get("artifacts"), step.at("artifacts"))

    def _check_patterns(self, patterns: object, path: YamlPath) -> None:
        """Warn about an artifact pattern that would be refused when the workflow runs."""
        for index, pattern in enumerate(patterns if isinstance(patterns, list) else ()):
            refusal = pattern_refusal(pattern) if isinstance(pattern, str) and pattern else None
            if refusal is not None:
                self._warning("artifact-pattern", f"artifact pattern '{pattern}' is not used: {refusal}",
                              path + (index,))

    def _lint_parallel_run(self, step: _Step) -> None:
        block = step.data.get("parallel_run")
        if not isinstance(block, dict):
            return
        self._unknown_keys(block, PARALLEL_RUN_KEYS, step.at("parallel_run"))
        runners, scripts = block.get("runners"), block.get("scripts")
        if not isinstance(runners, list) or not isinstance(scripts, list):
            return
        if len(runners) != len(scripts):
            self._error("runners-scripts-mismatch",
                        f"'runners' has {len(runners)} entries and 'scripts' has {len(scripts)}; "
                        "they are paired one to one", step.at("parallel_run"), on_key=True)
        self._lint_parallel_artifacts(step, block.get("artifacts"), len(scripts))
        for index, runner in enumerate(runners):
            self._check_runner(runner, step.at("parallel_run", "runners", index))
        for index, script in enumerate(scripts):
            if isinstance(script, str) and script:
                self._check_path(script, step.at("parallel_run", "scripts", index), folder=False)

    def _lint_parallel_artifacts(self, step: _Step, artifacts: object, scripts: int) -> None:
        if not isinstance(artifacts, list):
            return
        if len(artifacts) != scripts:
            self._error("artifacts-scripts-mismatch",
                        f"'artifacts' has {len(artifacts)} entries and 'scripts' has {scripts}; "
                        "each script has its own list of patterns", step.at("parallel_run", "artifacts"), on_key=True)
        for index, patterns in enumerate(artifacts):
            self._check_patterns(patterns, step.at("parallel_run", "artifacts", index))

    def _lint_open_program(self, step: _Step) -> None:
        name = step.text("name")
        if name is not None:
            self._seen.programs.add(name)

    def _lint_close_program(self, step: _Step) -> None:
        target = step.text("close_program")
        if target is None:
            return
        if target in self._seen.programs:
            self._seen.programs.discard(target)
        else:
            self._warning("unknown-program", f"no open_program step named '{target}' is open at this point",
                          step.at("close_program"))

    def _note_download(self, step: _Step) -> None:
        target = self._resolve(step.text("file_path"))
        if target is not None:
            self._seen.files.add(target)

    def _note_unzip(self, step: _Step) -> None:
        # Without extract_path the archive is unpacked into the working directory.
        target = self._resolve(step.text("extract_path") or ".")
        if target is not None:
            self._seen.folders.append(target)

    def _check_runner(self, runner: object, path: YamlPath) -> None:
        package = RUNNER_PACKAGES.get(runner) if isinstance(runner, str) else None
        if not isinstance(runner, str) or package is None or runner in self._seen.reported_runners:
            return
        if is_installed(package):
            return
        self._seen.reported_runners.add(runner)
        hint = " Install it with: pip install test_pioneer[gui]" if runner in OPTIONAL_RUNNERS else ""
        self._warning("runner-not-installed",
                      f"'{runner}' needs the '{package}' package, which is not installed here.{hint}", path)

    def _resolve(self, value: str | None) -> Path | None:
        """Resolve a workflow path the way the executor does: against the working directory."""
        if value is None:
            return None
        try:
            return (self._base_dir / value).resolve()
        except (OSError, ValueError):
            return None

    def _produced_earlier(self, target: Path) -> bool:
        """True when an earlier download or unzip step may create ``target``."""
        if target in self._seen.files:
            return True
        return any(folder == target or folder in target.parents for folder in self._seen.folders)

    def _check_path(self, value: str | None, path: YamlPath, folder: bool) -> None:
        target = self._resolve(value) if self._check_files else None
        if target is None or self._produced_earlier(target):
            return
        where = f"{value} (looked in {self._base_dir})"
        try:
            if not folder and not target.is_file():
                self._warning("missing-file", f"file not found: {where}", path)
            elif folder and not target.is_dir():
                self._warning("missing-file", f"folder not found: {where}", path)
            elif folder and not any(target.glob("*.json")):
                self._warning("missing-file", f"folder has no .json file: {where}", path)
        except OSError as error:
            # An unreadable location cannot be judged here; the run itself will report it.
            test_pioneer_logger.debug("Could not check %s: %s", target, error)


def run_lint_rules(document: YamlDocument, options: LintOptions | None = None) -> list[Diagnostic]:
    """Return the semantic problems of a parsed workflow.

    Parts that do not have the expected shape are skipped: the schema check reports those.
    """
    return _Linter(document, options or LintOptions()).run()
