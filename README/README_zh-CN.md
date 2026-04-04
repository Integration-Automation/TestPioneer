# TestPioneer

以 YAML 驱动的自动化测试框架，专为 CI/CD 流程设计，支持 GUI、Web、API 与负载测试，通过可插拔的 Runner 架构运作。

## 功能特色

- **多类型测试** - 通过可插拔 Runner 支持 GUI、Web、API 及负载/压力测试
- **YAML 配置** - 人类可读的测试流程，易于维护与版本控制
- **并行执行** - 使用不同 Runner 同时执行多个测试脚本
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

### 命令行

```bash
python -m test_pioneer -e path/to/test.yaml
```

### Python

```python
from test_pioneer import execute_yaml

execute_yaml("path/to/test.yaml")
```

### 项目模板

```python
from test_pioneer import create_template_dir

create_template_dir()
```

## YAML 配置文件

```yaml
pioneer_log: "test_pioneer.log"       # 可选：日志文件路径
recording_path: "test_video"          # 可选：视频录制输出路径
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

## 可用 Runner

| Runner | 包 | 说明 |
|--------|---|------|
| `gui-runner` | [je_auto_control](https://github.com/Integration-Automation/je_auto_control) | 桌面 GUI 自动化 |
| `web-runner` | [je_web_runner](https://github.com/Integration-Automation/je_web_runner) | 网页浏览器自动化 |
| `api-runner` | [je_api_testka](https://github.com/Integration-Automation/je_api_testka) | REST API 测试 |
| `load-runner` | [je_load_density](https://github.com/Integration-Automation/je_load_density) | 负载与压力测试 |

## 步骤类型

| 步骤 | 说明 |
|------|------|
| `run` | 使用指定 Runner 执行 JSON 测试脚本 |
| `run_folder` | 执行文件夹内所有测试文件 |
| `parallel_run` | 同时执行多个脚本 |
| `wait` | 暂停执行指定秒数 |
| `open_url` | 在默认浏览器打开 URL |
| `download_file` | 从 URL 下载文件 |
| `open_program` | 启动外部程序 |
| `close_program` | 终止运行中的程序 |
| `unzip_zipfile` | 解压缩 zip 文件 |

## 自动化 IDE

如需可视化编辑体验，请参阅 [PyBreeze](https://github.com/Integration-Automation/PyBreeze)。

## 许可证

[MIT](../LICENSE)
