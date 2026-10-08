# TestPioneer

[![Documentation Status](https://readthedocs.org/projects/testpioneer/badge/?version=latest)](https://testpioneer.readthedocs.io/en/latest/?badge=latest)
[![CI](https://github.com/Integration-Automation/TestPioneer/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/TestPioneer/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/test_pioneer)](https://pypi.org/project/test_pioneer/)
[![Python](https://img.shields.io/pypi/pyversions/test_pioneer)](https://pypi.org/project/test_pioneer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)

**语言：[English](../README.md) | [繁體中文](README_zh-TW.md) | 简体中文**

以 YAML 驱动的自动化测试框架，专为 CI/CD 流程设计，支持 GUI、Web、API 与负载测试，通过可插拔的 Runner 架构运作。

## 功能特色

- **多类型测试** - 通过可插拔 Runner 支持 GUI、Web、API 及负载/压力测试
- **YAML 配置** - 人类可读的测试流程，易于维护与版本控制
- **流程验证** - 执行前先以带版本的 JSON Schema 与 lint 规则检查流程
- **并行执行** - 使用不同 Runner 同时执行多个测试脚本
- **执行产物** - 每次执行都有一个 ID；失败的 Runner 其输出、退出码与文件都会保留
- **单一报告** - 所有 Runner 的结果合并成一份 JSON 与 HTML 报告，并可选择输出 JUnit XML
- **视频录制** - 内置测试过程录像功能，方便调试
- **进程管理** - 启动/终止外部程序，支持 stdout/stderr 重定向
- **跨平台** - 支持 Windows、macOS 及 Linux（Python 3.10+）

## 安装

```bash
pip install test_pioneer
```

包含 GUI 自动化支持：

```bash
pip install test_pioneer[gui]
```

## 快速开始

一个完整的示例：流程会启动一个小网站，用 API Runner 测试它，接着并行执行一个 API 脚本与一个负载测试。只需要 `pip install test_pioneer`，不需要浏览器，也不需要任何外部服务。

### 1. 项目结构

```text
my_project/
├── tests/
│   ├── test.yaml          # 流程
│   ├── api_smoke.json     # API Runner 脚本
│   ├── api_pages.json     # API Runner 脚本
│   └── load_home.json     # 负载 Runner 脚本
├── site/
│   └── index.html         # 示例所提供并测试的页面
└── reports/               # Runner 把报告写在这里
```

创建这些文件夹与页面。Runner 不会自己创建 `reports/`。

```bash
mkdir tests
mkdir site
mkdir reports
echo "<html><body>hello</body></html>" > site/index.html
```

### 2. Runner 脚本

Runner 脚本是一份 JSON 动作列表。每个脚本的最后一个动作都是写出该 Runner 的报告。

`tests/api_smoke.json`

```json
[
  ["AT_test_api_method", {"http_method": "get", "test_url": "http://127.0.0.1:8765/site/index.html",
                          "result_check_dict": {"status_code": 200}}],
  ["AT_generate_json_report", {"json_file_name": "reports/api_smoke"}]
]
```

`tests/api_pages.json` 故意请求一个不存在的页面，用来演示失败时的样子。

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

### 3. 流程

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

步骤按顺序执行。`run` 用一个 Runner 执行一个脚本；`parallel_run` 为每个脚本各启动一个进程，并等待全部结束。`artifacts` 列出 Runner 写出的文件，这些文件会被收集起来，Runner 的报告也由此读取。所有路径都相对于你启动 TestPioneer 的目录。

### 4. 验证

```bash
python -m test_pioneer validate tests/test.yaml
```

```text
Checked 1 file(s): 0 error(s), 0 warning(s)
```

不会执行任何步骤。命令会检查 YAML 语法、流程 JSON Schema 与 lint 规则，并为每个问题标出行号与列号，例如：

```text
tests/test.yaml:14:13: error: jobs.steps[2].with: 'api-runer' is not one of: gui-runner, web-runner, api-runner, load-runner, file-runner. Did you mean 'api-runner'? [schema-enum]
```

只要有错误，命令就以状态码 1 结束。`--strict` 会让警告也视为失败，`--format json` 则输出给工具使用的结构化诊断。`python -m test_pioneer schema` 会打印 JSON Schema，同一份内容也发布于 [`schema/testpioneer.schema.json`](../schema/testpioneer.schema.json)。

### 5. 在本机执行

```bash
python -m test_pioneer run tests/test.yaml
```

```text
Run 20261008T041404Z-1c9e7a52 failed: 3 runner execution(s) (2 passed, 1 failed); artifacts: artifacts/20261008T041404Z-1c9e7a52; 99 recorded test(s), 1 not passed
Report: report/testpioneer-report.json
Report: report/testpioneer-report.html
```

这次执行失败，命令以状态码 1 结束，因为 `api_pages.json` 记录了一条失败的请求。（记录的测试数量每次执行都不同：它包含负载测试的每一个请求。）打开 `report/testpioneer-report.html` 就能看到是哪一条。接着创建那个页面，再执行一次：

```bash
echo "<html><body>found</body></html>" > site/missing.html
python -m test_pioneer run tests/test.yaml
```

```text
Run 20261008T041429Z-427f5a29 passed: 3 runner execution(s) (3 passed); 99 recorded test(s), 0 not passed
Report: report/testpioneer-report.json
Report: report/testpioneer-report.html
```

`python -m test_pioneer -e tests/test.yaml` 会执行同一个流程并写出相同的文件，但始终以状态码 0 结束，与先前的版本相同。在 Python 中：

```python
from test_pioneer import execute_yaml

result = execute_yaml("tests/test.yaml")
print(result.status.value, result.summary())
```

### 6. 输出放在哪里

| 路径 | 何时写出 | 内容 |
|------|----------|------|
| `report/testpioneer-report.html` | 每次执行 | 整次执行的单一页面：步骤、每次 Runner 执行、它记录的测试，以及指向其产物的链接 |
| `report/testpioneer-report.json` | 每次执行 | 给程序读取的同一份结果。`--report_formats json,html,junit` 会另外写出 `report/testpioneer-junit.xml` |
| `artifacts/<run-id>/runners/<runner>/<nn>-<step>/` | Runner 未通过时 | `stdout.log`、`stderr.log`，以及放有 `artifacts:` 所列文件的 `collected/` |
| `artifacts/<run-id>/testpioneer/` | 执行未通过时 | `execution.log`（TestPioneer 做了什么）与 `manifest.json`（结果） |
| `test_pioneer.log` | 设置了 `pioneer_log` 时 | 步骤日志 |
| `site_out.log`、`site_err.log` | 设置了 `redirect_stdout` / `redirect_stderr` 时 | `open_program` 所启动程序的输出 |
| `reports/` | 由 Runner 脚本写出 | 各 Runner 自己的报告，文件名由脚本指定 |

通过的执行不会在 `artifacts/` 下留下任何东西。`--keep_artifacts always`，或在流程中写 `keep_artifacts: always`，会全部保留；`artifacts_path` 与 `report_path` 可改变这两个文件夹的位置。

### 7. 在 CI 中执行

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

流程有误时，`validate` 在几秒内就让任务失败；测试失败时，`run` 让任务失败；不论结果如何，上传步骤都会保留报告。

### 8. 在编辑器中打开流程

[PyBreeze](https://github.com/Integration-Automation/PyBreeze) 是这个工具家族的可视化编辑器。任何带有 YAML language server 的编辑器，只要流程的第一行是下面这一行，就能按 Schema 补全键名与 Runner 名称：

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/Integration-Automation/TestPioneer/main/schema/testpioneer.schema.json
```

创建起始项目：

```python
from test_pioneer import create_template_dir

create_template_dir()
```

### 9. 疑难排查

| 现象 | 原因与解法 |
|------|------------|
| `validate` 报告 `missing-file` | 脚本路径相对于你执行命令的目录。请从项目根目录执行，或加上 `--base_dir`。 |
| 每个 Runner 都正常结束，执行却是 `failed` | 有 Runner 在自己的报告中记录了失败的测试。HTML 报告会列出它；原始文件在 `artifacts/<run-id>/.../collected/` 下。 |
| 警告 `artifact pattern ... matched no file written by this runner` | 脚本没有写出报告：最后一个动作不是 `*_generate_json_report`、`reports/` 文件夹不存在，或（Web 与 GUI Runner）没有用 `WR_set_record_enable` / `AC_set_record_enable` 开启记录。 |
| 测试失败了，CI 任务却没有失败 | 任务使用的是 `-e`，它始终以状态码 0 结束。请改用 `run`。 |
| 报告 `gui-runner` 未安装 | 安装额外依赖：`pip install test_pioneer[gui]`。 |
| `start_site` 失败，或 API 测试连不上 | `python` 不在 `PATH` 中（在 `open_program` 改用 `python3` 或完整路径），或 8765 端口已被占用。 |

## 文档

完整文档请参阅 **[testpioneer.readthedocs.io](https://testpioneer.readthedocs.io/)**。

- [快速开始](https://testpioneer.readthedocs.io/en/latest/getting-started.html)
- [YAML 配置](https://testpioneer.readthedocs.io/en/latest/yaml-configuration.html)
- [验证](https://testpioneer.readthedocs.io/en/latest/validation.html)
- [执行 ID 与产物](https://testpioneer.readthedocs.io/en/latest/artifacts.html)
- [合并报告](https://testpioneer.readthedocs.io/en/latest/reports.html)
- [Runner](https://testpioneer.readthedocs.io/en/latest/runners.html)
- [步骤类型](https://testpioneer.readthedocs.io/en/latest/step-types.html)
- [Docker](https://testpioneer.readthedocs.io/en/latest/docker.html)
- [API 参考](https://testpioneer.readthedocs.io/en/latest/api-reference.html)

## 可用 Runner

| Runner | 包 | 说明 |
|--------|---|------|
| `gui-runner` | [AutoControlGUI](https://github.com/Integration-Automation/AutoControlGUI) | 桌面 GUI 自动化 |
| `web-runner` | [WebRunner](https://github.com/Integration-Automation/WebRunner) | 网页浏览器自动化 |
| `api-runner` | [APITestka](https://github.com/Integration-Automation/APITestka) | REST API 测试 |
| `load-runner` | [LoadDensity](https://github.com/Integration-Automation/LoadDensity) | 负载与压力测试 |
| `file-runner` | [FileAutomation](https://github.com/Integration-Automation/FileAutomation) | 文件、压缩包与云存储操作（`FA_*`） |

## 自动化 IDE

如需可视化编辑体验，请参阅 [PyBreeze](https://github.com/Integration-Automation/PyBreeze)。

## 许可证

[MIT](../LICENSE)
