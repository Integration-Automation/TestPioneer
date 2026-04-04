API Reference
=============

TestPioneer exposes two public functions from its top-level package.

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

Command Line Interface
----------------------

.. code-block:: bash

   python -m test_pioneer -e <yaml_file>

**Arguments:**

- ``-e``, ``--execute_yaml`` -- Path to the YAML file to execute.
