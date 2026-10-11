"""The artifact contract between TestPioneer and a runner: two environment variables.

Every runner execution receives the ID of the run it belongs to and a directory of its own to
write logs, reports, screenshots and videos into. A runner that ignores them still works: its
output and exit code are captured for it.
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

from test_pioneer.utils.exception.exceptions import WrongInputException

ENV_RUN_ID = "TEST_PIONEER_RUN_ID"
ENV_ARTIFACT_DIR = "TEST_PIONEER_ARTIFACT_DIR"

# What is left of a run's artifact directory once the run has ended.
KEEP_ON_FAILURE = "on_failure"
KEEP_ALWAYS = "always"
KEEP_NEVER = "never"
KEEP_POLICIES: tuple[str, ...] = (KEEP_ON_FAILURE, KEEP_ALWAYS, KEEP_NEVER)
DEFAULT_ARTIFACTS_PATH = "artifacts"

# A run ID names a directory, so it is limited to characters that are safe in a path.
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_SLUG = 48


def new_run_id() -> str:
    """Return a new run ID: a sortable UTC timestamp and a random suffix."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{secrets.token_hex(4)}"


def checked_run_id(run_id: str) -> str:
    """Return ``run_id`` when it is safe to use as a directory name; raise otherwise."""
    if not _RUN_ID.fullmatch(run_id) or run_id.endswith("."):
        raise WrongInputException(
            "Wrong input: a run ID is 1 to 64 letters, digits, '.', '_' or '-', "
            f"starts with a letter or digit and does not end with '.', got {run_id!r}")
    return run_id


def slug(text: str, fallback: str = "item") -> str:
    """Reduce free text, such as a step name, to a short name that is safe in a path."""
    cleaned = _UNSAFE.sub("_", text).strip("._-")[:_MAX_SLUG].rstrip("._-")
    return cleaned or fallback
