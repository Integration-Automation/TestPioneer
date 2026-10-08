"""Render a run result as one self-contained HTML page.

The page has no script and loads nothing. Every value that comes from a workflow or a runner is
escaped, and the only links are relative paths to the run's own artifact files.
"""
from __future__ import annotations

import html
import os
from pathlib import Path
from urllib.parse import quote

from test_pioneer.models.result import CaseResult, RunnerResult, RunResult, Status, StepResult

# Shown before the rest of a runner's tests is folded away.
_VISIBLE_PASSED = 20

_STYLE = """
:root { color-scheme: light dark; --bg: #fff; --fg: #1b1f24; --muted: #5c6670; --line: #d8dee4;
  --card: #f6f8fa; --passed: #1a7f37; --failed: #cf222e; --error: #9a6700; --cancelled: #6e7781; }
@media (prefers-color-scheme: dark) { :root { --bg: #0d1117; --fg: #e6edf3; --muted: #9198a1;
  --line: #30363d; --card: #161b22; --passed: #3fb950; --failed: #f85149; --error: #d29922;
  --cancelled: #8b949e; } }
body { margin: 0 auto; max-width: 72rem; padding: 1.5rem 1rem 3rem; background: var(--bg);
  color: var(--fg); font: 15px/1.5 system-ui, "Segoe UI", sans-serif; }
h1 { font-size: 1.5rem; margin: 0 0 .25rem; } h2 { font-size: 1.15rem; margin: 2rem 0 .5rem; }
h3 { font-size: 1rem; margin: 0; overflow-wrap: anywhere; }
.meta, .muted { color: var(--muted); } .meta span { margin-right: 1.25rem; white-space: nowrap; }
.tiles { display: flex; flex-wrap: wrap; gap: .75rem; margin: 1rem 0; }
.tile { background: var(--card); border: 1px solid var(--line); border-radius: 8px;
  padding: .6rem .9rem; min-width: 8rem; }
.tile b { display: block; font-size: 1.4rem; }
.badge { display: inline-block; border-radius: 999px; padding: 0 .6rem; font-size: .8rem;
  font-weight: 600; color: #fff; text-transform: uppercase; }
.passed { background: var(--passed); } .failed { background: var(--failed); }
.error { background: var(--error); } .cancelled { background: var(--cancelled); }
.scroll { overflow-x: auto; } table { border-collapse: collapse; width: 100%; }
th, td { border-bottom: 1px solid var(--line); padding: .35rem .6rem; text-align: left;
  vertical-align: top; }
th { color: var(--muted); font-weight: 600; } td.num { text-align: right; white-space: nowrap; }
td.msg, .msg { overflow-wrap: anywhere; white-space: pre-wrap; font-family: ui-monospace, Consolas, monospace;
  font-size: .85rem; }
.runner { border: 1px solid var(--line); border-radius: 8px; margin: .75rem 0; padding: .75rem .9rem; }
.runner header { display: flex; flex-wrap: wrap; gap: .5rem 1rem; align-items: baseline; }
ul.files { margin: .4rem 0 0; padding-left: 1.2rem; } a { color: inherit; }
details { margin-top: .5rem; } summary { cursor: pointer; color: var(--muted); }
.warn { border-left: 4px solid var(--error); background: var(--card); padding: .5rem .9rem; }
"""


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _badge(status: Status) -> str:
    return f'<span class="badge {status.value}">{status.value}</span>'


def _duration(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.1f} s" if milliseconds >= 1000 else f"{milliseconds} ms"


def _tile(label: str, counts: dict[str, int]) -> str:
    parts = [f"{counts[status.value]} {status.value}" for status in Status if counts[status.value]]
    return (f'<div class="tile"><span class="muted">{_esc(label)}</span><b>{counts["total"]}</b>'
            f'{_esc(", ".join(parts) or "none")}</div>')


