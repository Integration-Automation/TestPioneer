"""Tests for test_pioneer.validation.yaml_loader"""
import pytest

from test_pioneer.utils.exception.exceptions import WrongInputException
from test_pioneer.validation.yaml_loader import load_yaml

WORKFLOW = """\
pioneer_log: run.log
jobs:
  steps:
    - name: first
      wait: 1
    - name: second
      run: a.json
      with: api-runner
"""


class TestLoading:
    def test_string_is_parsed_into_data(self):
        document = load_yaml(WORKFLOW, "String")
        assert document.parsed is True
        assert document.diagnostics == ()
        assert document.source is None
        assert document.data["jobs"]["steps"][1]["with"] == "api-runner"

    def test_file_is_parsed_and_keeps_its_source(self, tmp_path):
        path = tmp_path / "flow.yml"
        path.write_text(WORKFLOW, encoding="utf-8")
        document = load_yaml(str(path))
        assert document.source == str(path)
        assert document.data["pioneer_log"] == "run.log"

    def test_non_ascii_file_is_read_as_utf8(self, tmp_path):
        path = tmp_path / "flow.yml"
        path.write_text("jobs:\n  steps:\n    - name: 測試步驟\n      wait: 1\n", encoding="utf-8")
        assert load_yaml(str(path)).data["jobs"]["steps"][0]["name"] == "測試步驟"

    def test_empty_text_parses_to_none(self):
        document = load_yaml("", "String")
        assert document.parsed is True
        assert document.data is None

    def test_unknown_yaml_type_raises(self):
        with pytest.raises(WrongInputException):
            load_yaml(WORKFLOW, "Stream")


class TestPositions:
    def test_key_and_value_positions_are_one_based(self):
        positions = load_yaml(WORKFLOW, "String").positions
        assert positions.locate(("pioneer_log",), on_key=True) == (1, 1)
        assert positions.locate(("pioneer_log",)) == (1, 14)
        assert positions.locate(("jobs", "steps", 1, "with"), on_key=True) == (8, 7)
        assert positions.locate(("jobs", "steps", 1, "with")) == (8, 13)

    def test_list_item_is_located_at_its_first_key(self):
        positions = load_yaml(WORKFLOW, "String").positions
        assert positions.locate(("jobs", "steps", 0)) == (4, 7)

    def test_missing_path_falls_back_to_its_parent(self):
        positions = load_yaml(WORKFLOW, "String").positions
        assert positions.locate(("jobs", "nothing")) == (2, 1)
        assert positions.locate(("jobs", "steps", 0, "nothing")) == (4, 7)

    def test_nothing_is_located_in_an_empty_document(self):
        assert load_yaml("", "String").positions.locate(("jobs",)) is None


class TestProblems:
    def test_syntax_error_becomes_a_located_diagnostic(self):
        document = load_yaml("jobs:\n  steps: [1, 2\n", "String")
        assert document.parsed is False
        assert document.data is None
        (problem,) = document.diagnostics
        assert problem.code == "yaml-syntax"
        assert problem.source == "yaml"
        assert problem.line is not None

    def test_several_documents_are_a_syntax_error(self):
        document = load_yaml("jobs: {}\n---\njobs: {}\n", "String")
        assert [item.code for item in document.diagnostics] == ["yaml-syntax"]

    def test_python_object_tag_is_refused(self):
        document = load_yaml("jobs: !!python/object/apply:os.getcwd []\n", "String")
        assert document.parsed is False
        assert document.diagnostics[0].code == "yaml-syntax"

    def test_missing_file_becomes_a_diagnostic(self, tmp_path):
        document = load_yaml(str(tmp_path / "absent.yml"))
        assert document.parsed is False
        assert [item.code for item in document.diagnostics] == ["yaml-unreadable"]

    def test_file_that_is_not_utf8_becomes_a_diagnostic(self, tmp_path):
        path = tmp_path / "flow.yml"
        path.write_bytes(b"jobs: \xff\xfe\n")
        assert [item.code for item in load_yaml(str(path)).diagnostics] == ["yaml-unreadable"]

    def test_duplicate_key_is_reported_where_it_repeats(self):
        document = load_yaml("jobs:\n  steps: []\njobs:\n  steps: [1]\n", "String")
        assert document.parsed is True
        assert document.data == {"jobs": {"steps": [1]}}
        (problem,) = document.diagnostics
        assert (problem.code, problem.line, problem.column) == ("duplicate-key", 3, 1)
        assert problem.path == ("jobs",)


class TestAliases:
    def test_merge_key_fields_are_part_of_the_step(self):
        text = (
            "defaults: &api\n  with: api-runner\n"
            "jobs:\n  steps:\n    - name: a\n      run: a.json\n      <<: *api\n"
        )
        document = load_yaml(text, "String")
        assert document.data["jobs"]["steps"][0]["with"] == "api-runner"
        assert document.positions.locate(("jobs", "steps", 0, "with")) == (2, 9)

    def test_nested_aliases_do_not_expand_without_bound(self):
        lines = ["a0: &a0 [x, x]"]
        for level in range(1, 40):
            lines.append(f"a{level}: &a{level} [*a{level - 1}, *a{level - 1}]")
        document = load_yaml("\n".join(lines) + "\n", "String")
        assert document.parsed is True
        assert document.positions.locate(("a39",), on_key=True) == (40, 1)
