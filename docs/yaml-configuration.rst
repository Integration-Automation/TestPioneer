YAML Configuration
==================

TestPioneer uses YAML files to define test workflows. Each YAML file describes a
sequence of steps to execute.

File Structure
--------------

.. code-block:: yaml

   pioneer_log: "test_pioneer.log"       # Optional: log file path
   recording_path: "test_video"          # Optional: video recording output (requires GUI extras)
   jobs:
     steps:
       - name: step_name
         # ... step configuration

Top-Level Keys
--------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Key
     - Required
     - Description
   * - ``pioneer_log``
     - No
     - Path to the log file. When set, all step execution logs are written to this file.
   * - ``recording_path``
     - No
     - Path for video recording output (without extension). Requires ``test_pioneer[gui]``.
   * - ``jobs``
     - Yes
     - Container for the ``steps`` list.

Steps
-----

Each step must have a unique ``name`` key. The step type is determined by which action
key is present (``run``, ``wait``, ``open_url``, etc.).

.. code-block:: yaml

   jobs:
     steps:
       - name: run_api_test
         run: tests/api_test.json
         with: api-runner

       - name: wait_for_service
         wait: 5

       - name: run_web_test
         run: tests/web_test.json
         with: web-runner

       - name: open_docs
         open_url: https://example.com
         url_open_method: open_new_tab

       - name: launch_app
         open_program: path/to/program
         redirect_stdout: output.log
         redirect_stderr: errors.log

       - name: parallel_tests
         parallel_run:
           runners: ["web-runner", "api-runner"]
           scripts: ["./tests/web.json", "./tests/api.json"]

Rules
-----

- Every step **must** have a unique ``name``.
- Duplicate step names cause execution to abort.
- Steps are executed sequentially in the order they appear, except for
  ``parallel_run`` which launches sub-processes concurrently.
- If any step fails, execution stops immediately.

Full Example
------------

.. code-block:: yaml

   pioneer_log: "test_pioneer.log"
   recording_path: "test_video"
   jobs:
     steps:
       # Run an API test
       - name: run_api_test
         run: tests/api_test.json
         with: api-runner

       # Wait 5 seconds
       - name: wait_for_service
         wait: 5

       # Run a web test
       - name: run_web_test
         run: tests/web_test.json
         with: web-runner

       # Open a URL in the browser
       - name: open_docs
         open_url: https://example.com
         url_open_method: open_new_tab

       # Launch an external program
       - name: launch_app
         open_program: path/to/program
         redirect_stdout: output.log
         redirect_stderr: errors.log

       # Close the program launched earlier
       - name: close_launched_app
         close_program: launch_app

       # Run tests in parallel
       - name: parallel_tests
         parallel_run:
           runners: ["web-runner", "api-runner"]
           scripts: ["./tests/web.json", "./tests/api.json"]

       # Run all JSON files in a folder
       - name: run_all_in_folder
         run_folder: tests/regression/
         with: web-runner

       # Download a file
       - name: download_asset
         download_file: https://example.com/asset.zip
         file_path: ./downloads/asset.zip

       # Unzip
       - name: extract_asset
         unzip_zipfile: true
         zip_file_path: ./downloads/asset.zip
         extract_path: ./assets/
