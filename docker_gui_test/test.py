import os
from pyvirtualdisplay import Display
from test_pioneer import execute_yaml


def list_all_files(base_path):
    """
    Recursively list all file paths under base_path using os.walk.
    """
    file_paths = []
    for root, dirs, files in os.walk(base_path):
        for filename in files:
            # Join root directory with filename
            full_path = os.path.join(root, filename)
            file_paths.append(full_path)
    return file_paths


if __name__ == '__main__':

    for path in list_all_files("./docker_gui_test"):
        print(path)

    # Start Xvfb on an unused display and export DISPLAY
    display = Display(visible=0, size=(1920, 1080))
    display.start()

    execute_yaml("./docker_gui_test/test_run_multi_time.yml")
