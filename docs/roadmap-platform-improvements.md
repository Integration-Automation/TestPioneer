# TestPioneer Platform Improvements Roadmap

This document defines the implementation plan for the next TestPioneer iteration. It is intentionally scoped as an architecture and delivery plan first; implementation PRs should be split by subsystem so the runner contract remains stable.

## Goals

1. Make YAML workflows easier to author and review.
2. Provide a consistent editor/validation experience.
3. Make parallel runner failures diagnosable by preserving runner-specific artifacts.
4. Produce one consolidated test report from all runners.
5. Keep the core executor backward compatible with existing YAML.

## 1. UI redesign

### Scope

Treat TestPioneer as the execution engine and expose the authoring/reporting experience through the existing visual-editor direction (PyBreeze), with a stable boundary between UI and the Python engine.

Proposed workspace:

- Project/file tree
- YAML editor
- Schema/lint diagnostics panel
- Run controls and live status
- Runner/step timeline
- Artifacts panel
- Consolidated report viewer

### Design principles

- YAML remains the source of truth.
- UI edits must round-trip without changing unrelated YAML.
- Validation errors should point to the YAML path and line/column.
- A run gets a unique run ID used by logs, artifacts, and reports.
- UI should not need to know runner-internal implementation details.

### Acceptance criteria

- Existing YAML can be opened without migration.
- Invalid YAML/schema errors are visible before execution.
- A run can be started, monitored, and inspected from one workspace.
- Artifacts and the merged report are discoverable from the run result.

## 2. YAML editor

### Scope

Implement the editor as a YAML-aware component rather than a generic text box.

Capabilities:

- Syntax highlighting
- YAML indentation/folding
- Schema-aware completion for top-level keys, jobs, steps, runner names, and action-specific fields
- Inline diagnostics
- Jump from a diagnostic to the exact YAML path
- Format/normalize YAML without changing semantic values
- Preserve comments where the editor library supports round-tripping

### API boundary

Introduce a small engine-facing validation API, for example:

- `load_yaml()`
- `validate_yaml()`
- `lint_yaml()`
- `get_yaml_schema()`

The UI should consume structured diagnostics rather than parse executor log messages.

## 3. YAML Schema + linter

### Proposed schema

Add a versioned JSON Schema under `schema/testpioneer.schema.json`.

Initial schema coverage:

- `pioneer_log`
- `recording_path`
- `jobs.steps`
- unique step `name`
- supported actions:
  - `run`
  - `run_folder`
  - `open_url`
  - `download_file`
  - `wait`
  - `open_program`
  - `close_program`
  - `unzip_zipfile`
  - `parallel_run`
- runner enum:
  - `gui-runner`
  - `web-runner`
  - `api-runner`
  - `load-runner`
  - `file-runner`

Schema validation should cover structural/type errors. The linter should additionally cover semantic rules that JSON Schema cannot express cleanly:

- duplicate step names
- action-specific required fields
- runners/scripts length mismatch
- unknown runner names
- missing referenced files where statically checkable
- conflicting action keys

### CLI

Add a validation command without executing tests, e.g.:

```bash
python -m test_pioneer validate tests/test.yaml
```

Exit non-zero on errors so CI can fail fast.

## 4. Collect runner artifacts on failure

### Current gap

`parallel_run` launches runner processes and waits for completion, but the process boundary does not currently define a standard artifact contract. This makes runner-specific logs, screenshots, videos, traces, and raw reports difficult to collect consistently.

### Proposed artifact contract

Create a per-run directory:

```text
artifacts/
  <run-id>/
    runners/
      web-runner/
      api-runner/
      load-runner/
      file-runner/
      gui-runner/
    testpioneer/
      execution.log
      manifest.json
```

Each runner invocation receives an artifact directory through an explicit environment variable or CLI argument, for example:

```text
TEST_PIONEER_ARTIFACT_DIR=<...>/runners/<runner>
TEST_PIONEER_RUN_ID=<run-id>
```

Do not rely on the runner's current working directory.

### Failure behavior

- Always preserve artifacts when a runner fails.
- Preserve artifacts for successful runners when configured, so the merged report can link to them.
- Record process exit code, start/end time, runner, script, and artifact path in a manifest.
- If artifact collection itself fails, report that as a collection warning rather than hiding the original test failure.

