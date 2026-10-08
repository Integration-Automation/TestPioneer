Consolidated Report
===================

Each runner has its own report format. TestPioneer reads them, translates them into one result
model and writes a single report for the whole run, whatever runners took part.

Report Files
------------

.. list-table::
   :header-rows: 1
   :widths: 35 12 53

   * - File
     - Format
     - Purpose
   * - ``report/testpioneer-report.json``
     - ``json``
     - The canonical, machine-readable result of the run.
   * - ``report/testpioneer-report.html``
     - ``html``
     - The same data for people: one self-contained page with the steps, every runner execution,
       its recorded tests and links to its artifacts.
   * - ``report/testpioneer-junit.xml``
     - ``junit``
     - JUnit XML for CI systems that display test results. Not written by default.

``json`` and ``html`` are written after every run, into ``report`` below the working directory,
and replace the files of the previous run. Change this in the workflow:

.. code-block:: yaml

   report_path: "build/report"            # default: report
   report_formats: [json, html, junit]    # default: [json, html]; [] writes no report
   jobs:
     steps:
       - name: run_api_test
         run: tests/api_test.json
         with: api-runner

or for one run, which takes precedence over the workflow:

.. code-block:: bash

   python -m test_pioneer run tests/test.yaml --report_path build/report --report_formats json,html,junit
   python -m test_pioneer run tests/test.yaml --report_formats none

.. code-block:: python

   from test_pioneer import RunOptions, execute_yaml

   result = execute_yaml("tests/test.yaml", options=RunOptions(report_formats=["junit"]))
   print(result.reports)

A report that cannot be written never changes the outcome of the run; the problem is added to
``warnings`` in the result.

Getting a Runner's Report into the Run
--------------------------------------

A runner's report is read from the artifact directory of its execution (:doc:`artifacts`). The
runner packages do not write there by themselves yet: a script names its report file, and the
file is created relative to the working directory. So a step declares what its runner writes,
and TestPioneer copies those files into the artifact directory when the runner ends:

.. code-block:: yaml

   jobs:
     steps:
       - name: run_api_test
         run: tests/api_test.json
         with: api-runner
         artifacts:
           - reports/api_*.json
           - screenshots

       - name: parallel_tests
         parallel_run:
           runners: ["web-runner", "api-runner"]
           scripts: ["tests/web.json", "tests/api.json"]
           artifacts:
             - ["reports/web_*.json", "screenshots"]
             - ["reports/par_api_*.json"]

with ``tests/api_test.json`` ending in its runner's report action, for example:

.. code-block:: json

   [
     ["AT_test_api_method", {"http_method": "get", "test_url": "http://localhost:8080/users",
                             "result_check_dict": {"status_code": 200}}],
     ["AT_generate_json_report", {"json_file_name": "reports/api_users"}]
   ]

Rules of ``artifacts``:

- A pattern is relative to the working directory and may use ``*``, ``?`` and ``**``. A folder
  stands for every file below it.
- For ``parallel_run`` it is a list with one list of patterns per script, in the same order.
- Only files changed since the runner started are copied, so a report left by an earlier run is
  never taken for this one.
- The files are copied, not moved, to ``collected/`` in the runner's artifact directory, with
  their relative path.
- A pattern that is absolute or contains ``..`` is not used. That, a pattern that matches no new
  file and a file that cannot be copied each add a warning to the result.
- The report generators of the runners do not create folders: ``reports/`` must exist before the
  script runs.

A runner that reads ``TEST_PIONEER_ARTIFACT_DIR`` and writes its report there needs no
``artifacts`` entry. An entry that is left in place does no harm: a pattern that the runner
satisfied inside its own artifact directory is not reported as unmatched, so one workflow works
with runner versions of both kinds.

Reading a Runner's Report
-------------------------

The web, API, load and GUI runners write a pair of files, ``<name>_success.json`` and
``<name>_failure.json``. Every record in them becomes one **recorded test** of the runner
execution:

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - Runner
     - Report action
     - A test is named by
   * - ``api-runner``
     - ``AT_generate_json_report``
     - The HTTP method and the URL.
   * - ``web-runner``
     - ``WR_generate_json_report``
     - The function that was called. Recording must be on: ``WR_set_record_enable``.
   * - ``gui-runner``
     - ``AC_generate_json_report``
     - The function that was called. Recording must be on: ``AC_set_record_enable``.
   * - ``load-runner``
     - ``LD_generate_json_report``
     - The HTTP method and the request name.
   * - ``file-runner``
     - None
     - FileAutomation writes no report, so only its outcome and output are known.

