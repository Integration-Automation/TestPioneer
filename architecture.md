# TestPioneer Architecture

> Short overview for people and agents.
> Last verified: 2026-10-08 against `d76ad27` plus the validation change, on
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
column.

## 2. Layers and directories

| Path | Responsibility |
| --- | --- |
| `test_pioneer/__init__.py` | Facade: `execute_yaml`, `create_template_dir`, `validate_yaml`, `lint_yaml`, `load_yaml`, `get_yaml_schema` |
| `test_pioneer/__main__.py`, `test_pioneer/cli.py` | CLI: `cli.main(argv)` returns the exit code of `python -m test_pioneer` (`-e/--execute_yaml <file>`, `validate`, `schema`) |
| `test_pioneer/schema/` | The workflow contract. `spec.py`: top-level keys, step types (`ACTIONS`, in dispatch order) and their fields. `definition.py`: builds the JSON Schema from `spec.py` and holds `SCHEMA_VERSION`. `get_yaml_schema()` returns it |
| `schema/testpioneer.schema.json` | The same schema, published for editors and other tools. Written by `python -m test_pioneer schema -o`; `test/test_schema.py` keeps it identical to the built one |
| `test_pioneer/validation/` | `yaml_loader.load_yaml` (safe parse that keeps the line and column of every key and value), `schema_validator.check_schema` (built-in validator for the keywords the schema uses), `linter.run_lint_rules` (semantic rules), `api.validate_yaml` / `lint_yaml` |
| `test_pioneer/models/` | `diagnostic.py`: `Diagnostic`, `ValidationResult`, `Severity`. `result.py`: the normalized run result (`RunResult`, `StepResult`, `RunnerResult`, `Artifact`, `Status`) |
| `test_pioneer/runner/registry.py` | `RUNNER_PACKAGES`: each `with:` tag and the package behind it. Read by the schema, the linter and `parallel_run` |
| `test_pioneer/executor/pioneer_executor.py` | `execute_yaml`: loads YAML (`yaml.safe_load`), validates it, and dispatches each step through `_STEP_HANDLERS` |
| `test_pioneer/executor/run/` | `executor_run.run` (one JSON file), `executor_run_folder.run_folder` (every `*.json` in a folder), `parallel_run.parallel_run` (subprocesses), `utils.select_with_runner` (maps `with:` tags to runners), `process_manager.py` (tracks parallel subprocesses) |
| `test_pioneer/executor/file/file_processing.py` | `download_file` and `unzip_zipfile` steps, delegated to `automation_file` |
| `test_pioneer/executor/browser/url.py` | `open_url` step (`webbrowser`) |
| `test_pioneer/executor/program/external_program.py` | `open_program` / `close_program` steps, with optional stdout/stderr redirect |
| `test_pioneer/executor/time/wait.py` | `wait` step (`blocked_wait`) |
| `test_pioneer/executor/test_recorder/` | `logger.set_logger` (`pioneer_log` file handler); `video_recoder.set_recorder` (screen recording through `je_auto_control.RecordingThread`) |
| `test_pioneer/process/` | `ExecuteProcess` (psutil-backed) and `process_manager_instance` (named programs and the set of used step names) |
| `test_pioneer/project/` | `create_template_dir` scaffolding (default parent `.TestPioneer`), templates in `template/template.py` |
| `test_pioneer/logging/loggin_instance.py` | `test_pioneer_logger`, `TestPioneerHandler`, `step_log_check` |
| `test_pioneer/utils/` | `exception/` (exceptions and tags), `package/check.py` (`is_installed`) |
| `test/` | pytest suite. `test/unit_test/` holds example YAML scenarios and manual scripts, excluded by `addopts = "--ignore=test/unit_test"` |
| `Dockerfile_GUI`, `Dockerfile_NonGUI`, `docker_gui_test/`, `docker_non_gui_test/`, `docker_*_requirements.txt` | Container images: the default build is the base image, `--target selftest` adds the bundled sample YAML/JSON and runs it |
| `docs/` | Sphinx docs (`getting-started.rst`, `api-reference.rst`, `docker.rst`, `changelog.rst`) |

