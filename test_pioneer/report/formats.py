"""Names of the consolidated report: its formats, its default location and its files."""
from __future__ import annotations

FORMAT_JSON = "json"
FORMAT_HTML = "html"
FORMAT_JUNIT = "junit"
REPORT_FORMATS: tuple[str, ...] = (FORMAT_JSON, FORMAT_HTML, FORMAT_JUNIT)
DEFAULT_REPORT_FORMATS: tuple[str, ...] = (FORMAT_JSON, FORMAT_HTML)
DEFAULT_REPORT_PATH = "report"

REPORT_FILES: dict[str, str] = {
    FORMAT_JSON: "testpioneer-report.json",
    FORMAT_HTML: "testpioneer-report.html",
    FORMAT_JUNIT: "testpioneer-junit.xml",
}
