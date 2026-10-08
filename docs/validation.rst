Validation
==========

A workflow can be checked without executing it. The check reads the YAML, compares it with the
workflow JSON Schema and then applies lint rules for what a schema cannot express. Every problem
is reported with its YAML path, line and column.

Command Line
------------

.. code-block:: bash

   python -m test_pioneer validate tests/test.yaml

For this workflow:

.. code-block:: yaml

   jobs:
     steps:
       - name: api_test
         run: tests/api_test.json
         with: api-runer
       - name: api_test
         wait: "5"

the command prints one line per problem, ``file:line:column: severity: path: message [code]``,
and exits with status 1:

.. code-block:: text

   tests/test.yaml:5:13: error: jobs.steps[0].with: 'api-runer' is not one of: gui-runner, web-runner, api-runner, load-runner, file-runner. Did you mean 'api-runner'? [schema-enum]
   tests/test.yaml:6:13: error: jobs.steps[1].name: step name 'api_test' is already used by jobs.steps[0] [duplicate-step-name]
   tests/test.yaml:7:13: error: jobs.steps[1].wait: expected an integer, got a string [schema-type]
   Checked 1 file(s): 3 error(s), 0 warning(s)

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Description
   * - ``files``
     - One or more workflow files to check. ``-`` reads a workflow from standard input, as UTF-8;
       it is reported under the name ``<stdin>``.
   * - ``--format {text,json}``
     - Output format. ``text`` (default) is shown above; ``json`` is described below.
   * - ``--strict``
     - Treat warnings as errors.
   * - ``--base_dir DIR``
     - Directory that script paths in the workflow are relative to. Defaults to the current
       directory, which is where ``run``, ``run_folder`` and ``parallel_run`` look when the
       workflow is executed.
   * - ``--no_file_check``
     - Do not check that the referenced scripts and folders exist.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Exit status
     - Meaning
   * - ``0``
     - No error. Warnings do not change the status unless ``--strict`` is given.
   * - ``1``
     - At least one file has an error, or a warning with ``--strict``.
   * - ``2``
     - The command line itself is wrong.

Errors and Warnings
-------------------

An **error** is something the executor would stop on, or an action that can never run as written.
A **warning** depends on the machine the check runs on, or is a leftover that the executor ignores.

.. list-table::
   :header-rows: 1
   :widths: 28 12 60

   * - Code
     - Severity
     - Meaning
   * - ``yaml-unreadable``
     - error
     - The file is missing, unreadable or not UTF-8.
   * - ``yaml-syntax``
     - error
     - The text is not one valid YAML document.
   * - ``duplicate-key``
     - error
     - A mapping repeats a key; YAML keeps only the last value.
   * - ``schema-type``
     - error
     - A value has the wrong type, for example ``wait: "5"``.
   * - ``schema-required``
     - error
     - ``jobs``, ``steps``, a step ``name``, or ``runners``/``scripts`` of ``parallel_run`` is missing.
   * - ``schema-enum``
     - error
     - A runner, a ``url_open_method``, ``keep_artifacts`` or a report format is not one of the
       known values.
   * - ``schema-min-items``
     - error
     - ``steps``, ``runners`` or ``scripts`` is an empty list.
   * - ``schema-min-length``
     - error
     - A path, URL or name is an empty string.
   * - ``schema-minimum``
     - error
     - ``wait`` is negative.
   * - ``duplicate-step-name``
     - error
     - Two steps share a ``name``.
   * - ``missing-action``
     - error
     - A step has a name but no action key, often because the key is misspelled.
   * - ``conflicting-actions``
     - error
     - A step has several action keys; only the first one would run.
   * - ``missing-required-field``
     - error
     - An action lacks a field it needs: ``with`` for ``run`` and ``run_folder``, ``file_path``
       for ``download_file``, ``zip_file_path`` for ``unzip_zipfile``.
   * - ``runners-scripts-mismatch``
     - error
     - ``runners`` and ``scripts`` of a ``parallel_run`` step have different lengths.
   * - ``artifacts-scripts-mismatch``
     - error
     - ``artifacts`` and ``scripts`` of a ``parallel_run`` step have different lengths.
   * - ``unknown-key``
     - warning
     - A key that TestPioneer does not read. The closest known key is suggested.
   * - ``unused-field``
     - warning
     - A field that belongs to another action, for example ``with`` on a ``wait`` step.
   * - ``artifact-pattern``
     - warning
     - An ``artifacts`` pattern is absolute or contains ``..``; it would not be used.
   * - ``unknown-program``
     - warning
     - ``close_program`` names a step that no earlier ``open_program`` step has.
   * - ``runner-not-installed``
     - warning
     - The package behind a runner is not installed on this machine.
   * - ``missing-file``
     - warning
     - A script of ``run`` or ``parallel_run``, or the folder of ``run_folder``, does not exist
       below ``--base_dir``. A path that an earlier ``download_file`` or ``unzip_zipfile`` step
       creates is not reported.

