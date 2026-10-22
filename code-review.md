# 程式審核：TestPioneer

## 審核者

- 審核者：工作區程式審核
- 日期：2026-10-22
- 對象：`TestPioneer`（工作樹熱點：YAML 編排、多 runner 分派、子行程組命令、舊式 CLI 旗標）
- 結論：有條件通過

無未關閉缺陷，故不是需修正。YAML 載入、`--execute_file`／`-e` 契約，以及「不可信字串不進 shell」這三項沒有立即損害。三則建議仍未關閉，故不是無保留通過。

## 審核規範

本次用下列十條。更嚴的數字從嚴（見文末「本專案加嚴」）。

1. 設計：步驟分派、runner 介面與跨專案邊界要和 `architecture.md` 一致，不另開第二套命令列。
2. 可讀性：認知複雜度 ≤ 15、函式 ≤ 80 行、巢狀 ≤ 4、參數 ≤ 7、行 ≤ 120。專案自訂更嚴者從嚴。
3. 錯誤處理：不裸 `except:`；失敗要留下可判斷的結果，不把型別錯誤變成未處理的 `TypeError`。
4. 死碼：熱點路徑上不留執行不到、又與現行契約矛盾的分支。
5. 型別與 docstring：公開函式有型別與說明；簽名寫 `str` 時，實際回傳不得靜默變成 `None`。
6. 安全：YAML 只用 `yaml.safe_load` 或 `yaml.SafeLoader`；子行程只用參數陣列；禁止 `shell=True`、`os.system`、`eval`、`exec`、`pickle.loads`、`verify=False`。
7. 測試：熱點契約在現有測試裡看得到（本次未執行測試）。
8. 效能：子行程等待方式與 `architecture.md` §4 的輪詢描述一致；不把未宣告的逾時欄位當成缺陷。
9. `architecture.md` §6：PyBreeze 的 `-e`、`create_template_dir`，以及 runner 的 `--execute_file` 與套件名不得漂移。
10. 文件同步：`docs/migration.rst`、`docs/step-types.rst`、`docs/api-reference.rst` 與 CLI、組命令方式一致。

嚴重度：缺陷（行為錯誤或可被直接利用，未關閉則結論為需修正）、建議（應改，但無立即損害）、備註（已核對、不另開項目）。

## 審核紀錄

### 方法

讀了 `architecture.md`（含 §6、§7）、`CLAUDE.md` 的安全、錯誤處理與複雜度、`progress.md` 開頭（檔案只到未完項 #9、#13，不足 80 行）。在 `test_pioneer/` 搜尋 `eval(`、`exec(`、`shell=True`、`pickle`、`yaml.load`、`yaml.safe_load`、`verify=False`、裸 `except:`、`subprocess`。排除 `test/`、`build/`、`dist/`、`__pycache__/`。下列每一則都對過原始檔。未跑測試、未啟動程式、未改其他檔、未呼叫其他 runner。

### 發現

#### CR-01 · 建議 · `executor_path` 可能以 `None` 進入 argv，且只接住 `OSError`

- 位置：`test_pioneer/executor/run/parallel_run.py` 的 `_resolve_executor_path`（約第 66–72 行）與 `parallel_run`（約第 182–188 行）；`test_pioneer/runner/adapter.py` 的 `ModuleRunner.command`（約第 53–55 行）；`_start_single_process`（約第 94–98 行）。
- 說明：`executor_path` 為空時改用 `sys.executable`。若結果正好是 `"py.exe"`，或此時仍是 `None`，則改為 `shutil.which("python3") or shutil.which("python")`。兩者都不在 PATH 上時函式回傳 `None`。`command` 仍組成 `[executor, "-m", package, "--execute_file", script]`，`Popen` 對 `None` 丟出 `TypeError`。啟動處只接 `OSError`，這個 `TypeError` 會冒出 `parallel_run`。`execute_yaml` 不跑 schema，非字串的 `executor_path`（例如數字）也會走同一條未接住的路。這不是 shell：字串會整段當成執行檔路徑，不會被殼層拆開。
- 依據：可讀性與型別（簽名寫 `Optional[str]`，呼叫端當成 `str`）；錯誤處理；安全項只確認沒有送進 shell。
- 狀態：未關閉
- 建議：`which` 失敗或型別不是 `str` 時，記一筆 runner 錯誤並跳過該程序，不要把 `None` 放進 argv。`"py.exe"` 若要保留，應在找不到替代解譯器時明確失敗。

