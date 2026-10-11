"""Run the download_file sample workflow and exit with status 1 when it does not pass."""
import sys
from pathlib import Path

from test_pioneer import execute_yaml

if __name__ == '__main__':
    result = execute_yaml("./test/unit_test/download_file/download_file.yml")
    print(f"{result.run_id}: {result.status.value} {result.summary()}")
    passed = result.status.value == "passed" and "MIT License" in Path("test/unit_test/output/downloaded_LICENSE").read_text(encoding="utf-8")
    sys.exit(0 if passed else 1)
