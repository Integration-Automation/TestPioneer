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
- **Parallel execution** - Run multiple test scripts concurrently with different runners
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

### Project Template

```python
from test_pioneer import create_template_dir

create_template_dir()
```

## Documentation

Full documentation is available at **[testpioneer.readthedocs.io](https://testpioneer.readthedocs.io/)**.

- [Getting Started](https://testpioneer.readthedocs.io/en/latest/getting-started.html)
- [YAML Configuration](https://testpioneer.readthedocs.io/en/latest/yaml-configuration.html)
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

## Automation IDE

For a visual editing experience, see [PyBreeze](https://github.com/Integration-Automation/PyBreeze).

## License

[MIT](LICENSE)
