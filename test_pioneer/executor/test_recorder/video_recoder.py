from je_auto_control import RecordingThread

from test_pioneer.exception.exceptions import ExecutorException


def set_recoder(yaml_data: dict) -> tuple[bool, RecordingThread] or None:
    # Pre-check recoding or no
    if "recording_path" in yaml_data.keys():
        if isinstance(yaml_data.get("recording_path"), str) is False:
            raise ExecutorException(f"recording_path not a str: {yaml_data.get('recording_path')}")
        import sys
        if 'threading' in sys.modules:
            del sys.modules['threading']
        from gevent.monkey import patch_thread
        patch_thread()
        recording = True
        recoder = RecordingThread()
        recoder.video_name = yaml_data.get("recording_path")
        recoder.daemon = True
        recoder.start()
        return recording, recoder
    else:
        return False, None
