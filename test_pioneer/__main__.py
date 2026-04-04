import argparse

from test_pioneer import execute_yaml
from test_pioneer.utils.exception.exceptions import ExecutorException

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TestPioneer - Automation test framework for CI/CD"
    )

    parser.add_argument(
        "-e", "--execute_yaml",
        type=str, help="choose yaml file to execute"
    )
    args = parser.parse_args()
    args = vars(args)
    if args.get("execute_yaml"):
        execute_yaml(args.get("execute_yaml"))
    else:
        raise ExecutorException(
            "execute_yaml have no argument, usage: python -m test_pioneer -e <filepath>")
