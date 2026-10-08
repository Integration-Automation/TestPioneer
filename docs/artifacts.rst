Run IDs and Artifacts
=====================

Every execution of a workflow is a **run** with its own ID. While a run is in progress TestPioneer
collects, per runner execution, what that runner printed, how it ended and whatever files it
wrote into the directory it was given. When the run ends, the artifacts of what failed are kept.

Run ID
------

A run ID looks like ``20261008T031542Z-9f2c1a7b``: the UTC start time and a random suffix. It
names the run's artifact directory, appears in its log and manifest, and is handed to every
runner. You can choose it yourself:

.. code-block:: bash

   python -m test_pioneer run tests/test.yaml --run_id nightly-42

.. code-block:: python

   from test_pioneer import RunOptions, execute_yaml

   result = execute_yaml("tests/test.yaml", options=RunOptions(run_id="nightly-42"))

A run ID is 1 to 64 letters, digits, ``.``, ``_`` or ``-``. It starts with a letter or digit and
does not end with ``.``.

Artifact Directory
------------------

.. code-block:: text

   artifacts/
     <run-id>/
       runners/
         api-runner/
           01-run_api_test/          one directory per runner execution
             stdout.log
             stderr.log
             collected/              files the step declared with artifacts:
             ...                     files the runner wrote itself
         web-runner/
           02-parallel_tests-1/      entry 1 of a parallel_run step
       testpioneer/
         execution.log               what TestPioneer logged for this run
         manifest.json               the run result (see below)

The directory of a runner execution is named after its position in the run and its step.
Characters that are not safe in a path are replaced, so a step name can never point outside the
run directory.

What Is Kept
------------

``keep_artifacts`` decides what is left when the run ends:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Value
     - Result
   * - ``on_failure``
     - Default. A run that passed leaves nothing behind. A run that did not pass keeps
       ``testpioneer/`` and the directory of every runner execution that did not pass.
   * - ``always``
     - Every run keeps everything, including the runners that passed.
   * - ``never``
     - Nothing is kept, even when the run fails.

Set it, and the location, in the workflow:

.. code-block:: yaml

   artifacts_path: "build/artifacts"     # default: artifacts
   keep_artifacts: always                # default: on_failure
   jobs:
     steps:
       - name: run_api_test
         run: tests/api_test.json
         with: api-runner

or for one run, which takes precedence over the workflow:

.. code-block:: bash

   python -m test_pioneer run tests/test.yaml --artifacts_path build/artifacts --keep_artifacts always

.. code-block:: python

   execute_yaml("tests/test.yaml", options=RunOptions(artifacts_path="build/artifacts", keep_artifacts="always"))

A problem with the artifacts never changes the outcome of the run. If the directory cannot be
created or a file cannot be listed, the run goes on and the problem is added to ``warnings`` in
the result.

Runner Contract
---------------

Each runner execution receives two environment variables:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Variable
     - Value
   * - ``TEST_PIONEER_RUN_ID``
     - The ID of the run.
   * - ``TEST_PIONEER_ARTIFACT_DIR``
     - Absolute path of the directory this execution may write into. It exists before the runner
       starts.

A runner writes its reports, screenshots, videos and traces there. It must not rely on its
working directory, which stays the one TestPioneer was started in.

A step can also name the files its runner writes, with ``artifacts:``; they are copied into
``collected/`` when the runner ends. See :doc:`reports`.

Native Support
^^^^^^^^^^^^^^

A runner supports the contract natively when it does two things.

1. With ``TEST_PIONEER_ARTIFACT_DIR`` set, a report it is asked to write under a relative name
   is written below that directory, and missing folders below it are created. An absolute name
   is used as it is, and without the variable nothing changes.
2. ``python -m <package> --execute_file <script>`` exits with a non-zero status when an action
   of the script failed or a failure was recorded, and with 0 otherwise.

TestPioneer is ready for such a runner: a non-zero exit status makes the execution ``failed``,
its report is read from the artifact directory, and an ``artifacts:`` pattern left in the
workflow is not reported as unmatched when the runner wrote the files itself. No runner package
does the first yet. The second is in LoadDensity's development branch; every released package
exits with status 0 when an action fails.

A runner that does not read the variables yet is still covered:

- **Sub-processes** (``parallel_run``): standard output and standard error go to ``stdout.log``
  and ``stderr.log`` in the artifact directory and are still shown on the console. The exit code
  and the start and end times are recorded.