The parameters of web and GUI actions are left out of the test name, because they can hold text
that was typed, such as a password.

This is how a failed action is noticed. The runner packages exit with status 0 and raise nothing
when an action of a script fails; the failure is only in their report. A runner execution whose
report holds a failed test is ``failed``, with the message ``1 of 3 recorded test(s) failed``,
and so are its step and the run.

A report that is not valid JSON, does not have the expected layout, or is larger than 50 MB is
not read. The runner keeps the status it had, a warning is added, and the file stays in the
artifact directory.

A runner package keeps one list of records per process, and its report writes the whole list.
``run`` and ``run_folder`` steps call the runner inside the TestPioneer process, so the report
file of a later step of the same runner also holds the records of the earlier ones. TestPioneer
counts each record once, for the step that produced it: a report that starts with the records
already counted adds only what follows them. A failure is therefore blamed on the step it
happened in, and not on the later ones. If a script clears its runner's records, the next report
does not start with the earlier records and all of it counts. The raw report file is kept as the
runner wrote it. The entries of a ``parallel_run`` step are separate processes, so each of their
reports holds only its own records.

JSON Report
-----------

``testpioneer-report.json`` is the result described in :doc:`artifacts`, with the recorded tests
of each runner execution in ``cases``:

.. code-block:: json

   {
     "format_version": "1.0",
     "run_id": "20261008T031542Z-9f2c1a7b",
     "status": "failed",
     "summary": {"passed": 1, "failed": 1, "error": 0, "cancelled": 0, "total": 2},
     "cases": {"passed": 3, "failed": 1, "error": 0, "cancelled": 0, "total": 4},
     "runners": [
       {
         "runner": "api-runner",
         "script": "tests/api.json",
         "step": "parallel_tests",
         "status": "failed",
         "exit_code": 0,
         "message": "1 of 2 recorded test(s) failed",
         "artifact_dir": "runners/api-runner/02-parallel_tests-2",
         "report": "runners/api-runner/02-parallel_tests-2/collected/reports/par_api_failure.json",
         "artifacts": [
           {"path": "runners/api-runner/02-parallel_tests-2/collected/reports/par_api_failure.json",
            "kind": "report", "size": 412}
         ],
         "cases": [
           {"name": "post http://localhost:8080/login", "status": "failed",
            "message": "HTTPError('500 Server Error')"},
           {"name": "GET http://localhost:8080/users", "status": "passed", "message": null}
         ]
       }
     ],
     "warnings": [],
     "reports": ["report/testpioneer-report.json", "report/testpioneer-report.html"]
   }

``summary`` counts runner executions and the top-level ``cases`` counts recorded tests.
``report`` is the raw runner report the cases came from, relative to ``artifact_dir`` of the
run; it is ``null`` when the runner's files were not kept. The steps, timing fields and the rest
are as in the manifest, which holds the same data.

HTML Report
-----------

``testpioneer-report.html`` shows the status of the run, counts of runner executions and recorded
tests, the steps in order, and one block per runner execution with its message, its recorded
tests (failures first) and links to its kept artifacts, the raw runner report among them.

The page is a single file with no script and no external resource, so it can be attached to a CI
run or mailed as it is. The artifact links are relative to the page: keep ``report/`` and
``artifacts/`` side by side, or upload both, for them to work. Every name and message that comes
from a workflow or a runner is escaped.

JUnit XML
---------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Element
     - Content
   * - ``<testsuite>``
     - One per runner execution, named ``<runner>: <script>``.
   * - ``<testcase>``
     - One per recorded test. A runner execution without a report is a single test named after
       its script.
   * - ``workflow steps`` suite
     - The steps that are not runner steps (``wait``, ``download_file``, ...), so a failed
       download is not lost.
   * - ``<failure>``, ``<error>``, ``<skipped>``
     - Status ``failed``, ``error`` and ``cancelled``.

Compatibility
-------------

- ``report/`` is new output of every run. Set ``report_formats: []`` to write nothing.
- ``artifacts`` is a new, optional step key; a workflow without it runs as before.
- A run can now be ``failed`` where it used to pass unnoticed: when a collected runner report
  holds a failed test. ``python -m test_pioneer -e`` still exits with status 0 either way.
