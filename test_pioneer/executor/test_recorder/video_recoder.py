from je_auto_control import RecordingThread
from test_pioneer.utils.exception.exceptions import ExecutorException


def set_recorder(yaml_data: dict) -> tuple[bool, RecordingThread] | tuple[bool, None]:
    """
    Set up a recording thread if 'recording_path' is provided in yaml_data.
    如果 yaml_data 中提供了 'recording_path'，則建立並啟動錄影執行緒。

    Args:
        yaml_data (dict): Dictionary containing 'recording_path' key.
                          包含 'recording_path' 鍵的字典。

    Returns:
        tuple[bool, RecordingThread] | tuple[bool, None]:
            - (True, RecordingThread) if recording is started.
              若成功啟動錄影，回傳 (True, RecordingThread)。
            - (False, None) if no recording is started.
              若未啟動錄影，回傳 (False, None)。
    """

    # Pre-check recording_path
    # 檢查是否有 recording_path
    recording_path = yaml_data.get("recording_path")
    if recording_path is None:
        return False, None

    # Validate type
    # 驗證 recording_path 型別
    if not isinstance(recording_path, str):
        raise ExecutorException(f"recording_path must be str, got: {recording_path}")

    # Patch threading with gevent
    # 使用 gevent 替換 threading
    import sys
    if "threading" in sys.modules:
        del sys.modules["threading"]
    from gevent.monkey import patch_thread
    patch_thread()

    # Initialize recording thread
    # 初始化錄影執行緒
    recorder = RecordingThread()
    recorder.video_name = recording_path
    recorder.daemon = True
    recorder.start()

    return True, recorder