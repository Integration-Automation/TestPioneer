"""Engine-facing validation API: check a workflow and get structured diagnostics back.

A UI or a CI job calls these instead of executing the workflow and reading its log.
"""
from __future__ import annotations

from test_pioneer.models.diagnostic import ValidationResult
from test_pioneer.validation.linter import LintOptions, run_lint_rules
from test_pioneer.validation.schema_validator import check_schema
from test_pioneer.validation.yaml_loader import YamlDocument, load_yaml


def check_document(document: YamlDocument, options: LintOptions | None = None,
                   semantic: bool = True) -> ValidationResult:
    """Check an already parsed workflow: schema first, then the lint rules when ``semantic``."""
    found = list(document.diagnostics)
    if document.parsed:
        found += check_schema(document)
        if semantic:
            found += run_lint_rules(document, options)
    found.sort(key=lambda item: (item.line or 0, item.column or 0))
    return ValidationResult(tuple(found), document.source)


def validate_yaml(stream: str, yaml_type: str = "File") -> ValidationResult:
    """Check a workflow's YAML syntax and its structure against the JSON Schema.

    Nothing is executed. ``stream`` and ``yaml_type`` mean the same as in ``execute_yaml``.
    """
    return check_document(load_yaml(stream, yaml_type), semantic=False)


def lint_yaml(stream: str, yaml_type: str = "File", options: LintOptions | None = None) -> ValidationResult:
    """Run ``validate_yaml`` and then the semantic rules a JSON Schema cannot express.

    The rules cover duplicate step names, missing or conflicting actions, fields an action needs,
    ``runners``/``scripts`` length, unknown keys, runner packages and referenced files.
    """
    return check_document(load_yaml(stream, yaml_type), options)
