import subprocess
import sys
import shutil
from pathlib import Path

from test_pioneer.executor.run.process_manager import process_manager
from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger
from test_pioneer.utils.package.check import is_installed


def parallel_run(step: dict, enable_logging: bool = False) -> bool:
    """
    Run multiple scripts in parallel using different runners.
    使用不同的 runner 平行執行多個腳本。

    Args:
        step (dict): Dictionary containing 'parallel_run' with keys:
                     包含 'parallel_run' 的字典，需包含以下鍵：
                     - runners (list[str]): Runner types 執行器類型
                     - scripts (list[str]): Script paths 腳本路徑
                     - executor_path (str, optional): Python executor path Python 執行器路徑
        enable_logging (bool): Whether to enable logging. 是否啟用日誌紀錄

    Returns:
        bool: True if success, False otherwise.
              成功回傳 True，失敗回傳 False
    """

    parallel_run_dict = step.get("parallel_run")
    if parallel_run_dict is None:
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message="parallel_run tag needs to be defined as an argument"
        )
        return False

    runner_list = parallel_run_dict.get("runners", [])
    script_path_list = parallel_run_dict.get("scripts", [])
    executor_path = parallel_run_dict.get("executor_path")

    # Validate runner/script count
    # 驗證 runner 與 script 數量是否一致
    if len(runner_list) != len(script_path_list):
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message="The number of runners and scripts is not equal"
        )
        return False

    # Define runner command mapping
    # 定義 runner 與對應的模組名稱
    runner_command_dict = {
        "web-runner": "je_web_runner",
        "api-runner": "je_api_testka",
        "load-runner": "je_load_density"
    }

    # Handle gui-runner dependency
    # 處理 gui-runner 依賴
    if "gui-runner" in runner_list and not is_installed("je_auto_control"):
        step_log_check(
            enable_logging=enable_logging,
            logger=test_pioneer_logger,
            level="error",
            message="Please install gui-runner: je_auto_control"
        )
        return False
    if is_installed("je_auto_control"):
        runner_command_dict["gui-runner"] = "je_auto_control"

    # Determine executor path
    # 決定 Python 執行器路徑
    if not executor_path:
        executor_path = sys.executable
    if executor_path == "py.exe" or executor_path is None:
        executor_path = shutil.which("python3") or shutil.which("python")

    # Start processes
    # 啟動多個子程序
    for runner, script in zip(runner_list, script_path_list):
        runner_package = runner_command_dict.get(runner)
        if not runner_package:
            step_log_check(
                enable_logging=enable_logging,
                logger=test_pioneer_logger,
                level="error",
                message=f"Unknown runner type: {runner}"
            )
            continue

        script_path = Path(script).resolve()
        if not script_path.is_file():
            step_log_check(
                enable_logging=enable_logging,
                logger=test_pioneer_logger,
                level="error",
                message=f"Script file does not exist: {script}"
            )
            continue

        # Use list instead of string for subprocess command
        # 使用 list 而非字串來建立 subprocess 命令，避免 shell 解析錯誤
        commands = [
            executor_path,
            "-m", runner_package,
            "--execute_file", str(script_path)
        ]

        try:
            current_process = subprocess.Popen(commands)
            process_manager.process_list.append(current_process)
        except Exception as error:
            step_log_check(
                enable_logging=enable_logging,
                logger=test_pioneer_logger,
                level="error",
                message=f"Failed to start process for {script}: {error}"
            )

    # Monitor processes
    # 監控子程序狀態
    while process_manager.process_list:
        for process in list(process_manager.process_list):  # 使用 list 避免迭代時修改
            process.poll()
            if process.returncode is not None:
                process_manager.process_list.remove(process)

    return True