class _Page:  # pylint: disable=too-few-public-methods  # one entry point over shared state
    """Builds the page for one result; links are made relative to where the page is written."""

    def __init__(self, result: RunResult, directory: Path) -> None:
        self._result = result
        self._directory = directory

    def render(self) -> str:
        """Return the whole HTML document."""
        result = self._result
        body = [
            f"<h1>TestPioneer report {_badge(result.status)}</h1>",
            (f'<p class="meta"><span>Run <b>{_esc(result.run_id)}</b></span>'
             f"<span>Workflow: {_esc(result.workflow or 'inline YAML')}</span>"
             f"<span>Started: {_esc(result.started_at)}</span>"
             f"<span>Duration: {_duration(result.duration_ms)}</span></p>"),
        ]
        if result.message:
            body.append(f'<p class="warn msg">{_esc(result.message)}</p>')
        body.append('<div class="tiles">' + _tile("Runner executions", result.summary())
                    + _tile("Recorded tests", result.case_summary()) + "</div>")
        body += [f'<p class="warn">Warning: {_esc(warning)}</p>' for warning in result.warnings]
        body += self._steps(result.steps)
        body.append("<h2>Runner executions</h2>")
        body += [self._runner(runner) for runner in result.runners] or ['<p class="muted">None.</p>']
        return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
                f"<title>TestPioneer report {_esc(result.run_id)}</title>\n<style>{_STYLE}</style>\n</head>\n"
                "<body>\n" + "\n".join(body) + "\n</body>\n</html>\n")

    def _steps(self, steps: list[StepResult]) -> list[str]:
        rows = [
            f"<tr><td class=\"num\">{index}</td><td>{_esc(step.name)}</td><td>{_esc(step.action)}</td>"
            f"<td>{_badge(step.status)}</td><td class=\"num\">{_duration(step.duration_ms)}</td>"
            f"<td class=\"msg\">{_esc(step.message or '')}</td></tr>"
            for index, step in enumerate(steps, start=1)
        ]
        return ["<h2>Steps</h2>", '<div class="scroll"><table>',
                "<tr><th>#</th><th>Step</th><th>Action</th><th>Status</th><th>Duration</th><th>Message</th></tr>",
                *rows, "</table></div>"]

    def _href(self, relative: str) -> str | None:
        """Link to a file of the run's artifact directory, relative to the page."""
        if self._result.artifact_dir is None:
            return None
        target = Path(self._result.artifact_dir) / relative
        try:
            path = os.path.relpath(target, self._directory)
        except ValueError:
            # Another drive on Windows: there is no relative path.
            return target.resolve().as_uri()
        return quote(Path(path).as_posix())

    def _files(self, runner: RunnerResult) -> str:
        items = []
        for artifact in runner.artifacts:
            href = self._href(artifact.path)
            name = _esc(artifact.path.rsplit("/", 1)[-1])
            label = f'<a href="{_esc(href)}">{name}</a>' if href else name
            mark = " (runner report)" if artifact.path == runner.report else ""
            detail = f"{_esc(artifact.kind)}, {artifact.size} bytes{mark}"
            items.append(f'<li>{label} <span class="muted">{detail}</span></li>')
        return '<ul class="files">' + "".join(items) + "</ul>" if items else ""

    def _runner(self, runner: RunnerResult) -> str:
        exit_code = "" if runner.exit_code is None else f"<span>exit code {runner.exit_code}</span>"
        parts = [
            '<section class="runner"><header>',
            f"<h3>{_esc(runner.runner)}: {_esc(runner.script)}</h3>{_badge(runner.status)}",
            (f'<span class="muted">step {_esc(runner.step)}</span>{exit_code}'
             f"<span>{_duration(runner.duration_ms)}</span></header>"),
        ]
        if runner.message:
            parts.append(f'<p class="msg">{_esc(runner.message)}</p>')
        parts.append(_cases(runner.cases))
        parts.append(self._files(runner))
        return "".join(parts) + "</section>"


def _case_rows(cases: list[CaseResult]) -> str:
    return "".join(
        f"<tr><td>{_badge(case.status)}</td><td>{_esc(case.name)}</td>"
        f"<td class=\"msg\">{_esc(case.message or '')}</td></tr>" for case in cases)


def _cases(cases: list[CaseResult]) -> str:
    """Tests of one runner: failures first and in full, a long run of passed tests folded away."""
    if not cases:
        return ""
    failed = [case for case in cases if case.status is not Status.PASSED]
    passed = [case for case in cases if case.status is Status.PASSED]
    head = "<tr><th>Status</th><th>Test</th><th>Message</th></tr>"
    table = f'<div class="scroll"><table>{head}{_case_rows(failed + passed[:_VISIBLE_PASSED])}</table></div>'
    rest = passed[_VISIBLE_PASSED:]
    if not rest:
        return table
    return (f"{table}<details><summary>{len(rest)} more passed</summary>"
            f'<div class="scroll"><table>{head}{_case_rows(rest)}</table></div></details>')


def render_html(result: RunResult, directory: Path) -> str:
    """Return the HTML report of a run, with artifact links relative to ``directory``."""
    return _Page(result, directory).render()
