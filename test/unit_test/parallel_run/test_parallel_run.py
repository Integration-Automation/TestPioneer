"""Run the parallel_run sample workflow and exit with status 1 when it does not pass."""
import sys

from test_pioneer import execute_yaml

if __name__ == '__main__':
    result = execute_yaml("./test/unit_test/parallel_run/test_parallel_run.yml")
    print(f"{result.run_id}: {result.status.value} {result.summary()}")
    passed = result.status.value == "passed"
    sys.exit(0 if passed else 1)
