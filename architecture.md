# TestPioneer Architecture

> Short overview for people and agents.
> Last verified: 2026-10-08 against `9951492` merged with `dev` (`a3afdcc`), on
> `feature/testpioneer-platform-improvements`.

## 1. Purpose

TestPioneer (`test_pioneer`) is a YAML-driven orchestrator for CI/CD test runs. It is published as
`test_pioneer` (stable, `pyproject.toml`) and `test_pioneer_dev` (dev, `dev.toml`). A YAML file
lists named `jobs.steps`, and each step does one of two things:

- run JSON action files through a sibling runner: WebRunner, APITestka, LoadDensity, or AutoControl
  for GUI tests;
- perform a utility action: download or unzip a file, open a URL, start or stop a program, wait, or
  run scripts in parallel.

File logging and screen recording are optional. A workflow can also be checked without executing
it: against a versioned JSON Schema and a set of lint rules, with diagnostics located by line and
column. Every execution is a run with an ID; it returns a normalized result and keeps the
artifacts of the runner executions that did not pass. The runners' own reports are read into
that result, and one consolidated report (JSON, HTML, optional JUnit XML) is written per run.

## 2. Layers and directories

| Path | Responsibility |
| --- | --- |
| `test_pioneer/__init__.py` | Facade: `execute_yaml`, `RunOptions`, `create_template_dir`, `validate_yaml`, `lint_yaml`, `load_yaml`, `get_yaml_schema` |
| `test_pioneer/__main__.py`, `test_pioneer/cli.py` | CLI: `cli.main(argv)` returns the exit code of `python -m test_pioneer` (`-e/--execute_yaml <file>`, `run`, `validate`, `schema`) |
| `test_pioneer/schema/` | The workflow contract. `spec.py`: top-level keys, step types (`ACTIONS`, in dispatch order) and their fields. `definition.py`: builds the JSON Schema from `spec.py` and holds `SCHEMA_VERSION`. `get_yaml_schema()` returns it |
| `schema/testpioneer.schema.json` | The same schema, published for editors and other tools. Written with `python -m test_pioneer schema > schema/testpioneer.schema.json`; `test/test_schema.py` keeps it identical to the built one |
| `test_pioneer/validation/` | `yaml_loader.load_yaml` (safe parse that keeps the line and column of every key and value), `schema_validator.check_schema` (built-in validator for the keywords the schema uses), `linter.run_lint_rules` (semantic rules), `api.validate_yaml` / `lint_yaml` |
| `test_pioneer/models/` | `diagnostic.py`: `Diagnostic`, `ValidationResult`, `Severity`. `result.py`: the normalized run result (`RunResult`, `StepResult`, `RunnerResult`, `Artifact`, `Status`) |
| `test_pioneer/runner/` | `adapter.py`: the `RunnerAdapter` protocol and `ModuleRunner` (a package started as `python -m <package> --execute_file <script>`, with the reader of its report format). `registry.py`: `RUNNERS`, one adapter per `with:` tag, read by the schema, the linter, `parallel_run` and the run session; `find_runner` |
| `test_pioneer/artifacts/` | `context.py`: the two environment variable names, the keep policies, run ID creation and checking. `store.py`: `ArtifactStore`, the directory tree of one run (runner directories, execution log, manifest, removal). `capture.py`: copies in-process output and sub-process logs without threads. `collect.py`: copies the files a step declares with `artifacts:` into its runner directory. `session.py`: `RunSession`, `RunOptions`, `current_session`, `in_process_runner` |
| `test_pioneer/report/` | `readers.py`: `ReportReader` and `RecordPairReader`, which turn a runner's `*_success.json` / `*_failure.json` pair into `CaseResult`s. `formats.py`: format names, default location and file names. `html_report.py`, `junit_report.py`: renderers. `service.py`: `write_reports` |
| `test_pioneer/executor/pioneer_executor.py` | `execute_yaml`: loads YAML (`yaml.safe_load`), opens a `RunSession`, dispatches each step through `_STEP_HANDLERS` and returns the `RunResult` |
| `test_pioneer/executor/run/` | `executor_run.run` (one JSON file), `executor_run_folder.run_folder` (every `*.json` in a folder), `parallel_run.parallel_run` (subprocesses), `runner_process.py` (one runner sub-process: its environment, log files and exit code), `utils.select_with_runner` (maps `with:` tags to runners), `process_manager.py` (tracks parallel subprocesses) |
| `test_pioneer/executor/file/file_processing.py` | `download_file` and `unzip_zipfile` steps, delegated to `automation_file` |
| `test_pioneer/executor/browser/url.py` | `open_url` step (`webbrowser`) |
| `test_pioneer/executor/program/external_program.py` | `open_program` / `close_program` steps, with optional stdout/stderr redirect |
| `test_pioneer/executor/time/wait.py` | `wait` step (`blocked_wait`) |
| `test_pioneer/executor/test_recorder/` | `logger.set_logger` (`pioneer_log` file handler); `video_recoder.set_recorder` (screen recording through `je_auto_control.RecordingThread`) |
| `test_pioneer/process/` | `ExecuteProcess` (psutil-backed) and `process_manager_instance` (named programs and the set of used step names) |
| `test_pioneer/project/` | `create_template_dir` scaffolding (default parent `.TestPioneer`), templates in `template/template.py` |
| `test_pioneer/logging/loggin_instance.py` | `test_pioneer_logger`, `TestPioneerHandler`, `step_log_check`, and `set_step_log_sink`, through which the run session receives every step message whether or not `pioneer_log` is set |
| `test_pioneer/utils/` | `exception/` (exceptions and tags), `package/check.py` (`is_installed`) |
| `test/` | pytest suite. `test/unit_test/` holds example YAML scenarios and manual scripts, excluded by `addopts = "--ignore=test/unit_test"` |
| `scripts/dev_release.py` | Release helper for the dev channel (stdlib only): picks the next `test_pioneer_dev` version from PyPI and tells whether the built wheel differs from the newest published one |
| `Dockerfile_GUI`, `Dockerfile_NonGUI`, `docker_gui_test/`, `docker_non_gui_test/`, `docker_*_requirements.txt` | Container images: the default build is the base image, `--target selftest` adds the bundled sample YAML/JSON and runs it |
| `docs/` | Sphinx docs (`getting-started.rst`, `api-reference.rst`, `docker.rst`, `changelog.rst`) |

