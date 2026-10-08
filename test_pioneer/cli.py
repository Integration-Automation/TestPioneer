"""Command line of ``python -m test_pioneer``.

``-e/--execute_yaml`` executes a workflow. ``validate`` checks workflow files without executing
them and ``schema`` prints the workflow JSON Schema.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from test_pioneer.executor.pioneer_executor import execute_yaml
from test_pioneer.models.diagnostic import Diagnostic, ValidationResult, format_path
from test_pioneer.schema import SCHEMA_VERSION, get_yaml_schema
from test_pioneer.utils.exception.exceptions import ExecutorException
from test_pioneer.validation import LintOptions, lint_yaml

EXIT_OK = 0
EXIT_INVALID = 1


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser of ``python -m test_pioneer``."""
    parser = argparse.ArgumentParser(
        prog="python -m test_pioneer",
        description="TestPioneer - Automation test framework for CI/CD",
    )
    parser.add_argument("-e", "--execute_yaml", type=str, help="choose yaml file to execute")
    commands = parser.add_subparsers(dest="command", metavar="{validate,schema}")

    validate = commands.add_parser(
        "validate", help="check workflow files without executing them",
        description="Check workflow files against the schema and the lint rules. Exits 1 on an error.",
    )
    validate.add_argument("files", nargs="+", help="workflow YAML files to check")
    validate.add_argument("--format", choices=("text", "json"), default="text", help="output format")
    validate.add_argument("--strict", action="store_true", help="treat warnings as errors")
    validate.add_argument("--base_dir", help="directory that script paths in the workflow are relative to "
                                             "(default: the current directory)")
    validate.add_argument("--no_file_check", action="store_true",
                          help="do not check that the referenced scripts and folders exist")

    schema = commands.add_parser("schema", help="print the workflow JSON Schema")
    schema.add_argument("-o", "--output", help="write the schema to this file instead of standard output")
    return parser


def _format_line(source: str, item: Diagnostic) -> str:
    """Render one diagnostic as ``file:line:column: severity: path: message [code]``."""
    place = source if item.line is None else f"{source}:{item.line}:{item.column}"
    return f"{place}: {item.severity.value}: {format_path(item.path)}: {item.message} [{item.code}]"


def _print_text(results: Sequence[ValidationResult]) -> None:
    errors = warnings = 0
    for result in results:
        errors += len(result.errors)
        warnings += len(result.warnings)
        for item in result.diagnostics:
            print(_format_line(result.source or "<string>", item))
    print(f"Checked {len(results)} file(s): {errors} error(s), {warnings} warning(s)")


def _print_json(results: Sequence[ValidationResult], passed: bool) -> None:
    report = {
        "schema_version": SCHEMA_VERSION,
        "ok": passed,
        "files": [result.to_dict() for result in results],
    }
    print(json.dumps(report, indent=2))


def _validate(args: argparse.Namespace) -> int:
    options = LintOptions(
        base_dir=Path(args.base_dir) if args.base_dir else None,
        check_files=not args.no_file_check,
    )
    results = [lint_yaml(path, options=options) for path in args.files]
    passed = all(result.ok and not (args.strict and result.warnings) for result in results)
    if args.format == "json":
        _print_json(results, passed)
    else:
        _print_text(results)
    return EXIT_OK if passed else EXIT_INVALID


def _schema(args: argparse.Namespace) -> int:
    text = json.dumps(get_yaml_schema(), indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)
    return EXIT_OK


def _keep_output_printable() -> None:
    """Escape characters the console encoding lacks instead of failing on them."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(errors="backslashreplace")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return the process exit code."""
    args = build_parser().parse_args(argv)
    _keep_output_printable()
    if args.command == "validate":
        return _validate(args)
    if args.command == "schema":
        return _schema(args)
    if args.execute_yaml:
        execute_yaml(args.execute_yaml)
        return EXIT_OK
    raise ExecutorException(
        "execute_yaml have no argument, usage: python -m test_pioneer -e <filepath>")
