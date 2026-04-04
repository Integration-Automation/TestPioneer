# TestPioneer

[![Documentation Status](https://readthedocs.org/projects/testpioneer/badge/?version=latest)](https://testpioneer.readthedocs.io/en/latest/?badge=latest)
[![CI](https://github.com/Integration-Automation/TestPioneer/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/TestPioneer/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/test_pioneer)](https://pypi.org/project/test_pioneer/)
[![Python](https://img.shields.io/pypi/pyversions/test_pioneer)](https://pypi.org/project/test_pioneer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)

以 YAML 驅動的自動化測試框架，專為 CI/CD 流程設計，支援 GUI、Web、API 與負載測試，透過可插拔的 Runner 架構運作。

## 功能特色

- **多類型測試** - 透過可插拔 Runner 支援 GUI、Web、API 及負載/壓力測試
- **YAML 設定** - 人類可讀的測試流程，易於維護與版本控制
- **平行執行** - 使用不同 Runner 同時執行多個測試腳本
- **影片錄製** - 內建測試過程錄影功能，方便除錯
- **程序管理** - 啟動/終止外部程式，支援 stdout/stderr 重新導向
- **跨平台** - 支援 Windows、macOS 及 Linux（Python 3.10+）

## 安裝

```bash
pip install test_pioneer
```

包含 GUI 自動化支援：

```bash
pip install test_pioneer[gui]
```

## 快速開始

### 命令列

```bash
python -m test_pioneer -e path/to/test.yaml
```

### Python

```python
from test_pioneer import execute_yaml

execute_yaml("path/to/test.yaml")
```

### 專案範本

```python
from test_pioneer import create_template_dir

create_template_dir()
```

## 文件

完整文件請參閱 **[testpioneer.readthedocs.io](https://testpioneer.readthedocs.io/)**。

- [快速開始](https://testpioneer.readthedocs.io/en/latest/getting-started.html)
- [YAML 設定](https://testpioneer.readthedocs.io/en/latest/yaml-configuration.html)
- [Runner](https://testpioneer.readthedocs.io/en/latest/runners.html)
- [步驟類型](https://testpioneer.readthedocs.io/en/latest/step-types.html)
- [Docker](https://testpioneer.readthedocs.io/en/latest/docker.html)
- [API 參考](https://testpioneer.readthedocs.io/en/latest/api-reference.html)

## 可用 Runner

| Runner | 套件 | 說明 |
|--------|------|------|
| `gui-runner` | [AutoControlGUI](https://github.com/Integration-Automation/AutoControlGUI) | 桌面 GUI 自動化 |
| `web-runner` | [WebRunner](https://github.com/Integration-Automation/WebRunner) | 網頁瀏覽器自動化 |
| `api-runner` | [APITestka](https://github.com/Integration-Automation/APITestka) | REST API 測試 |
| `load-runner` | [LoadDensity](https://github.com/Integration-Automation/LoadDensity) | 負載與壓力測試 |

## 自動化 IDE

如需視覺化編輯體驗，請參閱 [PyBreeze](https://github.com/Integration-Automation/PyBreeze)。

## 授權條款

[MIT](../LICENSE)