## 3. Entry points and public interfaces

- **Python**: `from test_pioneer import execute_yaml, create_template_dir`. Call
  `execute_yaml(stream, yaml_type="File")` with a path, or with `yaml_type="String"` and inline YAML.
  `validate_yaml` (syntax and schema) and `lint_yaml` (the same plus the lint rules) take the same
  two arguments and return a `ValidationResult`; `load_yaml` returns the parsed `YamlDocument` and
  `get_yaml_schema` the schema as a dict.
- **CLI**:
  - `python -m test_pioneer -e <file.yml>` (`--execute_yaml`) executes a workflow;
  - `python -m test_pioneer validate [--format {text,json}] [--strict] [--base_dir DIR]
    [--no_file_check] <file.yml>...` checks workflows without executing them and exits 1 on an
    error (or on a warning with `--strict`);
  - `python -m test_pioneer schema [-o FILE]` prints or writes the JSON Schema;
  - with neither `-e` nor a command, the CLI raises `ExecutorException`;
  - no `-d`, `-c` or `--execute_str`, and no console script is declared.
- **YAML contract**:
  - optional top-level keys `pioneer_log` (log file path) and `recording_path` (needs `je_auto_control`);
  - required `jobs.steps`, a list where each step has a unique `name` and one of `run`, `run_folder`,
    `open_url`, `download_file` (+ `file_path`), `wait`, `open_program`, `close_program`,
    `unzip_zipfile` or `parallel_run` (`runners`, `scripts`, optional `executor_path`);
  - `run` and `run_folder` need `with:` set to `web-runner`, `api-runner`, `load-runner`, `file-runner` or `gui-runner`;
  - the same contract is published as a JSON Schema, `schema/testpioneer.schema.json`.
- There is no MCP server, LSP, socket server, pytest plugin or GUI of its own.

## 4. Main flows

**YAML → steps**

```
python -m test_pioneer -e file.yml → execute_yaml → _load_yaml (yaml.safe_load, must be a dict)
  → set_logger (pioneer_log) + _setup_recorder (recording_path, only if je_auto_control is installed)
  → _extract_steps (jobs.steps) → _validate_steps (name present and unique)
  → _run_steps → _dispatch_step (first matching key in _STEP_HANDLERS) → handler(step) -> bool
  → a False result stops the remaining steps → recorder stopped in finally
```

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
  → JSON file resolved against cwd → json.loads → runner(file_content)
```

**`parallel_run` step (subprocess)**

```
_BASE_RUNNER_COMMANDS (+ gui-runner → je_auto_control) → for each (runner, script):
  subprocess.Popen([python, "-m", <package>, "--execute_file", <script>]) → process_manager → wait for all
```

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
     `python -m test_pioneer schema -o schema/testpioneer.schema.json`.
  5. Add `test/test_<area>.py`.
  6. Document it in `docs/step-types.rst`.
- **New runner (`with:` tag)**:
  1. Add the tag and its package to `RUNNER_PACKAGES` (`runner/registry.py`); `parallel_run`, the
     schema's runner enum and the linter read it. Add it to `OPTIONAL_RUNNERS` when the package
     comes from an extra.
  2. Import it lazily in `_build_runner_dict` (`executor/run/utils.py`).
  3. Declare the dependency in `pyproject.toml` and `dev.toml` (in `dependencies`, or in an extra
     like `gui`).
  4. Bump `SCHEMA_VERSION` and regenerate the published schema, as for a step type.
  5. Extend `test/test_run_utils.py` and `test/test_parallel_run.py`.
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
  (`pyproject.toml`, `dev.toml`) changes.
- The schema version, the `validate --format json` output or a diagnostic code changes.
- A sibling package's entry point that TestPioneer depends on changes: `execute_action`,
  `execute_files`, `--execute_file`, `download_file`, `unzip_all`, `RecordingThread`.
- The dependency list or the `gui` extra changes.
- A §6 contract with PyBreeze changes.
- A CLAUDE.md section referenced in §7 is renamed or its rule changes.
- Refresh the "Last verified" line whenever this file is re-checked against HEAD.