#### CR-02 · 建議 · `open_program` 先註冊再啟動，失敗時名稱與重導向檔都留下

- 位置：`test_pioneer/executor/program/external_program.py` 約第 96–111 行；`test_pioneer/process/execute_process.py` 的 `start_process` 約第 51–71 行。
- 說明：名稱寫入 `process_manager_instance.process_dict` 之後才呼叫 `start_process`。重導向路徑用 `open(..., "w")` 打開，沒有 `try`／`finally`。`Popen` 或第二個 `open` 失敗時，已開的檔不會關，名稱也留在字典裡。`exit_program` 只在行程已存在時收尾。同一程序稍後再用這個步驟名稱呼叫 `open_program`，會被「已經開啟」擋下。`shell=False` 與 `shlex.split` 這段是對的，不在此項。
- 依據：錯誤處理；資源要用完即關（`CLAUDE.md` 對檔案與 context manager 的要求）。同一程序多次 `execute_yaml` 才看得到殘留名稱；單次 CLI 程序結束後不會留下。
- 狀態：未關閉
- 建議：`start_process` 成功後再註冊。`open` 與 `Popen` 放在同一段清理裡，失敗時關掉已開的檔並拿掉名稱。

#### CR-03 · 建議 · `open_program` 超過函式長度上限

- 位置：`test_pioneer/executor/program/external_program.py` 的 `open_program`，約第 6–111 行（含文件字串約 106 行）。
- 說明：參數 3 個，巢狀不超過 2，分支是連續檢查，認知複雜度未超過 15，行長未超過 120。長度仍同時超過本次 80 行與專案 50 行。`close_program` 與 `parallel_run` 本體未超。
- 依據：可讀性；從嚴採 `architecture.md` §7 與 `CLAUDE.md` 的函式 ≤ 50 行。
- 狀態：未關閉
- 建議：把標準輸出、標準錯誤的檢查拆成小函式。不必為了行數改動組命令方式。

沒有第 4 則。未發現缺陷。

### 總評

熱點的安全結論是否定句：套件原始碼沒有把工作流程字串交給 shell。執行路徑用 `yaml.safe_load`，檢查路徑用 `yaml.SafeLoader`。`parallel_run` 的命令是 `[執行檔, "-m", 登錄表裡的套件名, "--execute_file", 已解析的腳本路徑]`，套件名不來自 YAML。`open_program` 先 `shlex.split`（Windows 用 `posix=False`），再以 `shell=False` 的參數陣列啟動。舊旗標 `-e`／`--execute_yaml` 與 runner 的 `--execute_file` 都還在，且與 §6 的套件名一致。

因此沒有立即損害。未關閉的只是 CR-01 到 CR-03：邊界上的 `None` argv、啟動失敗的清理，以及一個過長函式。

### 已核對

