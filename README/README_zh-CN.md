# TestPioneer

[![Documentation Status](https://readthedocs.org/projects/testpioneer/badge/?version=latest)](https://testpioneer.readthedocs.io/en/latest/?badge=latest)
[![CI](https://github.com/Integration-Automation/TestPioneer/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/TestPioneer/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/test_pioneer)](https://pypi.org/project/test_pioneer/)
[![Python](https://img.shields.io/pypi/pyversions/test_pioneer)](https://pypi.org/project/test_pioneer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)

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

## 文档

完整文档请参阅 **[testpioneer.readthedocs.io](https://testpioneer.readthedocs.io/)**。

- [快速开始](https://testpioneer.readthedocs.io/en/latest/getting-started.html)
- [YAML 配置](https://testpioneer.readthedocs.io/en/latest/yaml-configuration.html)
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

## 自动化 IDE

如需可视化编辑体验，请参阅 [PyBreeze](https://github.com/Integration-Automation/PyBreeze)。

## 许可证

[MIT](../LICENSE)
