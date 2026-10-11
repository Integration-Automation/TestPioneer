"""Parse workflow YAML and remember where every key and value sits in the text.

The positions let a diagnostic name a line and column, which the executor's own loader
(``yaml.safe_load``) throws away.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from test_pioneer.models.diagnostic import Diagnostic, Severity, YamlPath
from test_pioneer.utils.exception.exceptions import WrongInputException

Position = tuple[int, int]


def _position(mark: yaml.Mark) -> Position:
    """Turn a 0-based PyYAML mark into a 1-based line and column."""
    return mark.line + 1, mark.column + 1


class PositionIndex:
    """Line and column of each key and each value, addressed by YAML path."""

    def __init__(self) -> None:
        self._keys: dict[YamlPath, Position] = {}
        self._values: dict[YamlPath, Position] = {}

    def add_key(self, path: YamlPath, mark: yaml.Mark) -> None:
        """Record where the key that ends ``path`` starts."""
        self._keys[path] = _position(mark)

    def add_value(self, path: YamlPath, mark: yaml.Mark) -> None:
        """Record where the value at ``path`` starts."""
        self._values[path] = _position(mark)

    def locate(self, path: YamlPath, on_key: bool = False) -> Position | None:
        """Return the position of ``path``, or of its nearest recorded ancestor.

        ``on_key`` points at the key instead of the value. An ancestor is always reported by its
        key, so a missing entry is shown on the line that should contain it.
        """
        tables = (self._keys, self._values) if on_key else (self._values, self._keys)
        current = path
        while True:
            for table in tables:
                if current in table:
                    return table[current]
            if not current:
                return None
            current = current[:-1]
            tables = (self._keys, self._values)


@dataclass(frozen=True)
class YamlDocument:
    """A parsed workflow: its data, the position of each node, and any syntax problems."""

    data: object = None
    positions: PositionIndex = field(default_factory=PositionIndex)
    diagnostics: tuple[Diagnostic, ...] = ()
    source: str | None = None
    # False when the text could not be read or parsed, so there is no data to check.
    parsed: bool = True

    def position(self, path: YamlPath, on_key: bool = False) -> tuple[int | None, int | None]:
        """Return the line and column a diagnostic about ``path`` points at, or two ``None``."""
        return self.positions.locate(path, on_key) or (None, None)


class _Indexer:  # pylint: disable=too-few-public-methods  # one entry point over shared state
    """Walks the composed node tree once, filling the position index."""

    def __init__(self, positions: PositionIndex) -> None:
        self._positions = positions
        self._visited: set[int] = set()
        self.problems: list[Diagnostic] = []

    def visit(self, node: yaml.Node, path: YamlPath) -> None:
        """Record ``node`` at ``path`` and descend into it the first time it is met."""
        self._positions.add_value(path, node.start_mark)
        # An aliased node is reachable by many paths; walking each one again would let a small
        # file of nested aliases expand without bound.
        if id(node) in self._visited:
            return
        self._visited.add(id(node))
        if isinstance(node, yaml.MappingNode):
            self._visit_mapping(node, path)
        elif isinstance(node, yaml.SequenceNode):
            for index, item in enumerate(node.value):
                self.visit(item, path + (index,))

    def _visit_mapping(self, node: yaml.MappingNode, path: YamlPath) -> None:
        seen: set[str] = set()
        for key_node, value_node in node.value:
            if not isinstance(key_node, yaml.ScalarNode):
                continue
            key = str(key_node.value)
            child = path + (key,)
            if key in seen:
                line, column = _position(key_node.start_mark)
                self.problems.append(Diagnostic(
                    Severity.ERROR, "duplicate-key",
                    f"key '{key}' appears more than once in this mapping; only the last one is used",
                    child, line, column, "yaml"))
            seen.add(key)
            self._positions.add_key(child, key_node.start_mark)
            self.visit(value_node, child)


def _syntax_problem(error: Exception) -> Diagnostic:
    """Describe a parse failure, located when PyYAML says where it happened."""
    mark = getattr(error, "problem_mark", None) or getattr(error, "context_mark", None)
    parts = (getattr(error, "context", None), getattr(error, "problem", None))
    message = ", ".join(part for part in parts if part) or str(error) or type(error).__name__
    line, column = _position(mark) if isinstance(mark, yaml.Mark) else (None, None)
    return Diagnostic(Severity.ERROR, "yaml-syntax", message, (), line, column, "yaml")


def _parse(text: str, source: str | None) -> YamlDocument:
    """Parse YAML text with the safe loader and index the position of every node."""
    positions = PositionIndex()
    indexer = _Indexer(positions)
    loader = yaml.SafeLoader(text)
    try:
        node = loader.get_single_node()
        data = None if node is None else loader.construct_document(node)
        # Indexed after construction, which expands ``<<`` merge keys in place.
        if node is not None:
            indexer.visit(node, ())
    except (yaml.YAMLError, ValueError, RecursionError) as error:
        # ValueError: a malformed timestamp scalar. RecursionError: nesting deeper than the stack.
        return YamlDocument(diagnostics=(_syntax_problem(error),), source=source, parsed=False)
    finally:
        loader.dispose()
    return YamlDocument(data, positions, tuple(indexer.problems), source)


def _read(path: str) -> YamlDocument:
    """Read and parse a workflow file; an unreadable file becomes a diagnostic."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        problem = Diagnostic(Severity.ERROR, "yaml-unreadable",
                             f"cannot read the workflow file: {error}", source="yaml")
        return YamlDocument(diagnostics=(problem,), source=path, parsed=False)
    return _parse(text, path)


def load_yaml(stream: str, yaml_type: str = "File") -> YamlDocument:
    """Parse a workflow without executing it.

    ``stream`` is a file path when ``yaml_type`` is ``"File"`` and YAML text when it is
    ``"String"``, as in ``execute_yaml``. Syntax problems are returned in
    ``YamlDocument.diagnostics`` instead of being raised.
    """
    if yaml_type == "File":
        return _read(stream)
    if yaml_type == "String":
        return _parse(stream, None)
    raise WrongInputException(f"Wrong input: yaml_type must be 'File' or 'String', got {yaml_type!r}")