## 3. Entry points and public interfaces

- **Python**: `from test_pioneer import execute_yaml, create_template_dir`. Call
  `execute_yaml(stream, yaml_type="File", options=None)` with a path, or with `yaml_type="String"`
  and inline YAML. It returns a `RunResult`; `RunOptions(run_id, artifacts_path, keep_artifacts,
  report_path, report_formats)` overrides the workflow's own settings.
  `validate_yaml` (syntax and schema) and `lint_yaml` (the same plus the lint rules) take the same
  two arguments and return a `ValidationResult`; `load_yaml` returns the parsed `YamlDocument` and
  `get_yaml_schema` the schema as a dict.
- **CLI**:
  - `python -m test_pioneer -e <file.yml>` (`--execute_yaml`) executes a workflow and exits 0
    unless an exception is raised, whatever the steps did;
  - `python -m test_pioneer run [--run_id ID] [--artifacts_path DIR]
    [--keep_artifacts {on_failure,always,never}] [--report_path DIR] [--report_formats FORMATS]
    <file.yml>` executes one and exits 0 when the run passed, 1 when it did not;
  - `python -m test_pioneer validate [--format {text,json}] [--strict] [--base_dir DIR]
    [--no_file_check] <file.yml>...` checks workflows without executing them and exits 1 on an
    error (or on a warning with `--strict`);
  - `python -m test_pioneer schema` prints the JSON Schema;
  - with neither `-e` nor a command, the CLI raises `ExecutorException`;
  - no `-d`, `-c` or `--execute_str`, and no console script is declared.
