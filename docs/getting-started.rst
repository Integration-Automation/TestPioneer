Getting Started
===============

Features
--------

- **Multi-type testing** -- GUI, Web, API, and Load/Stress testing via pluggable runners
- **YAML configuration** -- Human-readable test workflows, easy to maintain and version control
- **Parallel execution** -- Run multiple test scripts concurrently with different runners
- **Video recording** -- Built-in test session recording for debugging (requires GUI extras)
- **Process management** -- Launch/terminate external programs with stdout/stderr redirection
- **Cross-platform** -- Windows, macOS, and Linux (Python 3.10+)

Requirements
------------

- Python 3.10 or higher

Installation
------------

Install the base package:

.. code-block:: bash

   pip install test_pioneer

With GUI automation support:

.. code-block:: bash

   pip install test_pioneer[gui]

Quick Start
-----------

Command Line
^^^^^^^^^^^^

.. code-block:: bash

   python -m test_pioneer -e path/to/test.yaml

Python API
^^^^^^^^^^

.. code-block:: python

   from test_pioneer import execute_yaml

   execute_yaml("path/to/test.yaml")

You can also pass a YAML string directly:

.. code-block:: python

   from test_pioneer import execute_yaml

   yaml_content = """
   jobs:
     steps:
       - name: my_test
         run: tests/api_test.json
         with: api-runner
   """
   execute_yaml(yaml_content, yaml_type="String")

Project Template
^^^^^^^^^^^^^^^^

Generate a starter ``.TestPioneer`` directory with a sample YAML file:

.. code-block:: python

   from test_pioneer import create_template_dir

   create_template_dir()

This creates a ``.TestPioneer/`` folder in the current directory containing a sample
YAML workflow file.

IDE Support
-----------

For a visual editing experience, see `PyBreeze <https://github.com/Integration-Automation/PyBreeze>`_.