- YAML：`test_pioneer/executor/pioneer_executor.py` 的 `_load_yaml` 對檔案與字串都呼叫 `yaml.safe_load`。`test_pioneer/validation/yaml_loader.py` 使用 `yaml.SafeLoader`，並拒絕非檔案／字串的 `yaml_type`。搜尋沒有不帶 `SafeLoader` 的 `yaml.load`、沒有 `eval(`、`exec(`、`pickle`、`verify=False`、裸 `except:`、`os.system`。`!!python` 標籤由 safe loader 拒絕；`test/test_yaml_loader.py` 有對應案例。別名展開由索引器的已造訪集合擋住，該測試亦在。
- 子行程：僅兩處 `Popen`。`runner_process._spawn` 預設 `shell=False`（未寫出關鍵字，預設即否），命令是 list，並註明套件名來自登錄表。`ExecuteProcess.start_process` 明示 `shell=False`。腳本路徑先 `Path.resolve()` 再當單一參數，不含殼層元字元解釋。`executor_path` 整段是 argv[0]，不是 `shell=True` 字串。
- 旗標契約：`cli.py` 保留 `-e`／`--execute_yaml`（失敗的步驟仍以 0 結束，除非丟出例外）、`run`、`validate`（含 `-` 與 `--format json`）、`schema`。沒有 `-d`、`-c`、`--execute_str`，`pyproject.toml` 沒有 console script。`__init__.py` 匯出 `create_template_dir`。`ModuleRunner.command` 與 `RUNNERS` 對上 §6：`je_web_runner`、`je_api_testka`、`je_load_density`、`automation_file`、`je_auto_control`。`test/test_parallel_run.py` 鎖定 `automation_file` 的 `--execute_file`。`test/test_cli.py` 鎖定 `-e` 的結束碼。
- 失敗的 `parallel_run` 仍回傳 `True`：未知 runner 與缺檔會 `reject`，結束碼由 `RunnerProcess.close` 寫入執行結果；步驟狀態取較差者，但不停下一個步驟。與 `architecture.md` §4 及 `docs/migration.rst` 一致，測試亦期望 `True`。
- 逾時：`parallel_run` 以 0.1 秒輪詢，沒有上限。schema 與 linter 把 `timeout` 當成未知鍵（`test/test_linter.py`）。這是契約選擇，不是漏接的欄位，不列為缺陷。與 §7「子行程要設逾時」並存，留給後續若要內建上限時再改契約。
- 路徑：`run`／`run_folder`／腳本路徑經 `resolve()`，沒有關在工作目錄內。`open_program` 的目的就是啟動流程所寫的程式。在「操作者自己的流程」這個邊界下，不把 `../` 單列為缺陷。
- 文件：`docs/step-types.rst` 的 `executor_path`、`docs/api-reference.rst` 的 `-e`、`docs/migration.rst` 的 `--execute_file` 與程式一致。`progress.md` 的 #9、#13 仍是倉庫外阻塞，與 §6「已發行 runner 在動作失敗時結束碼為 0」的寫法相符。
- 死碼：`executor/run/process_manager.py` 的 `add_process`、`cleanup_finished`、`terminate_all` 沒有被生產路徑呼叫；`parallel_run` 直接改 `process_list`，中斷時走 `RunnerProcess.cancel`。三個方法仍有單元測試，不算不可達，不單列。

### 未涵蓋

- 未執行 pytest，也未對照兄弟倉庫裡 `--execute_file` 的實際解析。
- 未逐行看 `Dockerfile_*`、`docker_*_test/`、`scripts/dev_release.py`（後者沒有本次搜尋命中）。
- 未用版本庫核對 `architecture.md` 開頭的 “Last verified: 2026-10-08”。
- 未審 HTML 報告、下載 URL 是否含查詢權杖，以及 runner 套件內部如何處理 JSON。

### 本專案加嚴

`architecture.md` §7 與 `CLAUDE.md` 規定函式 ≤ 50 行、檔案 ≤ 750 行、循環複雜度 ≤ 10，嚴於本次函式 80 行。本次從嚴採 50，故 CR-03 成立。認知複雜度 15、巢狀 4、參數 7、行 120 與專案相同。安全條文（禁止 `shell=True`、只許 `safe_load`）與本次第 6 條相同，熱點符合。

### 結論

有條件通過。缺陷 0、建議 3（CR-01、CR-02、CR-03）、備註寫在「已核對」，沒有另開編號。YAML 為安全載入；子行程為參數陣列且未設 `shell=True`；`-e` 與 `--execute_file` 契約仍在。條件是上述三則建議，皆無立即損害。
