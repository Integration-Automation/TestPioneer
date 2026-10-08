# TestPioneer

[![Documentation Status](https://readthedocs.org/projects/testpioneer/badge/?version=latest)](https://testpioneer.readthedocs.io/en/latest/?badge=latest)
[![CI](https://github.com/Integration-Automation/TestPioneer/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/TestPioneer/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/test_pioneer)](https://pypi.org/project/test_pioneer/)
[![Python](https://img.shields.io/pypi/pyversions/test_pioneer)](https://pypi.org/project/test_pioneer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Language: English | [繁體中文](README/README_zh-TW.md) | [简体中文](README/README_zh-CN.md)**

A YAML-driven automation test framework for CI/CD pipelines, supporting GUI, Web, API, and Load testing through pluggable runners.

## Features

- **Multi-type testing** - GUI, Web, API, and Load/Stress testing via pluggable runners
- **YAML configuration** - Human-readable test workflows, easy to maintain and version control
- **Workflow validation** - Check a workflow against a versioned JSON Schema and lint rules before anything runs
- **Parallel execution** - Run multiple test scripts concurrently with different runners
- **Run artifacts** - Every run has an ID; the output, exit code and files of each runner that fails are kept
- **One report** - The results of every runner are merged into a single JSON and HTML report, with optional JUnit XML
- **Video recording** - Built-in test session recording for debugging
- **Process management** - Launch/terminate external programs with stdout/stderr redirection
- **Cross-platform** - Windows, macOS, and Linux (Python 3.10+)

## Installation

```bash
pip install test_pioneer
```

With GUI automation support:

```bash
pip install test_pioneer[gui]
```

## Quick Start

One complete example: a workflow that starts a small web site, tests it with the API runner, then runs an API script and a load test in parallel. It needs only `pip install test_pioneer`; no browser and no external service.

### 1. Project Layout

```text
my_project/
├── tests/
│   ├── test.yaml          # the workflow
│   ├── api_smoke.json     # API runner script
│   ├── api_pages.json     # API runner script
│   └── load_home.json     # load runner script
├── site/
│   └── index.html         # the page the example serves and tests
└── reports/               # the runners write their reports here
```

Create the folders and the page. The runners do not create `reports/` themselves.

```bash
mkdir tests
mkdir site
mkdir reports
echo "<html><body>hello</body></html>" > site/index.html
```

### 2. Runner Scripts

A runner script is a JSON list of actions. Each one ends by writing its runner's report.

`tests/api_smoke.json`

```json
[
  ["AT_test_api_method", {"http_method": "get", "test_url": "http://127.0.0.1:8765/site/index.html",
                          "result_check_dict": {"status_code": 200}}],
  ["AT_generate_json_report", {"json_file_name": "reports/api_smoke"}]
]
```

`tests/api_pages.json` requests a page that does not exist, on purpose, to show what a failure looks like.

```json
[
  ["AT_test_api_method", {"http_method": "get", "test_url": "http://127.0.0.1:8765/site/index.html",
                          "result_check_dict": {"status_code": 200}}],
  ["AT_test_api_method", {"http_method": "get", "test_url": "http://127.0.0.1:8765/site/missing.html",
                          "result_check_dict": {"status_code": 200}}],
  ["AT_generate_json_report", {"json_file_name": "reports/api_pages"}]
]
```

`tests/load_home.json`

```json
[
  ["LD_start_test", {"user_detail_dict": {"user": "fast_http_user"},
                     "user_count": 5, "spawn_rate": 5, "test_time": 3,
                     "tasks": {"get": {"request_url": "http://127.0.0.1:8765/site/index.html"}}}],
  ["LD_generate_json_report", {"json_file_name": "reports/load_home"}]
]
```

### 3. The Workflow

`tests/test.yaml`

```yaml
pioneer_log: "test_pioneer.log"
jobs:
  steps:
    - name: start_site
      open_program: "python -m http.server 8765 --bind 127.0.0.1"
      redirect_stdout: "site_out.log"
      redirect_stderr: "site_err.log"

    - name: wait_for_site
      wait: 3

    - name: api_smoke
      run: tests/api_smoke.json
      with: api-runner
      artifacts: ["reports/api_smoke_*.json"]

    - name: api_and_load
      parallel_run:
        runners: ["api-runner", "load-runner"]
        scripts: ["tests/api_pages.json", "tests/load_home.json"]
        artifacts:
          - ["reports/api_pages_*.json"]
          - ["reports/load_home_*.json"]

    - name: stop_site
      close_program: start_site
```

Steps run in order. `run` executes one script with one runner; `parallel_run` starts one process per script and waits for all of them. `artifacts` names the files a runner writes, so they are collected and its report is read. Every path is relative to the directory you start TestPioneer in.

### 4. Validate

```bash
python -m test_pioneer validate tests/test.yaml
```

```text
Checked 1 file(s): 0 error(s), 0 warning(s)
```

Nothing is executed. The YAML syntax, the workflow JSON Schema and the lint rules are checked, and each problem is reported with its line and column, for example:

```text
tests/test.yaml:14:13: error: jobs.steps[2].with: 'api-runer' is not one of: gui-runner, web-runner, api-runner, load-runner, file-runner. Did you mean 'api-runner'? [schema-enum]
```

The command exits with status 1 on an error. `--strict` also fails on warnings, and `--format json` prints structured diagnostics for tools. `python -m test_pioneer schema` prints the JSON Schema, which is also published as [`schema/testpioneer.schema.json`](schema/testpioneer.schema.json).

### 5. Run Locally

```bash
python -m test_pioneer run tests/test.yaml
```

```text
Run 20261008T041404Z-1c9e7a52 failed: 3 runner execution(s) (2 passed, 1 failed); artifacts: artifacts/20261008T041404Z-1c9e7a52; 99 recorded test(s), 1 not passed
Report: report/testpioneer-report.json
Report: report/testpioneer-report.html
```

The run failed, and the command exited with status 1, because `api_pages.json` recorded a failed request. (The number of recorded tests changes from run to run: it includes every request of the load test.) Open `report/testpioneer-report.html` to see which one. Then create the page and run again:

```bash
echo "<html><body>found</body></html>" > site/missing.html
python -m test_pioneer run tests/test.yaml
```

```text
Run 20261008T041429Z-427f5a29 passed: 3 runner execution(s) (3 passed); 99 recorded test(s), 0 not passed
Report: report/testpioneer-report.json
Report: report/testpioneer-report.html
```

`python -m test_pioneer -e tests/test.yaml` executes the same workflow and writes the same files, but always exits with status 0, as it did in earlier versions. In Python:

```python
from test_pioneer import execute_yaml

result = execute_yaml("tests/test.yaml")
print(result.status.value, result.summary())
```

### 6. Where the Output Goes

| Path | Written | Content |
|------|---------|---------|
| `report/testpioneer-report.html` | Every run | One page for the whole run: steps, each runner execution, the tests it recorded, links to its artifacts |
| `report/testpioneer-report.json` | Every run | The same result for programs. `--report_formats json,html,junit` adds `report/testpioneer-junit.xml` |
| `artifacts/<run-id>/runners/<runner>/<nn>-<step>/` | A runner that did not pass | `stdout.log`, `stderr.log` and `collected/` with the files named under `artifacts:` |
| `artifacts/<run-id>/testpioneer/` | A run that did not pass | `execution.log` (what TestPioneer did) and `manifest.json` (the result) |
| `test_pioneer.log` | When `pioneer_log` is set | Step log |
| `site_out.log`, `site_err.log` | When `redirect_stdout` / `redirect_stderr` are set | Output of the program started by `open_program` |
| `reports/` | By the runner scripts | Each runner's own report, as its script names it |

A run that passed leaves nothing under `artifacts/`. `--keep_artifacts always`, or `keep_artifacts: always` in the workflow, keeps everything; `artifacts_path` and `report_path` move the two folders.

### 7. Run in CI

```yaml
name: tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: "3.12"
      - run: pip install test_pioneer
      - run: mkdir -p reports
      - name: Validate the workflow
        run: python -m test_pioneer validate tests/test.yaml
      - name: Run the workflow
        run: python -m test_pioneer run tests/test.yaml --report_formats json,html,junit
      - name: Keep the report and the artifacts
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: testpioneer
          path: |
            report/
            artifacts/
```

`validate` fails the job in seconds when the workflow is wrong, `run` fails it when a test fails, and the upload step keeps the report either way.

### 8. Open the Workflow in an Editor

[PyBreeze](https://github.com/Integration-Automation/PyBreeze) is the visual editor of this tool family. Any editor with a YAML language server completes keys and runner names from the schema when the workflow starts with this line:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/Integration-Automation/TestPioneer/main/schema/testpioneer.schema.json
```

A starter project is created with:

```python
from test_pioneer import create_template_dir

create_template_dir()
```

### 9. Troubleshooting

| What you see | Cause and fix |
|--------------|---------------|
| `validate` reports `missing-file` | Script paths are relative to the directory you run from. Run from the project root, or pass `--base_dir`. |
| The run is `failed` although every runner exited normally | A runner recorded a failed test in its report. The HTML report lists it; the raw file is under `artifacts/<run-id>/.../collected/`. |
| Warning `artifact pattern ... matched no file written by this runner` | The script wrote no report: its last action is not a `*_generate_json_report`, the `reports/` folder does not exist, or (web and GUI runners) recording was not switched on with `WR_set_record_enable` / `AC_set_record_enable`. |
| A failed test does not fail the CI job | The job uses `-e`, which always exits with status 0. Use `run`. |
| `gui-runner` is reported as not installed | Install the extra: `pip install test_pioneer[gui]`. |
| `start_site` fails, or the API tests cannot connect | `python` is not on the `PATH` (use `python3` or a full path in `open_program`), or port 8765 is taken. |

## Documentation

Full documentation is available at **[testpioneer.readthedocs.io](https://testpioneer.readthedocs.io/)**.

- [Getting Started](https://testpioneer.readthedocs.io/en/latest/getting-started.html)
- [YAML Configuration](https://testpioneer.readthedocs.io/en/latest/yaml-configuration.html)
- [Validation](https://testpioneer.readthedocs.io/en/latest/validation.html)
- [Run IDs and Artifacts](https://testpioneer.readthedocs.io/en/latest/artifacts.html)
- [Consolidated Report](https://testpioneer.readthedocs.io/en/latest/reports.html)
- [Runners](https://testpioneer.readthedocs.io/en/latest/runners.html)
- [Step Types](https://testpioneer.readthedocs.io/en/latest/step-types.html)
- [Docker](https://testpioneer.readthedocs.io/en/latest/docker.html)
- [API Reference](https://testpioneer.readthedocs.io/en/latest/api-reference.html)

## Available Runners

| Runner | Package | Description |
|--------|---------|-------------|
| `gui-runner` | [AutoControlGUI](https://github.com/Integration-Automation/AutoControlGUI) | Desktop GUI automation |
| `web-runner` | [WebRunner](https://github.com/Integration-Automation/WebRunner) | Web browser automation |
| `api-runner` | [APITestka](https://github.com/Integration-Automation/APITestka) | REST API testing |
| `load-runner` | [LoadDensity](https://github.com/Integration-Automation/LoadDensity) | Load & stress testing |
| `file-runner` | [FileAutomation](https://github.com/Integration-Automation/FileAutomation) | File, archive and cloud-storage actions (`FA_*`) |

## Automation IDE

For a visual editing experience, see [PyBreeze](https://github.com/Integration-Automation/PyBreeze).

## License

[MIT](LICENSE)
