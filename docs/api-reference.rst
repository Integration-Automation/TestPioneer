API Reference
=============

TestPioneer exposes its public functions from the top-level package: ``execute_yaml`` and
``create_template_dir`` run and scaffold workflows; ``validate_yaml``, ``lint_yaml``,
``load_yaml`` and ``get_yaml_schema`` check them without executing anything.

execute_yaml
------------

.. code-block:: python

   from test_pioneer import execute_yaml

   execute_yaml(stream, yaml_type="File")

Execute a YAML test workflow.

**Parameters:**

- ``stream`` (str) -- Path to a YAML file, or a YAML string.
- ``yaml_type`` (str) -- ``"File"`` (default) to read from a file path, or ``"String"``
  to parse the stream as a YAML string directly.

**Raises:**

- ``YamlException`` -- If the YAML is invalid, missing ``jobs`` or ``steps``.
- ``WrongInputException`` -- If ``yaml_type`` is not ``"File"`` or ``"String"``.
- ``ExecutorException`` -- If recording setup fails.

**Example:**

.. code-block:: python

   # From file
   execute_yaml("path/to/test.yaml")

   # From string
   execute_yaml("""
   jobs:
     steps:
       - name: test
         run: tests/test.json
         with: api-runner
   """, yaml_type="String")

create_template_dir
-------------------

.. code-block:: python

   from test_pioneer import create_template_dir

   create_template_dir(project_path=None, parent_name=".TestPioneer")

Create a template project directory with a sample YAML workflow file.

**Parameters:**

- ``project_path`` (str | None) -- Base directory path. Defaults to the current
  working directory.
- ``parent_name`` (str) -- Name of the template directory. Defaults to ``".TestPioneer"``.

**Example:**

.. code-block:: python

   # Create in current directory
   create_template_dir()

   # Create in a specific location
   create_template_dir(project_path="/home/user/projects", parent_name="my_tests")

validate_yaml
-------------

.. code-block:: python

   from test_pioneer import validate_yaml

   result = validate_yaml(stream, yaml_type="File")

Check a workflow's YAML syntax and its structure against the JSON Schema. Nothing is executed.

**Parameters:**

- ``stream`` (str) -- Path to a YAML file, or a YAML string.
- ``yaml_type`` (str) -- ``"File"`` (default) or ``"String"``, as in ``execute_yaml``.

**Returns:** a ``ValidationResult`` with these attributes:

- ``ok`` (bool) -- ``True`` when there is no error. Warnings do not count.
- ``diagnostics`` -- every ``Diagnostic``, in document order.
- ``errors`` / ``warnings`` -- the diagnostics of each severity.
- ``source`` (str | None) -- the file path, or ``None`` for a YAML string.
- ``to_dict()`` -- the JSON form printed by ``validate --format json``.

Each ``Diagnostic`` has ``severity`` (``Severity.ERROR`` or ``Severity.WARNING``), ``code``,
``message``, ``path`` (a tuple such as ``("jobs", "steps", 0, "with")``), ``line`` and ``column``
(starting at 1, or ``None``) and ``source`` (``"yaml"``, ``"schema"`` or ``"lint"``).

**Raises:**

- ``WrongInputException`` -- If ``yaml_type`` is not ``"File"`` or ``"String"``. A file that
  cannot be read and a YAML syntax error are returned as diagnostics, not raised.

lint_yaml
---------

.. code-block:: python

   from test_pioneer import lint_yaml
   from test_pioneer.validation import LintOptions

   result = lint_yaml(stream, yaml_type="File", options=None)

Run ``validate_yaml`` and then the lint rules: duplicate step names, missing or conflicting
actions, fields an action needs, ``runners``/``scripts`` length, unknown keys, runner packages
and referenced files. The codes are listed in :doc:`validation`.

**Parameters:**

- ``stream``, ``yaml_type`` -- As in ``validate_yaml``.
- ``options`` (LintOptions | None) -- ``LintOptions(base_dir=None, check_files=True)``.
  ``base_dir`` (``pathlib.Path``) is where relative script paths are resolved and defaults to
  the current directory. ``check_files=False`` turns the missing-file rule off.

**Returns:** a ``ValidationResult``.

**Example:**

.. code-block:: python

   from pathlib import Path

   result = lint_yaml("tests/test.yaml", options=LintOptions(base_dir=Path("project")))
   for problem in result.diagnostics:
       print(f"{problem.line}:{problem.column} {problem.severity.value} {problem.message}")

load_yaml
---------

.. code-block:: python

   from test_pioneer import load_yaml

   document = load_yaml(stream, yaml_type="File")

Parse a workflow without executing it and keep the position of every key and value.

**Returns:** a ``YamlDocument`` with these attributes:

- ``data`` -- the parsed YAML, or ``None`` when it could not be parsed.
- ``parsed`` (bool) -- ``False`` when the text could not be read or parsed.
- ``diagnostics`` -- syntax problems and duplicate keys.
- ``positions.locate(path, on_key=False)`` -- the ``(line, column)`` of a YAML path, or of its
  nearest parent when the path does not exist.
- ``source`` (str | None) -- the file path, or ``None`` for a YAML string.

get_yaml_schema
---------------

.. code-block:: python

   from test_pioneer import get_yaml_schema

   schema = get_yaml_schema()

Return the workflow JSON Schema (draft 2020-12) as a new ``dict``. Its ``version`` field is the
schema version. The same schema is published as ``schema/testpioneer.schema.json``.

Command Line Interface
----------------------

.. code-block:: bash

   python -m test_pioneer -e <yaml_file>
   python -m test_pioneer validate <yaml_file>...
   python -m test_pioneer schema

**Arguments:**

- ``-e``, ``--execute_yaml`` -- Path to the YAML file to execute.

**Commands:**

- ``validate [--format {text,json}] [--strict] [--base_dir DIR] [--no_file_check] files...`` --
  Check workflow files without executing them. Exits with status 1 when a file has an error.
  See :doc:`validation`.
- ``schema [-o FILE]`` -- Print the workflow JSON Schema, or write it to ``FILE``.
