"""Tests for test_pioneer.artifacts: run IDs, the artifact store and output capture."""
import io
import json
import re
import sys

import pytest

from test_pioneer.artifacts.capture import LogEcho, tee_output
from test_pioneer.artifacts.context import checked_run_id, new_run_id, slug
from test_pioneer.artifacts.store import ArtifactStore, artifact_kind
from test_pioneer.models.result import RunResult
from test_pioneer.utils.exception.exceptions import WrongInputException


class TestRunId:
    def test_new_id_is_a_utc_timestamp_and_a_random_suffix(self):
        assert re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{8}", new_run_id())

    def test_new_ids_differ(self):
        assert len({new_run_id() for _ in range(50)}) == 50

    def test_generated_id_is_accepted(self):
        run_id = new_run_id()
        assert checked_run_id(run_id) == run_id

    @pytest.mark.parametrize("run_id", ["nightly-42", "a", "2026.10.08_build", "A" * 64])
    def test_safe_ids_are_accepted(self, run_id):
        assert checked_run_id(run_id) == run_id

    @pytest.mark.parametrize("run_id", [
        "", "..", "../up", "a/b", "a\\b", "-leading", ".hidden", "trailing.", "has space", "A" * 65, "名稱",
    ])
    def test_ids_that_are_not_a_plain_directory_name_are_refused(self, run_id):
        with pytest.raises(WrongInputException):
            checked_run_id(run_id)


class TestSlug:
    @pytest.mark.parametrize("text, expected", [
        ("run_api_test", "run_api_test"),
        ("test parallel_run", "test_parallel_run"),
        ("../../etc/passwd", "etc_passwd"),
        ("C:\\Windows\\system32", "C_Windows_system32"),
        ("...", "item"),
        ("步驟", "item"),
        ("", "item"),
    ])
    def test_text_becomes_a_safe_name(self, text, expected):
        assert slug(text) == expected

    def test_long_text_is_shortened(self):
        assert len(slug("x" * 500)) == 48

    def test_fallback_is_used_when_nothing_is_left(self):
        assert slug("///", "step") == "step"


class TestArtifactKind:
    @pytest.mark.parametrize("name, kind", [
        ("stdout.log", "log"), ("report.json", "report"), ("junit.XML", "report"), ("index.html", "report"),
        ("shot.PNG", "screenshot"), ("video.mp4", "video"), ("network.har", "trace"), ("data.bin", "other"),
        ("noextension", "other"),
    ])
    def test_kind_follows_the_extension(self, tmp_path, name, kind):
        assert artifact_kind(tmp_path / name) == kind


class TestArtifactStore:
    def test_layout(self, tmp_path):
        store = ArtifactStore(tmp_path / "artifacts", "run-1")
        store.create()
        assert store.run_dir == tmp_path / "artifacts" / "run-1"
        assert store.execution_log == store.run_dir / "testpioneer" / "execution.log"
        assert store.manifest == store.run_dir / "testpioneer" / "manifest.json"
        assert store.engine_dir.is_dir()

    def test_each_runner_execution_gets_its_own_directory(self, tmp_path):
        store = ArtifactStore(tmp_path, "run-1")
        store.create()
        first = store.new_runner_dir("api-runner", "login")
        second = store.new_runner_dir("api-runner", "login")
        third = store.new_runner_dir("web-runner", "../escape")
        assert store.relative(first) == "runners/api-runner/01-login"
        assert store.relative(second) == "runners/api-runner/02-login"
        assert store.relative(third) == "runners/web-runner/03-escape"
        assert first.is_dir() and second.is_dir() and third.is_dir()

    def test_collect_lists_files_with_kind_and_size(self, tmp_path):
        store = ArtifactStore(tmp_path, "run-1")
        store.create()
        directory = store.new_runner_dir("web-runner", "ui")
        (directory / "stdout.log").write_text("hello", encoding="utf-8")
        (directory / "shots").mkdir()
        (directory / "shots" / "fail.png").write_bytes(b"\x89PNG")
        found = [item.to_dict() for item in store.collect(directory)]
        assert found == [
            {"path": "runners/web-runner/01-ui/shots/fail.png", "kind": "screenshot", "size": 4},
            {"path": "runners/web-runner/01-ui/stdout.log", "kind": "log", "size": 5},
        ]

    def test_manifest_is_the_run_result_as_json(self, tmp_path):
        store = ArtifactStore(tmp_path, "run-1")
        store.create()
        store.write_manifest(RunResult(run_id="run-1", workflow="流程.yml"))
        written = json.loads(store.manifest.read_text(encoding="utf-8"))
        assert written["run_id"] == "run-1"
        assert written["workflow"] == "流程.yml"

    def test_remove_deletes_a_runner_directory_and_its_empty_parents(self, tmp_path):
        store = ArtifactStore(tmp_path, "run-1")
        store.create()
        kept = store.new_runner_dir("api-runner", "kept")
        removed = store.new_runner_dir("web-runner", "removed")
        (removed / "stdout.log").write_text("x", encoding="utf-8")
        store.remove(removed)
        assert not (store.run_dir / "runners" / "web-runner").exists()
        assert kept.is_dir()
        assert store.engine_dir.is_dir()

    def test_remove_refuses_a_path_outside_the_run(self, tmp_path):
        store = ArtifactStore(tmp_path / "artifacts", "run-1")
        store.create()
        outside = tmp_path / "precious"
        outside.mkdir()
        with pytest.raises(ValueError, match="not inside the run directory"):
            store.remove(outside)
        with pytest.raises(ValueError, match="not inside the run directory"):
            store.remove(store.run_dir)
        assert outside.is_dir()

    def test_remove_run_also_removes_the_root_it_created(self, tmp_path):
        store = ArtifactStore(tmp_path / "artifacts", "run-1")
        store.create()
        store.remove_run()
        assert not (tmp_path / "artifacts").exists()

    def test_remove_run_removes_every_level_of_a_nested_root_it_created(self, tmp_path):
        (tmp_path / "build").mkdir()
        store = ArtifactStore(tmp_path / "build" / "out" / "runs", "run-1")
        store.create()
        store.remove_run()
        assert (tmp_path / "build").is_dir()
        assert not (tmp_path / "build" / "out").exists()

    def test_remove_run_keeps_a_root_that_was_already_there(self, tmp_path):
        root = tmp_path / "artifacts"
        root.mkdir()
        store = ArtifactStore(root, "run-1")
        store.create()
        store.remove_run()
        assert root.is_dir()
        assert not store.run_dir.exists()

    def test_remove_run_keeps_a_root_that_holds_another_run(self, tmp_path):
        first = ArtifactStore(tmp_path / "artifacts", "run-1")
        first.create()
        second = ArtifactStore(tmp_path / "artifacts", "run-2")
        second.create()
        first.remove_run()
        assert second.run_dir.is_dir()


