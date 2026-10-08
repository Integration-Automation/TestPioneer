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

### Command Line

```bash
python -m test_pioneer -e path/to/test.yaml
```

### Python

```python
from test_pioneer import execute_yaml

execute_yaml("path/to/test.yaml")
```

### Run with a Result

```bash
python -m test_pioneer run path/to/test.yaml
```

Executes the workflow like `-e`, but exits with status 1 when the run did not pass, so a CI job fails with the tests. For a run that did not pass, `artifacts/<run-id>/` keeps each failed runner's `stdout.log`, `stderr.log` and the files it wrote, plus TestPioneer's own `execution.log` and a `manifest.json` with every step and runner. Use `--keep_artifacts always` to keep them for passing runs too. `execute_yaml()` returns the same result in Python.

Every run also writes `report/testpioneer-report.json` and `report/testpioneer-report.html`: one report for all runners, with the tests each runner recorded and links to its artifacts. Add `--report_formats json,html,junit` for JUnit XML. A step lists the report files its runner writes under `artifacts:`, which is also how a failed action is detected, since the runners exit with status 0 either way.

### Validate a Workflow

```bash
python -m test_pioneer validate path/to/test.yaml
```

Checks the YAML syntax, the workflow JSON Schema and the lint rules without executing anything. Each problem is reported with its line and column, and the command exits with status 1 on an error, so CI can fail before any test runs. Add `--format json` for structured output and `--strict` to treat warnings as errors.

```bash
python -m test_pioneer schema
```

Prints the workflow JSON Schema, also published as [`schema/testpioneer.schema.json`](schema/testpioneer.schema.json).

### Project Template

```python
from test_pioneer import create_template_dir

create_template_dir()
```

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
