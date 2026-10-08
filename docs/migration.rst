Upgrading
=========

What changes for a project that already uses TestPioneer when it moves to the version with
workflow validation, run artifacts and the consolidated report.

Nothing to Change
-----------------

- Every existing workflow file runs without an edit. All new keys are optional.
- ``python -m test_pioneer -e <file>`` executes the workflow as before and still exits with
  status 0 whatever the steps did.
- ``execute_yaml(stream, yaml_type)`` takes the same arguments and raises the same exceptions.
- The runners are started with the same command line,
  ``python -m <package> --execute_file <script>``, in the same working directory.
- A failed step still stops the steps after it, and a ``parallel_run`` runner that fails still
  does not.

New Files
---------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Path
     - Written
     - Turn it off or move it
   * - ``report/testpioneer-report.json``, ``report/testpioneer-report.html``
     - After every run, replacing the previous ones
     - ``report_formats: []``; ``report_path``
   * - ``artifacts/<run-id>/``
     - Only for a run that did not pass
     - ``keep_artifacts: never``; ``artifacts_path``

Both are below the directory TestPioneer is started in. Add them to ``.gitignore``:

.. code-block:: text

   /artifacts/
   /report/

With both turned off, a run leaves exactly the files it left before.

What Behaves Differently
------------------------

- **Return value.** ``execute_yaml`` returned ``None`` and now returns a ``RunResult``.
  Code that ignored the return value is not affected.
- **A run can be failed where it used to end silently.** Two things are now noticed: a
  ``parallel_run`` runner that exits with a non-zero status, and a runner report, collected with
  ``artifacts:``, that holds a failed test. Both make the step and the run ``failed`` in the
  result, in the report, and in the exit status of ``python -m test_pioneer run``. The exit
  status of ``-e`` does not change.
- **A download that fails now fails its step.** A ``download_file`` step used to be reported as
  done even when nothing was downloaded, and the workflow went on. It now stops there, like any
  other failed step.
- **Step names are unique per workflow, not per process.** A second ``execute_yaml`` call in
  the same Python process used to stop with "job name duplicated" when it reused a step name of
  the first. It now runs. A program that an earlier call left open can still be closed by its
  name, and ``open_program`` refuses to start another one under a name that is still open.
- **Runner processes get two more environment variables**, ``TEST_PIONEER_RUN_ID`` and
  ``TEST_PIONEER_ARTIFACT_DIR``.
- **The console output of** ``parallel_run`` **runners** is still shown, now copied from log files
  ten times a second. Lines of different runners can interleave differently than before.
- **Interrupting** a ``parallel_run`` step (Ctrl+C) now also stops the runner processes it
  started.
- **An error message.** For a workflow file that is not a mapping, the exception text is now
  ``Not a dict: got list`` and no longer contains the content of the file.
- **Step messages** are also written to the run's ``execution.log``. The ``TestPioneer`` logger
  itself is unchanged: it only receives them when ``pioneer_log`` is set.

Recommended Steps
-----------------

1. Check the workflows: ``python -m test_pioneer validate <files>``. It reports mistakes that
   used to pass silently, such as a misspelled key or a step without its runner. See
   :doc:`validation`.
2. In CI, validate first, then replace ``-e`` with ``run`` so that a failed run fails the job.
3. End each runner script with its report action and name the files in the step's
   ``artifacts:``. This is what lets a failed action fail the run. See :doc:`reports`.
4. Upload ``report/`` and ``artifacts/`` from CI, whether the job passed or not.

:doc:`getting-started` shows all four in one example.

For Tools That Drive TestPioneer
--------------------------------

The contract an editor or launcher relied on is unchanged: ``python -m test_pioneer -e <yaml>``
and ``create_template_dir``. New, stable interfaces to build on:

- ``python -m test_pioneer validate --format json`` and the diagnostic codes (:doc:`validation`);
- ``schema/testpioneer.schema.json`` and ``python -m test_pioneer schema``;
- ``python -m test_pioneer run`` with ``--run_id``, its exit status, and
  ``report/testpioneer-report.json`` or ``artifacts/<run-id>/testpioneer/manifest.json``
  (:doc:`artifacts`, :doc:`reports`).
