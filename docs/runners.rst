Runners
=======

TestPioneer uses a pluggable runner architecture. Each runner handles a specific type
of testing by delegating to a specialized package.

Available Runners
-----------------

.. list-table::
   :header-rows: 1
   :widths: 15 25 60

   * - Runner
     - Package
     - Description
   * - ``gui-runner``
     - `AutoControlGUI <https://github.com/Integration-Automation/AutoControlGUI>`_
     - Desktop GUI automation. Requires ``test_pioneer[gui]`` extras.
   * - ``web-runner``
     - `WebRunner <https://github.com/Integration-Automation/WebRunner>`_
     - Web browser automation using Selenium-based workflows.
   * - ``api-runner``
     - `APITestka <https://github.com/Integration-Automation/APITestka>`_
     - REST API testing with JSON-defined request sequences.
   * - ``load-runner``
     - `LoadDensity <https://github.com/Integration-Automation/LoadDensity>`_
     - Load and stress testing.

Usage
-----

Runners are specified with the ``with`` key in ``run`` and ``run_folder`` steps:

.. code-block:: yaml

   - name: my_web_test
     run: tests/web_test.json
     with: web-runner

For parallel execution, runners are specified as a list:

.. code-block:: yaml

   - name: parallel_tests
     parallel_run:
       runners: ["web-runner", "api-runner"]
       scripts: ["./tests/web.json", "./tests/api.json"]

GUI Runner
----------

The ``gui-runner`` requires an additional dependency that is not installed by default.
Install it via:

.. code-block:: bash

   pip install test_pioneer[gui]

This installs the ``je_auto_control`` package which provides desktop automation
capabilities including mouse/keyboard control and screen recording.

.. note::

   GUI tests require a display environment. In headless CI/CD environments,
   use ``Xvfb`` (X Virtual Framebuffer). See :doc:`docker` for pre-configured
   Docker images.
