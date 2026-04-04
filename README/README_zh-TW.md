# TestPioneer

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

## YAML 設定檔

```yaml
pioneer_log: "test_pioneer.log"       # 選填：日誌檔案路徑
recording_path: "test_video"          # 選填：影片錄製輸出路徑
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

| Runner | 套件 | 說明 |
|--------|------|------|
| `gui-runner` | [AutoControlGUI](https://github.com/Integration-Automation/AutoControlGUI) | 桌面 GUI 自動化 |
| `web-runner` | [WebRunner](https://github.com/Integration-Automation/WebRunner) | 網頁瀏覽器自動化 |
| `api-runner` | [APITestka](https://github.com/Integration-Automation/APITestka) | REST API 測試 |
| `load-runner` | [LoadDensity](https://github.com/Integration-Automation/LoadDensity) | 負載與壓力測試 |

## 步驟類型

| 步驟 | 說明 |
|------|------|
| `run` | 使用指定 Runner 執行 JSON 測試腳本 |
| `run_folder` | 執行資料夾內所有測試檔案 |
| `parallel_run` | 同時執行多個腳本 |
| `wait` | 暫停執行指定秒數 |
| `open_url` | 在預設瀏覽器開啟 URL |
| `download_file` | 從 URL 下載檔案 |
| `open_program` | 啟動外部程式 |
| `close_program` | 終止執行中的程式 |
| `unzip_zipfile` | 解壓縮 zip 檔案 |

## 自動化 IDE

如需視覺化編輯體驗，請參閱 [PyBreeze](https://github.com/Integration-Automation/PyBreeze)。

## 授權條款

[MIT](../LICENSE)
