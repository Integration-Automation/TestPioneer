"""The README's complete example stays valid, and the three READMEs stay in step.

The example is extracted from each README exactly as a reader would copy it. Nothing is executed
here: the scripts must be JSON and the workflow must pass ``validate`` with its scripts in place.
"""
import json
import re
from pathlib import Path

import pytest

from test_pioneer import lint_yaml
from test_pioneer.validation import LintOptions

REPO_ROOT = Path(__file__).resolve().parents[1]
READMES = ("README.md", "README/README_zh-TW.md", "README/README_zh-CN.md")
EXAMPLE_FILES = ["tests/api_smoke.json", "tests/api_pages.json", "tests/load_home.json", "tests/test.yaml"]
# A line that is only a back-quoted tests/ path, a blank line, then a fenced block.
_FILE_BLOCK = re.compile(r"^`(tests/[\w.]+)`[^\n]*\n\n```\w+\n(.*?)^```", re.MULTILINE | re.DOTALL)
_HEADING = re.compile(r"^(#{2,3}) ", re.MULTILINE)
_FENCE = re.compile(r"^```(\w*)$", re.MULTILINE)


def _text(readme: str) -> str:
    return (REPO_ROOT / readme).read_text(encoding="utf-8")


def _example(readme: str) -> dict:
    """Return the example's files, by path, as the README shows them."""
    return dict(_FILE_BLOCK.findall(_text(readme)))


@pytest.mark.parametrize("readme", READMES)
def test_the_example_has_every_file(readme):
    assert list(_example(readme)) == EXAMPLE_FILES


@pytest.mark.parametrize("readme", READMES[1:])
def test_the_translations_show_the_same_example(readme):
    assert _example(readme) == _example(READMES[0])


def test_each_runner_script_is_a_json_action_list_that_ends_with_its_report():
    scripts = [json.loads(body) for name, body in _example(READMES[0]).items() if name.endswith(".json")]
    assert [actions[-1][0] for actions in scripts] == [
        "AT_generate_json_report", "AT_generate_json_report", "LD_generate_json_report"]


def test_the_workflow_passes_validation_with_its_scripts_in_place(tmp_path, monkeypatch):
    monkeypatch.setattr("test_pioneer.validation.linter.is_installed", lambda package: True)
    for name, body in _example(READMES[0]).items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    result = lint_yaml(str(tmp_path / "tests" / "test.yaml"), options=LintOptions(base_dir=tmp_path))
    assert result.diagnostics == ()


@pytest.mark.parametrize("readme", READMES[1:])
def test_the_translations_have_the_same_structure(readme):
    english, translated = _text(READMES[0]), _text(readme)
    assert _HEADING.findall(translated) == _HEADING.findall(english)
    assert _FENCE.findall(translated) == _FENCE.findall(english)
