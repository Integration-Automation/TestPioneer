# TestPioneer

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

## YAML Configuration

```yaml
pioneer_log: "test_pioneer.log"       # Optional: log file path
recording_path: "test_video"          # Optional: video recording output
jobs:
  steps:
    - name: run_api_test
      run: tests/api_test.json
      with: api-runner

    - name: wait_for_service
      wait: 5

    - name: run_web_test
      run: tests/web_test.json
      with: web-runner

    - name: open_docs
      open_url: https://example.com
      url_open_method: open_new_tab    # open | open_new | open_new_tab

    - name: launch_app
      open_program: path/to/program
      redirect_stdout: output.log
      redirect_stderr: errors.log

    - name: parallel_tests
      parallel_run:
        runners: ["web-runner", "api-runner"]
        scripts: ["./tests/web.json", "./tests/api.json"]
```

## Available Runners

| Runner | Package | Description |
|--------|---------|-------------|
| `gui-runner` | [je_auto_control](https://github.com/Integration-Automation/je_auto_control) | Desktop GUI automation |
| `web-runner` | [je_web_runner](https://github.com/Integration-Automation/je_web_runner) | Web browser automation |
| `api-runner` | [je_api_testka](https://github.com/Integration-Automation/je_api_testka) | REST API testing |
| `load-runner` | [je_load_density](https://github.com/Integration-Automation/je_load_density) | Load & stress testing |

## Step Types

| Step | Description |
|------|-------------|
| `run` | Execute a JSON test script with a specified runner |
| `run_folder` | Run all test files in a directory |
| `parallel_run` | Run multiple scripts concurrently |
| `wait` | Pause execution for specified seconds |
| `open_url` | Open a URL in the default browser |
| `download_file` | Download a file from a URL |
| `open_program` | Launch an external program |
| `close_program` | Terminate a running program |
| `unzip_zipfile` | Extract a zip archive |

## Automation IDE

For a visual editing experience, see [PyBreeze](https://github.com/Integration-Automation/PyBreeze).

## License

[MIT](LICENSE)