"""Run the run_folder sample workflow and exit with status 1 when it does not pass."""
import sys
from pathlib import Path

from test_pioneer import execute_yaml

if __name__ == '__main__':
    result = execute_yaml("./test/unit_test/run_folder/test_run_folder.yml")
    print(f"{result.run_id}: {result.status.value} {result.summary()}")
    passed = result.status.value == "passed" and Path("test/unit_test/output/run_folder/copied.txt").is_file()
    sys.exit(0 if passed else 1)
