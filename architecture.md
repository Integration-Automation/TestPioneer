# TestPioneer Architecture

> Short overview for people and agents.
> Last verified: 2026-09-22 against `dfe9eaa` on `dev`.

## 1. Purpose

TestPioneer (`test_pioneer`) is a YAML-driven orchestrator for CI/CD test runs. It is published as
`test_pioneer` (stable, `pyproject.toml`) and `test_pioneer_dev` (dev, `dev.toml`). A YAML file
lists named `jobs.steps`, and each step does one of two things:

- run JSON action files through a sibling runner: WebRunner, APITestka, LoadDensity, or AutoControl
  for GUI tests;
- perform a utility action: download or unzip a file, open a URL, start or stop a program, wait, or
  run scripts in parallel.

File logging and screen recording are optional.

## 2. Layers and directories

| Path | Responsibility |
| --- | --- |
| `test_pioneer/__init__.py` | Facade: `execute_yaml`, `create_template_dir` |
| `test_pioneer/__main__.py` | CLI: `python -m test_pioneer -e/--execute_yaml <file>` |
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
| `Dockerfile_GUI`, `Dockerfile_NonGUI`, `Test_GUI_DockerFile`, `Test_NonGUI_DockerFile`, `docker_gui_test/`, `docker_non_gui_test/`, `docker_*_requirements.txt` | Container images, plus sample YAML/JSON for container runs |
| `docs/` | Sphinx docs (`getting-started.rst`, `api-reference.rst`, `docker.rst`, `changelog.rst`) |

## 3. Entry points and public interfaces

- **Python**: `from test_pioneer import execute_yaml, create_template_dir`. Call
  `execute_yaml(stream, yaml_type="File")` with a path, or with `yaml_type="String"` and inline YAML.
- **CLI**:
  - `python -m test_pioneer -e <file.yml>` (`--execute_yaml`) is the only flag;
  - without it, the CLI raises `ExecutorException`;
  - no `-d`, `-c` or `--execute_str`, and no console script is declared.
- **YAML contract**:
  - optional top-level keys `pioneer_log` (log file path) and `recording_path` (needs `je_auto_control`);
  - required `jobs.steps`, a list where each step has a unique `name` and one of `run`, `run_folder`,
    `open_url`, `download_file` (+ `file_path`), `wait`, `open_program`, `close_program`,
    `unzip_zipfile` or `parallel_run` (`runners`, `scripts`, optional `executor_path`);
  - `run` and `run_folder` need `with:` set to `web-runner`, `api-runner`, `load-runner`, `file-runner` or `gui-runner`.
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
  3. Add `test/test_<area>.py`.
  4. Document it in `docs/api-reference.rst`.
- **New runner (`with:` tag)**:
  1. Import it lazily in `_build_runner_dict` (`executor/run/utils.py`).
  2. Add its package to `_BASE_RUNNER_COMMANDS` (`executor/run/parallel_run.py`).
  3. Declare the dependency in `pyproject.toml` and `dev.toml` (in `dependencies`, or in an extra
     like `gui`).
  4. Extend `test/test_run_utils.py` and `test/test_parallel_run.py`.
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
- The CLI flag, the `execute_yaml` / `create_template_dir` facade, or the packaging (`pyproject.toml`,
  `dev.toml`) changes.
- A sibling package's entry point that TestPioneer depends on changes: `execute_action`,
  `execute_files`, `--execute_file`, `download_file`, `unzip_all`, `RecordingThread`.
- The dependency list or the `gui` extra changes.
- A §6 contract with PyBreeze changes.
- A CLAUDE.md section referenced in §7 is renamed or its rule changes.
- Refresh the "Last verified" line whenever this file is re-checked against HEAD.
