"""The workflow vocabulary: top-level keys, step types and their fields.

The JSON Schema is built from this module, the linter reads it, and a test compares it with the
executor's handler table, so a step type is described in one place.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

JsonSchema = dict[str, object]

RUNNER_REF = "#/$defs/runner"
URL_OPEN_METHODS: tuple[str, ...] = ("open", "open_new", "open_new_tab")


def _text(description: str, allow_empty: bool = False) -> JsonSchema:
    """Schema of a string value; empty strings are rejected unless ``allow_empty``."""
    schema: JsonSchema = {"type": "string", "description": description}
    if not allow_empty:
        schema["minLength"] = 1
    return schema


@dataclass(frozen=True)
class ActionSpec:
    """One step type: the key that selects it, that key's value, and its companion keys."""

    key: str
    value: Mapping[str, object]
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()

    @property
    def fields(self) -> tuple[str, ...]:
        """Every companion key this step type reads."""
        return self.required + self.optional


TOP_LEVEL_FIELDS: Mapping[str, Mapping[str, object]] = MappingProxyType({
    "pioneer_log": _text("Log file path. When set, step execution is logged to this file.",
                        allow_empty=True),
    "recording_path": _text(
        "Screen recording output path, without extension. Needs test_pioneer[gui].",
        allow_empty=True),
})

# Keys a step reads besides its name and its action key.
STEP_FIELDS: Mapping[str, Mapping[str, object]] = MappingProxyType({
    "with": {"$ref": RUNNER_REF},
    "url_open_method": {
        "type": "string",
        "enum": list(URL_OPEN_METHODS),
        "description": "How the browser opens the URL. Defaults to open.",
    },
    "file_path": _text("Local path the downloaded file is saved to."),
    "redirect_stdout": _text("File the program's standard output is written to.", allow_empty=True),
    "redirect_stderr": _text("File the program's standard error is written to.", allow_empty=True),
    "zip_file_path": _text("Path of the zip archive to extract."),
    "password": _text("Password of an encrypted archive.", allow_empty=True),
    "extract_path": _text("Directory to extract into. Defaults to the working directory.", allow_empty=True),
})

# In dispatch order: when a step holds several action keys, the executor runs the first one.
ACTIONS: tuple[ActionSpec, ...] = (
    ActionSpec("run", _text("JSON action file to run, relative to the working directory."),
               required=("with",)),
    ActionSpec("run_folder", _text("Folder whose *.json files are all run, in name order."),
               required=("with",)),
    ActionSpec("open_url", _text("URL to open in the default browser."),
               optional=("url_open_method",)),
    ActionSpec("download_file", _text("URL of the file to download."), required=("file_path",)),
    ActionSpec("wait", {"type": "integer", "minimum": 0, "description": "Seconds to wait."}),
    ActionSpec("open_program", _text("Program or command line to start. Close it by step name."),
               optional=("redirect_stdout", "redirect_stderr")),
    ActionSpec("close_program", _text("Name of the open_program step whose program is closed.")),
    ActionSpec("unzip_zipfile",
               {"description": "Marks an unzip step. The archive is named by zip_file_path."},
               required=("zip_file_path",), optional=("password", "extract_path")),
    ActionSpec("parallel_run", {"$ref": "#/$defs/parallel_run"}),
)

ACTION_KEYS: tuple[str, ...] = tuple(action.key for action in ACTIONS)
ACTION_BY_KEY: Mapping[str, ActionSpec] = MappingProxyType({action.key: action for action in ACTIONS})

TOP_LEVEL_KEYS: tuple[str, ...] = (*TOP_LEVEL_FIELDS, "jobs")
JOBS_KEYS: tuple[str, ...] = ("steps",)
STEP_KEYS: tuple[str, ...] = ("name", *ACTION_KEYS, *STEP_FIELDS)
PARALLEL_RUN_KEYS: tuple[str, ...] = ("runners", "scripts", "executor_path")
