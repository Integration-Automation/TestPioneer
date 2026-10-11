Changelog
=========

Unreleased
----------

- Workflow validation without execution: ``python -m test_pioneer validate``, a versioned JSON
  Schema (``schema/testpioneer.schema.json``) and lint rules, with diagnostics located by line
  and column (:doc:`validation`)
- Every run has an ID and returns a result; the output, exit code and files of each runner that
  did not pass are kept under ``artifacts/<run-id>/`` (:doc:`artifacts`)
- Runner reports are read, a failed test in one fails the run, and one consolidated JSON and HTML
  report is written per run, with optional JUnit XML (:doc:`reports`)
- ``python -m test_pioneer run`` exits with status 1 when the run did not pass
- New optional workflow keys: ``artifacts_path``, ``keep_artifacts``, ``report_path``,
  ``report_formats``, and ``artifacts`` on ``run``, ``run_folder`` and ``parallel_run``
- Existing workflows and ``python -m test_pioneer -e`` behave as before (:doc:`migration`)

v0.1.33
-------

- Current stable release
- YAML-driven test execution with pluggable runners
- Parallel execution support
- Video recording for GUI tests
- Docker images for GUI and non-GUI testing
- GitHub Actions CI pipeline
