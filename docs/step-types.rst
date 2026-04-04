Step Types
==========

Each step in the YAML workflow is identified by its action key. Below is a detailed
reference of all available step types.

run
---

Execute a single JSON test script using a specified runner.

.. code-block:: yaml

   - name: my_test
     run: tests/api_test.json
     with: api-runner

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Required
     - Description
   * - ``run``
     - Yes
     - Path to the JSON test file (relative to current working directory).
   * - ``with``
     - Yes
     - Runner to use: ``gui-runner``, ``web-runner``, ``api-runner``, or ``load-runner``.

run_folder
----------

Execute all JSON files inside a specified folder using a single runner.

.. code-block:: yaml

   - name: run_all_tests
     run_folder: tests/regression/
     with: web-runner

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Required
     - Description
   * - ``run_folder``
     - Yes
     - Path to the folder containing JSON test files.
   * - ``with``
     - Yes
     - Runner to use.

parallel_run
------------

Run multiple scripts concurrently, each with its own runner. Scripts are launched as
separate sub-processes and monitored until all complete.

.. code-block:: yaml

   - name: parallel_tests
     parallel_run:
       runners: ["web-runner", "api-runner"]
       scripts: ["./tests/web.json", "./tests/api.json"]
       executor_path: /usr/bin/python3    # optional

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Required
     - Description
   * - ``runners``
     - Yes
     - List of runner types. Must match the length of ``scripts``.
   * - ``scripts``
     - Yes
     - List of script file paths. Each script runs with its corresponding runner.
   * - ``executor_path``
     - No
     - Custom Python executable path. Defaults to ``sys.executable``.

wait
----

Pause execution for a specified number of seconds.

.. code-block:: yaml

   - name: wait_5s
     wait: 5

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Required
     - Description
   * - ``wait``
     - Yes
     - Number of seconds to wait (integer).

open_url
--------

Open a URL in the system's default web browser.

.. code-block:: yaml

   - name: open_docs
     open_url: https://example.com
     url_open_method: open_new_tab

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Required
     - Description
   * - ``open_url``
     - Yes
     - The URL to open.
   * - ``url_open_method``
     - No
     - Method: ``open`` (default), ``open_new``, or ``open_new_tab``.

download_file
-------------

Download a file from a URL to a local path.

.. code-block:: yaml

   - name: download_asset
     download_file: https://example.com/asset.zip
     file_path: ./downloads/asset.zip

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Required
     - Description
   * - ``download_file``
     - Yes
     - URL of the file to download.
   * - ``file_path``
     - Yes
     - Local path to save the downloaded file.

open_program
------------

Launch an external program. The process is registered by step name and can be closed
later using ``close_program``.

.. code-block:: yaml

   - name: launch_server
     open_program: ./server.exe
     redirect_stdout: server_out.log
     redirect_stderr: server_err.log

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Required
     - Description
   * - ``open_program``
     - Yes
     - Path or command to the program to launch.
   * - ``redirect_stdout``
     - No
     - File path to redirect standard output.
   * - ``redirect_stderr``
     - No
     - File path to redirect standard error.

close_program
-------------

Terminate a program that was previously launched by ``open_program``. Uses the step
``name`` of the ``open_program`` step as the identifier.

.. code-block:: yaml

   - name: stop_server
     close_program: launch_server

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Required
     - Description
   * - ``close_program``
     - Yes
     - The ``name`` of the ``open_program`` step to close.

unzip_zipfile
-------------

Extract a zip archive.

.. code-block:: yaml

   - name: extract_archive
     unzip_zipfile: true
     zip_file_path: ./downloads/asset.zip
     extract_path: ./assets/
     password: secret123

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Required
     - Description
   * - ``zip_file_path``
     - Yes
     - Path to the zip file.
   * - ``extract_path``
     - No
     - Directory to extract into. Defaults to current directory.
   * - ``password``
     - No
     - Password for encrypted zip files.