### Runner compatibility

Use an adapter/contract layer so runners that do not yet support an artifact argument can still be wrapped. Add native artifact support incrementally to each runner.

## 5. Merge runner reports

### Proposed normalized result model

Introduce a TestPioneer-owned result format independent of any single runner:

```json
{
  "run_id": "...",
  "status": "passed|failed|error|cancelled",
  "started_at": "...",
  "finished_at": "...",
  "runners": [
    {
      "runner": "web-runner",
      "script": "...",
      "status": "passed|failed|error|cancelled",
      "exit_code": 0,
      "duration_ms": 1234,
      "report": "runners/web-runner/report.json",
      "artifacts": []
    }
  ]
}
```

### Merge pipeline

1. Execute runners independently.
2. Collect their raw artifacts/reports.
3. Parse supported runner report formats through adapters.
4. Normalize into the TestPioneer result model.
5. Generate one consolidated report.
6. Keep raw reports alongside the merged report for debugging.

### Report output

Proposed outputs:

- `report/testpioneer-report.json` — machine-readable canonical result
- `report/testpioneer-report.html` — human-readable consolidated report
- optional JUnit XML for CI integrations

The merged report should show:

- overall pass/fail/error counts
- runner summary
- test/script status
- duration
- failure message/stack where available
- links to runner artifacts
- links to raw runner reports

## 6. README complete example

Rewrite the README quick-start section around one end-to-end example instead of isolated snippets.

The example should show:

1. Installation
2. Project layout
3. A complete YAML workflow
4. Running locally
5. Running in CI
6. Parallel runners
7. Where logs/artifacts/reports are generated
8. YAML validation/linting
9. How to open the workflow in the UI/editor
10. Troubleshooting common failures

Keep the existing English/Traditional Chinese/Simplified Chinese README structure aligned.

## Suggested implementation order

### Phase 1 — Contracts and validation

- [x] Define run/artifact/result data models.
- [x] Add versioned JSON Schema.
- [x] Add YAML validator/linter API.
- [x] Add validation CLI.
- [x] Add unit tests for schema and semantic lint rules.

### Phase 2 — Runner execution and artifacts

- [x] Introduce run ID and artifact directory management.
- [x] Extend parallel runner process launch with artifact context.
- [x] Capture process metadata and exit codes.
- [x] Define runner adapter interface.
- [x] Add artifact collection tests.
- [x] Verify failure artifacts are preserved.

### Phase 3 — Report normalization

- [x] Define normalized TestPioneer result model.
- [x] Implement runner report adapters.
- [x] Implement merge service.
- [x] Generate JSON + HTML reports.
- [x] Add JUnit output if useful for CI consumers.
- [x] Add integration tests with multiple runners.

### Phase 4 — YAML editor / UI

- [ ] Build YAML editor around the schema.
- [ ] Add completion and inline diagnostics.
- [ ] Add run controls/status.
- [ ] Add artifact/report viewer.
- [ ] Add UI integration tests.
- [ ] Ensure YAML round-trip compatibility.

### Phase 5 — Documentation

- [ ] Replace the README quick-start with a complete workflow.
- [ ] Document schema/linter.
- [ ] Document artifact directory and runner contract.
- [ ] Document merged report format.
- [ ] Add migration/compatibility notes.
- [ ] Synchronize Traditional Chinese and Simplified Chinese README content.

## Testing strategy

### Unit

- YAML parsing and schema validation
- semantic lint rules
- artifact manifest generation
- runner process result handling
- report normalization/merge

### Integration

- sequential and parallel execution
- one runner failure while another succeeds
- multiple runner failures
- missing runner dependency
- missing script
- malformed runner report
- artifact collection failure
- merged report generation

### Regression

Existing behavior must remain valid for current YAML files and existing runner commands.

## Definition of Done

- Existing YAML workflows continue to execute.
- Invalid workflows fail validation before test execution in CI.
- Every runner execution has a traceable run ID.
- Failed runs preserve runner-specific artifacts.
- All supported runner results can be represented in one normalized report.
- The UI can edit, validate, execute, and inspect a workflow.
- README contains a complete copy/pasteable example and explains outputs.
- CI covers schema/linter, artifact collection, and report merging.