- **YAML contract**:
  - optional top-level keys `pioneer_log` (log file path), `recording_path` (needs `je_auto_control`),
    `artifacts_path` (default `artifacts`), `keep_artifacts` (`on_failure`, `always`, `never`),
    `report_path` (default `report`) and `report_formats` (list of `json`, `html`, `junit`);
  - required `jobs.steps`, a list where each step has a unique `name` and one of `run`, `run_folder`,
    `open_url`, `download_file` (+ `file_path`), `wait`, `open_program`, `close_program`,
    `unzip_zipfile` or `parallel_run` (`runners`, `scripts`, optional `executor_path`);
  - `run` and `run_folder` need `with:` set to `web-runner`, `api-runner`, `load-runner`, `file-runner` or `gui-runner`;
  - `run` and `run_folder` take an optional `artifacts` list of file patterns, and `parallel_run`
    one such list per script;
  - the same contract is published as a JSON Schema, `schema/testpioneer.schema.json`.
- **PyPI packages**: `test_pioneer` (stable) and `test_pioneer_dev` (dev channel), both published by CI.
  - Stable: a push to `main` runs `publish.yml`, which bumps `pyproject.toml`, tags and uploads.
  - Dev: the `publish-dev` job of `ci.yml` runs after `unit-test` and `integration-test` on a push
    to `dev` (never on `main`, a pull request or the schedule). It builds from `dev.toml` and uploads
    when the commit is still the tip of `dev` and the wheel differs from the newest published one.
    `scripts/dev_release.py` takes the version from PyPI (newest release plus one patch), so nothing
    is committed back and the version in `dev.toml` is only a floor.
  - Both jobs install only the hash-locked `.github/requirements/publish.txt` and build with
    `python -m build --no-isolation`, so the build backend is the locked `setuptools` too.
  - Contents, the same for both: the wheel holds only the `test_pioneer/` package; the sdist adds
    `LICENSE`, `README.md`, `pyproject.toml`, `MANIFEST.in` and the generated metadata. It carries no
    tests, because `MANIFEST.in` prunes `test/` (`test/test_sdist_manifest.py` pins it).
- There is no MCP server, LSP, socket server, pytest plugin or GUI of its own.

## 4. Main flows

**YAML → steps**

```
python -m test_pioneer -e file.yml → execute_yaml → _load_yaml (yaml.safe_load, must be a dict)
  → set_logger (pioneer_log) → RunSession (run ID, keep policy, artifact directory)
  → _setup_recorder (recording_path, only if je_auto_control is installed)
  → with session: _extract_steps (jobs.steps) → _validate_steps (name present and unique)
    → _run_steps → session.run_step → _dispatch_step (first matching key in _STEP_HANDLERS)
    → handler(step) -> bool → a False result stops the remaining steps (recorded as cancelled)
  → session ends: statuses combined, keep policy applied, manifest written
  → recorder stopped in finally → RunResult returned
```

**Run session**

```
RunSession.__enter__ → ArtifactStore.create (<artifacts_path>/<run-id>/testpioneer/execution.log)
  → current_session() set + step log sink set (every step_log_check message → execution.log)
run_step → StepResult (timing; True → passed, False → failed, exception → error and re-raised)
  → the step takes the worst status of itself and the runner executions recorded during it
begin/end (or reject) → RunnerResult + runners/<runner>/<nn>-<step>/ + the two variables
end → collect_files (the step's artifacts: patterns, files changed since the runner started,
  copied to collected/) → find_runner(runner).report.read(directory) → RunnerResult.cases
  → a runner that ended normally but recorded a failed test becomes failed
__exit__ → run status = worst step status → on_failure: a passed run is removed entirely, a
  failed one keeps testpioneer/ and the runners that did not pass
  → write_reports (<report_path>/testpioneer-report.{json,html}, testpioneer-junit.xml)
  → manifest.json
```