- **In-process calls** (``run``, ``run_folder``): what the runner prints is copied to the same two
  files, the variables are set for the length of the call, and the timing and any exception are
  recorded.

Results
-------

``execute_yaml`` returns the result of the run, and ``testpioneer/manifest.json`` holds the same
data:

.. code-block:: json

   {
     "format_version": "1.0",
     "run_id": "20261008T031542Z-9f2c1a7b",
     "status": "failed",
     "started_at": "2026-10-08T03:15:42.105Z",
     "finished_at": "2026-10-08T03:15:49.871Z",
     "duration_ms": 7766,
     "workflow": "tests/test.yaml",
     "message": null,
     "artifact_dir": "artifacts/20261008T031542Z-9f2c1a7b",
     "summary": {"passed": 1, "failed": 1, "error": 0, "cancelled": 0, "total": 2},
     "steps": [
       {
         "name": "parallel_tests",
         "action": "parallel_run",
         "status": "failed",
         "started_at": "2026-10-08T03:15:42.110Z",
         "finished_at": "2026-10-08T03:15:49.870Z",
         "duration_ms": 7760,
         "message": "Runner api-runner (tests/api.json) failed: exit code 1"
       }
     ],
     "runners": [
       {
         "runner": "api-runner",
         "script": "tests/api.json",
         "step": "parallel_tests",
         "status": "failed",
         "exit_code": 1,
         "started_at": "2026-10-08T03:15:42.131Z",
         "finished_at": "2026-10-08T03:15:49.870Z",
         "duration_ms": 7739,
         "message": "exit code 1",
         "artifact_dir": "runners/api-runner/02-parallel_tests-2",
         "report": null,
         "artifacts": [
           {"path": "runners/api-runner/02-parallel_tests-2/stderr.log", "kind": "log", "size": 412}
         ]
       }
     ],
     "warnings": []
   }

``summary`` counts the runner executions. Paths inside ``runners`` are relative to
``artifact_dir``. ``exit_code`` is ``null`` for an in-process call. ``kind`` is ``log``,
``report``, ``screenshot``, ``video``, ``trace`` or ``other``, chosen by file extension.

The result also holds the tests each runner recorded in its own report (``cases``), the raw
report they came from (``report``) and the consolidated report files (``reports``); these are
described in :doc:`reports`.

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Status
     - Meaning
   * - ``passed``
     - Finished without a problem.
   * - ``failed``
     - Ran to the end and reported a failure: a runner process exited with a non-zero code, the
       runner's own report holds a failed test, or a step returned a failure.
   * - ``error``
     - Could not be completed: a script or runner that does not exist, a process that could not
       be started, an exception.
   * - ``cancelled``
     - Did not run because an earlier step stopped the run, or was interrupted.

A step takes the worst status of itself and its runner executions, and the run the worst status
of its steps: ``error`` over ``failed`` over ``cancelled`` over ``passed``.

Exit Status
-----------

.. code-block:: bash

   python -m test_pioneer run tests/test.yaml

``run`` exits with status 0 when the run passed and 1 when it did not, so a CI job fails with
the tests. It prints one line, for example::

   Run 20261008T031542Z-9f2c1a7b failed: 2 runner execution(s) (1 passed, 1 failed); artifacts: artifacts/20261008T031542Z-9f2c1a7b

.. note::

   The released runner packages exit with status 0 when one of the actions in a script fails; only a
   script that cannot be read or is malformed makes them exit with 1. A failed action is found
   in the runner's own report instead: have the script write one and declare it with
   ``artifacts:``, as described in :doc:`reports`.

Compatibility
-------------

- ``python -m test_pioneer -e`` executes the workflow as before and still exits with status 0
  whatever the steps did. Use ``run`` when the exit status should follow the result.
- A failed ``parallel_run`` runner does not stop the steps after it, as before. It now makes the
  step and the run ``failed``.
- ``execute_yaml`` used to return ``None`` and now returns the result. It raises the same
  exceptions as before.
- New files appear under ``artifacts_path``, by default only for a run that did not pass
  (``keep_artifacts: never`` turns them off), and under ``report_path`` (:doc:`reports`).
- A step handler that is called directly, outside ``execute_yaml``, records nothing and starts
  its processes exactly as before.
