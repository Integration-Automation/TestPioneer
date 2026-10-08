# TestPioneer

[![Documentation Status](https://readthedocs.org/projects/testpioneer/badge/?version=latest)](https://testpioneer.readthedocs.io/en/latest/?badge=latest)
[![CI](https://github.com/Integration-Automation/TestPioneer/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/TestPioneer/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/test_pioneer)](https://pypi.org/project/test_pioneer/)
[![Python](https://img.shields.io/pypi/pyversions/test_pioneer)](https://pypi.org/project/test_pioneer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)

**語言：[English](../README.md) | 繁體中文 | [简体中文](README_zh-CN.md)**

以 YAML 驅動的自動化測試框架，專為 CI/CD 流程設計，支援 GUI、Web、API 與負載測試，透過可插拔的 Runner 架構運作。

## 功能特色

- **多類型測試** - 透過可插拔 Runner 支援 GUI、Web、API 及負載/壓力測試
- **YAML 設定** - 人類可讀的測試流程，易於維護與版本控制
- **流程驗證** - 執行前先以具版本的 JSON Schema 與 lint 規則檢查流程
- **平行執行** - 使用不同 Runner 同時執行多個測試腳本
- **執行產物** - 每次執行都有一個 ID；失敗的 Runner 其輸出、結束代碼與檔案都會保留
- **單一報告** - 所有 Runner 的結果合併成一份 JSON 與 HTML 報告，並可選擇輸出 JUnit XML
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

一個完整的範例：流程會啟動一個小網站，用 API Runner 測試它，接著平行執行一支 API 腳本與一個負載測試。只需要 `pip install test_pioneer`，不需要瀏覽器，也不需要任何外部服務。

### 1. 專案結構

```text
my_project/
├── tests/
│   ├── test.yaml          # 流程
│   ├── api_smoke.json     # API Runner 腳本
│   ├── api_pages.json     # API Runner 腳本
│   └── load_home.json     # 負載 Runner 腳本
├── site/
│   └── index.html         # 範例所提供並測試的頁面
└── reports/               # Runner 把報告寫在這裡
```

建立這些資料夾與頁面。Runner 不會自己建立 `reports/`。

```bash
mkdir tests
mkdir site
mkdir reports
echo "<html><body>hello</body></html>" > site/index.html
```

### 2. Runner 腳本

Runner 腳本是一份 JSON 動作清單。每一支腳本的最後一個動作都是寫出該 Runner 的報告。

`tests/api_smoke.json`

```json
[
  ["AT_test_api_method", {"http_method": "get", "test_url": "http://127.0.0.1:8765/site/index.html",
                          "result_check_dict": {"status_code": 200}}],
  ["AT_generate_json_report", {"json_file_name": "reports/api_smoke"}]
]
```

`tests/api_pages.json` 刻意請求一個不存在的頁面，用來示範失敗時的樣子。

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

步驟依序執行。`run` 以一個 Runner 執行一支腳本；`parallel_run` 為每支腳本各啟動一個程序，並等待全部結束。`artifacts` 列出 Runner 寫出的檔案，這些檔案會被收集起來，Runner 的報告也由此讀取。所有路徑都相對於你啟動 TestPioneer 的目錄。

### 4. 驗證

```bash
python -m test_pioneer validate tests/test.yaml
```

```text
Checked 1 file(s): 0 error(s), 0 warning(s)
```

不會執行任何步驟。指令會檢查 YAML 語法、流程 JSON Schema 與 lint 規則，並為每個問題標出行號與欄號，例如：

```text
tests/test.yaml:14:13: error: jobs.steps[2].with: 'api-runer' is not one of: gui-runner, web-runner, api-runner, load-runner, file-runner. Did you mean 'api-runner'? [schema-enum]
```

只要有錯誤，指令就以狀態碼 1 結束。`--strict` 會讓警告也視為失敗，`--format json` 則輸出給工具使用的結構化診斷。`python -m test_pioneer schema` 會印出 JSON Schema，同一份內容也發佈於 [`schema/testpioneer.schema.json`](../schema/testpioneer.schema.json)。

### 5. 在本機執行

```bash
python -m test_pioneer run tests/test.yaml
```

```text
Run 20261008T041404Z-1c9e7a52 failed: 3 runner execution(s) (2 passed, 1 failed); artifacts: artifacts/20261008T041404Z-1c9e7a52; 99 recorded test(s), 1 not passed
Report: report/testpioneer-report.json
Report: report/testpioneer-report.html
```

這次執行失敗，指令以狀態碼 1 結束，因為 `api_pages.json` 記錄了一筆失敗的請求。（記錄的測試數量每次執行都不同：它包含負載測試的每一個請求。）打開 `report/testpioneer-report.html` 就能看到是哪一筆。接著建立那個頁面，再執行一次：

```bash
echo "<html><body>found</body></html>" > site/missing.html
python -m test_pioneer run tests/test.yaml
```

```text
Run 20261008T041429Z-427f5a29 passed: 3 runner execution(s) (3 passed); 99 recorded test(s), 0 not passed
Report: report/testpioneer-report.json
Report: report/testpioneer-report.html
```

`python -m test_pioneer -e tests/test.yaml` 會執行同一個流程並寫出相同的檔案，但一律以狀態碼 0 結束，與先前的版本相同。在 Python 中：

```python
from test_pioneer import execute_yaml

result = execute_yaml("tests/test.yaml")
print(result.status.value, result.summary())
```

### 6. 輸出放在哪裡

| 路徑 | 何時寫出 | 內容 |
|------|----------|------|
| `report/testpioneer-report.html` | 每次執行 | 整次執行的單一頁面：步驟、每次 Runner 執行、它記錄的測試，以及連到其產物的連結 |
| `report/testpioneer-report.json` | 每次執行 | 給程式讀取的同一份結果。`--report_formats json,html,junit` 會另外寫出 `report/testpioneer-junit.xml` |
| `artifacts/<run-id>/runners/<runner>/<nn>-<step>/` | Runner 未通過時 | `stdout.log`、`stderr.log`，以及放有 `artifacts:` 所列檔案的 `collected/` |
| `artifacts/<run-id>/testpioneer/` | 執行未通過時 | `execution.log`（TestPioneer 做了什麼）與 `manifest.json`（結果） |
| `test_pioneer.log` | 設定了 `pioneer_log` 時 | 步驟日誌 |
| `site_out.log`、`site_err.log` | 設定了 `redirect_stdout` / `redirect_stderr` 時 | `open_program` 所啟動程式的輸出 |
| `reports/` | 由 Runner 腳本寫出 | 各 Runner 自己的報告，檔名由腳本指定 |

通過的執行不會在 `artifacts/` 下留下任何東西。`--keep_artifacts always`，或在流程中寫 `keep_artifacts: always`，會全部保留；`artifacts_path` 與 `report_path` 可改變這兩個資料夾的位置。

### 7. 在 CI 中執行

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

流程有誤時，`validate` 在幾秒內就讓工作失敗；測試失敗時，`run` 讓工作失敗；不論結果如何，上傳步驟都會保留報告。

### 8. 在編輯器中開啟流程

[PyBreeze](https://github.com/Integration-Automation/PyBreeze) 是這個工具家族的視覺化編輯器。任何具備 YAML language server 的編輯器，只要流程的第一行是下面這一行，就能依 Schema 補全鍵名與 Runner 名稱：

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/Integration-Automation/TestPioneer/main/schema/testpioneer.schema.json
```

建立起始專案：

```python
from test_pioneer import create_template_dir

create_template_dir()
```

### 9. 疑難排解

| 現象 | 原因與解法 |
|------|------------|
| `validate` 回報 `missing-file` | 腳本路徑相對於你執行指令的目錄。請從專案根目錄執行，或加上 `--base_dir`。 |
| 每個 Runner 都正常結束，執行卻是 `failed` | 有 Runner 在自己的報告中記錄了失敗的測試。HTML 報告會列出它；原始檔在 `artifacts/<run-id>/.../collected/` 下。 |
| 警告 `artifact pattern ... matched no file written by this runner` | 腳本沒有寫出報告：最後一個動作不是 `*_generate_json_report`、`reports/` 資料夾不存在，或（Web 與 GUI Runner）沒有用 `WR_set_record_enable` / `AC_set_record_enable` 開啟記錄。 |
| 測試失敗了，CI 工作卻沒有失敗 | 工作使用的是 `-e`，它一律以狀態碼 0 結束。請改用 `run`。 |
| 回報 `gui-runner` 未安裝 | 安裝額外套件：`pip install test_pioneer[gui]`。 |
| `start_site` 失敗，或 API 測試連不上 | `python` 不在 `PATH` 中（在 `open_program` 改用 `python3` 或完整路徑），或 8765 埠已被占用。 |

## 文件

完整文件請參閱 **[testpioneer.readthedocs.io](https://testpioneer.readthedocs.io/)**。

- [快速開始](https://testpioneer.readthedocs.io/en/latest/getting-started.html)
- [YAML 設定](https://testpioneer.readthedocs.io/en/latest/yaml-configuration.html)
- [驗證](https://testpioneer.readthedocs.io/en/latest/validation.html)
- [執行 ID 與產物](https://testpioneer.readthedocs.io/en/latest/artifacts.html)
- [合併報告](https://testpioneer.readthedocs.io/en/latest/reports.html)
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
| `file-runner` | [FileAutomation](https://github.com/Integration-Automation/FileAutomation) | 檔案、壓縮檔與雲端儲存操作（`FA_*`） |

## 自動化 IDE

如需視覺化編輯體驗，請參閱 [PyBreeze](https://github.com/Integration-Automation/PyBreeze)。

## 授權條款

[MIT](../LICENSE)