An artifact or report problem (`OSError`, or `ValueError` for a malformed runner report) becomes
an entry of `RunResult.warnings`; it never changes the outcome. A handler called outside
`execute_yaml` finds no session and behaves as before.

**Validation (nothing is executed)**

```
python -m test_pioneer validate file.yml → lint_yaml → load_yaml (yaml.SafeLoader; position index;
  syntax errors and duplicate keys become diagnostics)
  → check_schema (get_yaml_schema: type, required, enum, minItems, minLength, minimum)
  → run_lint_rules (duplicate names, missing/conflicting actions, required fields,
    runners/scripts length, unknown keys, runner packages, referenced files)
  → ValidationResult, sorted by line and column → text or JSON → exit 0 / 1
```

`execute_yaml` does not call the validator: a workflow runs exactly as it did before, whether or
not it would pass `validate`.

**`run` step (in-process)**

```
select_with_runner → _build_runner_dict (sets LOCUST_SKIP_MONKEY_PATCH=1, then imports
  je_web_runner / je_api_testka / je_load_density execute_action, + je_auto_control if installed)
  → JSON file resolved against cwd → json.loads
  → in_process_runner: TEST_PIONEER_RUN_ID / TEST_PIONEER_ARTIFACT_DIR set for the call,
    sys.stdout / sys.stderr copied to stdout.log / stderr.log → runner(file_content)
```

**`parallel_run` step (subprocess)**

```
_BASE_RUNNER_COMMANDS (+ gui-runner → je_auto_control) → for each (runner, script):
  RUNNERS[runner].command(python, script) = [python, "-m", <package>, "--execute_file", <script>]
  → start_runner_process: Popen with the two variables added to the environment and
    stdout / stderr written to the runner directory → process_manager
  → wait loop (0.1 s): copy new log bytes to the console, record each exit code
    (0 → passed, otherwise failed); an interrupted wait terminates what is still running
```

A runner that fails does not stop the steps after the `parallel_run` step, as before; it makes
the step and the run `failed`.

## 5. Extension points

- **New step type**, in this order:
  1. Add a handler under `test_pioneer/executor/<area>/` with the signature
     `(step: dict, enable_logging: bool = False) -> bool`. Report problems with `step_log_check` and
     return `False`.
  2. Add its YAML key to `_STEP_HANDLERS` in `executor/pioneer_executor.py`. Order matters: the
     first key present in the step wins.
  3. Describe it in `ACTIONS` (`schema/spec.py`) at the same position, with its value schema and
     its required and optional fields; add new fields to `STEP_FIELDS`. `test/test_schema.py`
     fails while the two tables differ.
  4. Bump `SCHEMA_VERSION` (`schema/definition.py`) and regenerate the published schema:
     `python -m test_pioneer schema > schema/testpioneer.schema.json`.
  5. Add `test/test_<area>.py`.
  6. Document it in `docs/step-types.rst`.
- **New runner (`with:` tag)**:
  1. Add a `ModuleRunner(tag, package)` to `RUNNERS` (`runner/registry.py`); `parallel_run`, the
     schema's runner enum and the linter read it. Pass `optional=True` when the package comes
     from an extra, and `report=` with the reader of its report format. A runner with another
     command line implements `RunnerAdapter` itself.
  2. Import it lazily in `_build_runner_dict` (`executor/run/utils.py`).
  3. Declare the dependency in `pyproject.toml` and `dev.toml` (in `dependencies`, or in an extra
     like `gui`).
  4. Bump `SCHEMA_VERSION` and regenerate the published schema, as for a step type.
  5. Extend `test/test_run_utils.py` and `test/test_parallel_run.py`.
- **New runner report format**: implement `ReportReader.read(directory)` in `report/readers.py`
  (return `None` when there is no report, raise `ValueError` for a malformed one) and give it to
  the runner's adapter. For a runner of the same family, a `RecordPairReader` with that runner's
  field names is enough. Test it in `test/test_report_readers.py` with a record in the runner's
  real shape.
