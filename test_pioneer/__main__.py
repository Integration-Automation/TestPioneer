import argparse

from test_pioneer import execute_yaml
from test_pioneer.exception.exceptions import ExecutorException

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

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
            f"execute_yaml have no argument right way to use: python -m test_pioneer. -e filepath or -e string")