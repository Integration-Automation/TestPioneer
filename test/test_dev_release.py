"""``scripts/dev_release.py`` numbers and gates the ``test_pioneer_dev`` releases CI publishes.

A wrong version is refused by PyPI (a number is never reused) and a wrong comparison either
publishes on every push or never again, so both are pinned here without touching the network.
"""
from __future__ import annotations

import importlib.util
import io
import re
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "dev_release.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
WHEEL_NAME = "test_pioneer_dev-0.1.41-py3-none-any.whl"


def _load_script() -> ModuleType:
    """Import ``scripts/dev_release.py``, which is not part of an importable package."""
    spec = importlib.util.spec_from_file_location("dev_release", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dev_release = _load_script()


def _wheel(version: str, source: str = "VALUE = 1\n", requires: str = "pyyaml") -> bytes:
    """Return a small wheel of ``test_pioneer_dev`` at ``version``."""
    info = f"test_pioneer_dev-{version}.dist-info"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("test_pioneer/__init__.py", source)
        archive.writestr(f"{info}/METADATA",
                         f"Name: test_pioneer_dev\nVersion: {version}\nRequires-Dist: {requires}\n")
        archive.writestr(f"{info}/RECORD", f"test_pioneer/__init__.py,sha256={version}\n")
        archive.writestr(f"{info}/WHEEL", f"Generator: setuptools ({version})\n")
        archive.writestr(f"{info}/licenses/LICENSE", "MIT\n")
    return buffer.getvalue()


@pytest.mark.parametrize("floor, released, expected", [
    ((0, 1, 40), {(0, 1, 40): None, (0, 1, 39): None}, "0.1.41"),
    ((0, 1, 40), {(0, 1, 45): None}, "0.1.46"),
    ((0, 2, 0), {(0, 1, 45): None}, "0.2.1"),
    ((0, 1, 40), {}, "0.1.41"),
])
def test_next_version_is_one_patch_above_the_floor_and_every_release(floor, released, expected):
    """The next version is one patch above the highest of the floor and the releases."""
    assert dev_release.next_version(floor, released) == expected


def test_published_keeps_plain_releases_and_their_wheels(monkeypatch):
    """Only ``X.Y.Z`` releases that have files count, each with its wheel URL if it has one."""
    payload = (
        b'{"releases": {'
        b'"0.1.39": [{"packagetype": "sdist", "url": "https://files.pythonhosted.org/a.tar.gz"}],'
        b'"0.1.40": [{"packagetype": "sdist", "url": "https://files.pythonhosted.org/b.tar.gz"},'
        b' {"packagetype": "bdist_wheel", "url": "https://files.pythonhosted.org/b.whl"}],'
        b'"0.1.41.dev1": [{"packagetype": "bdist_wheel", "url": "https://files.pythonhosted.org/c.whl"}],'
        b'"0.1.38": []}}'
    )
    monkeypatch.setattr(dev_release, "fetch", lambda url: payload)
    assert dev_release.published("test_pioneer_dev") == {
        (0, 1, 39): None,
        (0, 1, 40): "https://files.pythonhosted.org/b.whl",
    }


def test_fetch_refuses_a_host_that_is_not_pypi():
    """A URL outside PyPI's two hosts is refused before any request is made."""
    with pytest.raises(ValueError):
        dev_release.fetch("https://example.com/test_pioneer_dev.whl")


def test_prepare_writes_pyproject_from_dev_toml_with_the_next_version(tmp_path, monkeypatch):
    """``prepare`` copies ``dev.toml`` to ``pyproject.toml`` and changes only the version."""
    dev_toml = (REPO_ROOT / "dev.toml").read_text(encoding="utf-8")
    (tmp_path / "dev.toml").write_text(dev_toml, encoding="utf-8")
    asked = []
    monkeypatch.setattr(dev_release, "published", lambda name: asked.append(name) or {(9, 9, 9): None})

    assert dev_release.prepare(tmp_path) == "9.9.10"

    written = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert asked == ["test_pioneer_dev"]
    assert written == dev_release.VERSION_LINE.sub(r'\g<1>"9.9.10"', dev_toml, count=1)
    assert written.count('version = "9.9.10"') == 1


def test_fingerprint_ignores_what_only_the_version_number_changes():
    """Two builds of the same sources at different versions have the same fingerprint."""
    assert dev_release.fingerprint(_wheel("0.1.40")) == dev_release.fingerprint(_wheel("0.1.41"))


@pytest.mark.parametrize("difference", [{"source": "VALUE = 2\n"}, {"requires": "pyyaml>=6"}])
def test_fingerprint_sees_changed_code_and_changed_metadata(difference):
    """A changed module or a changed dependency gives a different fingerprint."""
    assert dev_release.fingerprint(_wheel("0.1.40")) != dev_release.fingerprint(
        _wheel("0.1.41", **difference))


@pytest.mark.parametrize("latest, expected", [
    ({}, True),
    ({"source": "VALUE = 0\n"}, True),
    ({"source": "VALUE = 1\n"}, False),
])
def test_changed_compares_the_built_wheel_with_the_newest_published_one(
        tmp_path, monkeypatch, latest, expected):
    """``changed`` is true with no release or a different newest wheel, false for the same one."""
    (tmp_path / WHEEL_NAME).write_bytes(_wheel("0.1.41"))
    url = "https://files.pythonhosted.org/test_pioneer_dev-0.1.40-py3-none-any.whl"
    released = {(0, 1, 39): "https://files.pythonhosted.org/old.whl", (0, 1, 40): url} if latest else {}
    monkeypatch.setattr(dev_release, "published", lambda name: released)
    monkeypatch.setattr(dev_release, "fetch", lambda asked: _wheel("0.1.40", **latest) if asked == url else b"")

    assert dev_release.changed(tmp_path) is expected


def test_changed_publishes_when_the_newest_release_has_no_wheel(tmp_path, monkeypatch):
    """A newest release without a wheel cannot be compared, so the build is published."""
    (tmp_path / WHEEL_NAME).write_bytes(_wheel("0.1.41"))
    monkeypatch.setattr(dev_release, "published", lambda name: {(0, 1, 40): None})

    assert dev_release.changed(tmp_path) is True


def test_main_writes_the_result_where_the_workflow_reads_it(tmp_path, monkeypatch):
    """``changed`` appends its result to ``$GITHUB_OUTPUT``; an unknown command exits 2."""
    output = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(dev_release, "changed", lambda dist: False)

    assert dev_release.main(["changed", str(tmp_path)]) == 0
    assert output.read_text(encoding="utf-8") == "changed=false\n"
    assert dev_release.main(["publish"]) == 2


def _publish_job() -> str:
    """Return the text of the ``publish-dev`` job, the last job of the workflow."""
    text = WORKFLOW.read_text(encoding="utf-8")
    return re.split(r"^  publish-dev:\s*$", text, maxsplit=1, flags=re.MULTILINE)[1]


def test_the_workflow_publishes_only_a_tested_push_to_dev():
    """The job waits for both test jobs and runs only for a push to ``dev``, never ``main``."""
    job = _publish_job()
    assert "needs: [unit-test, integration-test]" in job
    assert "if: github.event_name == 'push' && github.ref == 'refs/heads/dev'" in job


def test_the_workflow_uploads_only_a_changed_build_and_keeps_no_credentials():
    """The upload comes last, behind the comparison and the tip check, without checkout credentials."""
    job = _publish_job()
    upload = job.index("twine upload")
    assert job.index("dev_release.py prepare") < job.index("python -m build") < upload
    assert job.index("dev_release.py changed dist") < upload
    assert job.index("git ls-remote origin refs/heads/dev") < upload
    assert "if: steps.compare.outputs.changed == 'true' && steps.tip.outputs.current == 'true'" in job
    assert "persist-credentials: false" in job