- **New report format**: add its name and file to `report/formats.py`, a renderer beside
  `html_report.py`, and a branch in `report/service.py`; the schema's `report_formats` enum and
  the `--report_formats` option read `REPORT_FORMATS`.
- **New lint rule**: add a method to `_Linter` (`validation/linter.py`), register it in `_rules`
  when it belongs to one step type, list its code in `docs/validation.rst`, and test it in
  `test/test_linter.py`. Errors are for what the executor stops on or can never run; anything that
  depends on the machine is a warning.
- **New schema keyword**: the built-in validator implements only `CONSTRAINT_KEYWORDS`
  (`validation/schema_validator.py`). Implement the keyword there before the schema uses it;
  `test/test_schema.py` fails otherwise.
- **Project template**: edit `project/template/template.py` and `project/create_template_structure.py`.

## 6. Cross-project boundaries

- **Declared dependencies** (`pyproject.toml`): `je_web_runner`, `je_load_density`, `je_api_testka`,
  `je-mail-thunder`, `automation-file`, `psutil`, `pyyaml`. The optional extra `gui` adds
  `je_auto_control`.
- **In-process imports**:
  - `execute_action` (for `run`) and `execute_files` (for `run_folder`) from `je_web_runner`,
    `je_api_testka`, `je_load_density` and `automation_file` in `executor/run/utils.py`;
  - `je_auto_control.execute_action` / `execute_files` for `gui-runner`, imported only for a GUI step;
  - `automation_file.download_file` / `unzip_all` in `executor/file/file_processing.py`;
  - `je_auto_control.RecordingThread` in `executor/test_recorder/video_recoder.py`.
- **Subprocess contract**: `parallel_run.py` spawns `python -m je_web_runner|je_api_testka|je_load_density|automation_file|je_auto_control --execute_file <script>`.
  It depends on those packages keeping the legacy `--execute_file` flag.
- **`run_folder`** passes the folder's `.json` files, as sorted string paths, to the runner's `execute_files`.
- **`je-mail-thunder`** is declared but not imported anywhere in `test_pioneer/`.
- **PyBreeze** depends on these names:
  - it launches `python -m test_pioneer -e <yaml>`
    (`PyBreeze/pybreeze/extend/process_executor/test_pioneer/test_pioneer_process_manager.py`);
  - it imports `create_template_dir`
    (`pybreeze/pybreeze_ui/menu/automation_menu/test_pioneer_menu/build_test_pioneer_menu.py`).
- **Runner artifact contract**, offered to the runner packages: every runner execution gets
  `TEST_PIONEER_RUN_ID` and `TEST_PIONEER_ARTIFACT_DIR` (an existing directory, absolute path) in
  its environment. None of the five packages reads them yet (checked 2026-10-08 against
  je_api_testka 0.0.145, je_web_runner 0.0.93, je_load_density 0.0.77, automation_file 0.0.51,
  je_auto_control 0.0.225); until one does, its directory holds only the captured output.
- **Runner exit codes**: `python -m <package> --execute_file` exits 0 in all five packages when
  an action of the script fails, and 1 only for a script that is missing or malformed
  (je_auto_control also for an unknown command or a failed `AC_assert_*`). A `failed` status
  from an exit code therefore means only that.
- **Runner report format**, relied on here and owned by the runner packages: the pair
  `<name>_success.json` / `<name>_failure.json`, each an object of `Success_TestN` /
  `Failure_TestN` records, written by `AT_generate_json_report`, `WR_generate_json_report`,
  `LD_generate_json_report` and `AC_generate_json_report`. The readers use these record fields:
  API `request_method`, `http_method`, `request_url`, `test_url`, `error`; web and GUI
  `function_name`, `exception`; load `Method`, `name`, `error`. A renamed field degrades a test
  name to its record key; a changed layout makes the report unreadable, which is a warning.
  The path a script gives is relative to the working directory and its folder must exist.