JSON Output
-----------

``--format json`` prints one object, for tools that show the diagnostics themselves:

.. code-block:: json

   {
     "schema_version": "1.0.0",
     "ok": false,
     "files": [
       {
         "source": "tests/test.yaml",
         "ok": false,
         "errors": 1,
         "warnings": 0,
         "diagnostics": [
           {
             "severity": "error",
             "code": "schema-type",
             "message": "expected an integer, got a string",
             "path": ["jobs", "steps", 1, "wait"],
             "pointer": "jobs.steps[1].wait",
             "line": 7,
             "column": 13,
             "source": "schema"
           }
         ]
       }
     ]
   }

``line`` and ``column`` start at 1 and are ``null`` when a problem has no position, as for a file
that cannot be read. ``source`` is ``yaml``, ``schema`` or ``lint``. The top-level ``ok`` follows
the exit status, so it is ``false`` for a warning under ``--strict``.

Checking Text That Is Not Saved
-------------------------------

An editor can check the buffer in front of the user without writing it to disk:

.. code-block:: bash

   python -m test_pioneer validate --format json --base_dir path/to/project - < buffer.yml

``--base_dir`` says where the scripts the workflow names are, since standard input has no
location of its own. In the JSON output the file's ``source`` is ``<stdin>``.

Python API
----------

.. code-block:: python

   from test_pioneer import lint_yaml, validate_yaml

   result = lint_yaml("tests/test.yaml")
   if not result.ok:
       for problem in result.errors:
           print(problem.line, problem.column, problem.code, problem.message)

- ``validate_yaml`` checks the YAML syntax and the JSON Schema.
- ``lint_yaml`` does the same and then applies the lint rules. This is what the command runs.
- ``load_yaml`` parses a workflow and keeps the position of every key and value.
- ``get_yaml_schema`` returns the JSON Schema as a ``dict``.

See :doc:`api-reference` for the signatures.

JSON Schema
-----------

The schema is published in the repository as ``schema/testpioneer.schema.json`` (JSON Schema
draft 2020-12). Its ``version`` field follows semantic versioning: the minor part grows when
something is added, the major part when a workflow that used to validate no longer does.

Print or save the schema of the installed version:

.. code-block:: bash

   python -m test_pioneer schema
   python -m test_pioneer schema > testpioneer.schema.json

An editor with a YAML language server completes keys and runner names from it. Point the file at
the schema with a comment on its first line:

.. code-block:: yaml

   # yaml-language-server: $schema=https://raw.githubusercontent.com/Integration-Automation/TestPioneer/main/schema/testpioneer.schema.json
   jobs:
     steps:
       - name: api_test
         run: tests/api_test.json
         with: api-runner

The schema covers structure and types. Rules such as unique step names are lint rules, so they
are reported by ``validate`` and ``lint_yaml`` but not by a schema-only tool.

In CI
-----

Validate before running, so a broken workflow fails in seconds:

.. code-block:: yaml

   - name: Validate workflows
     run: python -m test_pioneer validate tests/test.yaml

   - name: Run workflows
     run: python -m test_pioneer -e tests/test.yaml

Compatibility
-------------

Validation is a separate command. ``python -m test_pioneer -e`` and ``execute_yaml`` execute a
workflow exactly as before, whether or not it would pass ``validate``.