class TestTeeOutput:
    def test_output_reaches_both_the_console_and_the_logs(self, tmp_path, capsys):
        with tee_output(tmp_path):
            print("to stdout")
            print("to stderr", file=sys.stderr)
        seen = capsys.readouterr()
        assert seen.out == "to stdout\n"
        assert seen.err == "to stderr\n"
        assert (tmp_path / "stdout.log").read_text(encoding="utf-8") == "to stdout\n"
        assert (tmp_path / "stderr.log").read_text(encoding="utf-8") == "to stderr\n"

    def test_streams_are_restored(self, tmp_path):
        before = sys.stdout, sys.stderr
        with tee_output(tmp_path):
            assert sys.stdout is not before[0]
        assert (sys.stdout, sys.stderr) == before

    def test_streams_are_restored_after_an_exception(self, tmp_path):
        before = sys.stdout, sys.stderr
        with pytest.raises(RuntimeError), tee_output(tmp_path):
            print("before the failure")
            raise RuntimeError("boom")
        assert (sys.stdout, sys.stderr) == before
        assert (tmp_path / "stdout.log").read_text(encoding="utf-8") == "before the failure\n"

    def test_a_log_that_received_nothing_is_removed(self, tmp_path):
        with tee_output(tmp_path):
            print("only stdout")
        assert (tmp_path / "stdout.log").is_file()
        assert not (tmp_path / "stderr.log").exists()

    def test_no_directory_means_no_capture(self, capsys):
        before = sys.stdout
        with tee_output(None):
            assert sys.stdout is before
            print("plain")
        assert capsys.readouterr().out == "plain\n"

    def test_a_directory_that_is_gone_does_not_stop_the_call(self, tmp_path, capsys):
        with tee_output(tmp_path / "missing"):
            print("still printed")
        assert capsys.readouterr().out == "still printed\n"

    def test_a_stream_kept_past_the_call_still_writes_to_the_console(self, tmp_path, capsys):
        with tee_output(tmp_path):
            kept = sys.stdout
        kept.write("late\n")
        kept.flush()
        assert capsys.readouterr().out == "late\n"

    def test_other_attributes_come_from_the_original_stream(self, tmp_path):
        with tee_output(tmp_path):
            assert sys.stdout.encoding
            assert sys.stdout.isatty() in (True, False)

    def test_a_lone_surrogate_is_escaped_in_the_log(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "stdout", io.StringIO())
        with tee_output(tmp_path):
            sys.stdout.write("步驟 \udc80\n")
        assert (tmp_path / "stdout.log").read_text(encoding="utf-8") == "步驟 \\udc80\n"


class _BinaryConsole(io.TextIOWrapper):
    """A text stream over an in-memory byte buffer, like a real console stream."""

    def __init__(self) -> None:
        super().__init__(io.BytesIO(), encoding="utf-8")

    def written(self) -> bytes:
        self.flush()
        return self.buffer.getvalue()


class TestLogEcho:
    def test_new_bytes_are_copied_as_they_are_appended(self, tmp_path):
        log = tmp_path / "stdout.log"
        console = _BinaryConsole()
        with log.open("wb") as writer:
            echo = LogEcho(log, console)
            writer.write(b"first\n")
            writer.flush()
            echo.pump()
            assert console.written() == b"first\n"
            writer.write(b"second\n")
            writer.flush()
            echo.pump()
            echo.pump()
            assert console.written() == b"first\nsecond\n"
            echo.close()

    def test_close_copies_what_is_left(self, tmp_path):
        log = tmp_path / "stdout.log"
        log.write_bytes(b"tail")
        console = _BinaryConsole()
        LogEcho(log, console).close()
        assert console.written() == b"tail"

    def test_a_stream_without_a_byte_buffer_gets_text(self, tmp_path):
        log = tmp_path / "stdout.log"
        log.write_bytes(b"plain text\n")
        console = io.StringIO()
        LogEcho(log, console).close()
        assert console.getvalue() == "plain text\n"