- **Run result contract**, offered to CI and UIs:
  - `<artifacts_path>/<run-id>/testpioneer/manifest.json` and the return value of
    `execute_yaml`: `RunResult.to_dict()` with `format_version` (`RESULT_FORMAT_VERSION`),
    documented in `docs/artifacts.rst`;
  - the directory layout `runners/<runner>/<nn>-<step>/` with `stdout.log` and `stderr.log`;
  - `python -m test_pioneer run`: exit status 0 (passed) or 1, and its summary lines;
  - `<report_path>/testpioneer-report.json` (the same `RunResult.to_dict()`),
    `testpioneer-report.html` and `testpioneer-junit.xml`, documented in `docs/reports.rst`.
- **Validation contract**, offered to editors and UIs (PyBreeze is the intended consumer):
  - `schema/testpioneer.schema.json`, at that path and under the `$id` URL it declares. Its
    `version` follows `SCHEMA_VERSION`: a minor bump adds something, a major bump is for a
    workflow that used to validate and no longer does;
  - `python -m test_pioneer validate --format json`: an object with `schema_version`, `ok` and
    `files[]`, each file with `source`, `ok`, `errors`, `warnings` and `diagnostics[]` of
    `severity`, `code`, `message`, `path`, `pointer`, `line`, `column`, `source`. Exit status 0,
    1 (problems) or 2 (usage);
  - the diagnostic codes listed in `docs/validation.rst`;
  - `validate_yaml`, `lint_yaml`, `load_yaml`, `get_yaml_schema` in `test_pioneer`, and
    `LintOptions` in `test_pioneer.validation`.

## 7. Design constraints

- Strategy pattern for runner dispatch, Factory for step creation, a Singleton logger. Extend by
  adding runners or steps (CLAUDE.md § Coding Standards › Design Patterns & Software Engineering).
- Security:
  - validate YAML content, CLI arguments and file paths;
  - no `shell=True`, `os.system`, `eval`, `exec` or `pickle.loads`;
  - load YAML only with `yaml.safe_load`;
  - never log secrets
  (§ Security (Mandatory); § Static Analysis Compliance › Security).
- Set timeouts on I/O and subprocesses. Prefer `pathlib.Path` (§ Performance).
- Type hints on every public signature. New code is `mypy --strict` clean. Public modules and
  classes have docstrings (§ Static Analysis Compliance › Typing & Documentation).
- Limits: cognitive complexity ≤ 15, cyclomatic complexity ≤ 10, functions ≤ 50 lines, files ≤ 750
  lines, ≤ 7 parameters, nesting ≤ 4, lines ≤ 120 characters (§ Static Analysis Compliance ›
  Complexity & Size; › Naming & Style).
- No dead code, and no `TODO` or `FIXME`; file an issue instead (§ Code Hygiene).
- English, imperative commit subjects under 72 characters, one logical change per commit (§ Git
  Commit Rules).
- The dependency set is listed in § Dependencies. Keep it in sync with `pyproject.toml`.

## 8. When to update this file

- A step type, YAML key or `with:` runner tag is added, removed or renamed.
- The CLI flags or commands, the facade in `test_pioneer/__init__.py`, or the packaging
  (`pyproject.toml`, `dev.toml`, `MANIFEST.in`) changes.
- The schema version, the `validate --format json` output or a diagnostic code changes.
- The artifact layout, the two environment variables, the keep policies or the fields of the run
  result change.
- A report file name or format, or a record field that a report reader uses, changes.
- A sibling package's entry point that TestPioneer depends on changes: `execute_action`,
  `execute_files`, `--execute_file`, `download_file`, `unzip_all`, `RecordingThread`.
- The dependency list or the `gui` extra changes.
- A §6 contract with PyBreeze changes.
- A CLAUDE.md section referenced in §7 is renamed or its rule changes.
- Refresh the "Last verified" line whenever this file is re-checked against HEAD.
