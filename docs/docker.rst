Docker
======

TestPioneer provides two Dockerfile configurations for running tests in containerized
environments.

Non-GUI Docker Image
--------------------

For API, Load, and Web tests that don't require a display:

.. code-block:: bash

   docker build -f Dockerfile_NonGUI -t testpioneer-nongui .

This image includes:

- Ubuntu 24.04
- Python 3.11 (compiled from source)
- TestPioneer with non-GUI dependencies
- A non-root ``pioneer`` user, which containers run as

GUI Docker Image
----------------

For tests that require GUI automation and screen recording:

.. code-block:: bash

   docker build -f Dockerfile_GUI -t testpioneer-gui .

This image includes everything in the non-GUI image, plus:

- Xvfb (X Virtual Framebuffer)
- Google Chrome + ChromeDriver
- GUI libraries (GTK, OpenGL, X11)
- ``je_auto_control`` for GUI automation

Running Tests in Docker
-----------------------

Non-GUI example:

.. code-block:: bash

   docker run --rm -v $(pwd)/tests:/app/tests testpioneer-nongui \
     python3.11 -m test_pioneer -e /app/tests/api_test.yaml

GUI example (with virtual display):

.. code-block:: bash

   docker run --rm -v $(pwd)/tests:/app/tests testpioneer-gui \
     bash -c "Xvfb :99 -screen 0 1920x1080x24 & export DISPLAY=:99 && \
     python3.11 -m test_pioneer -e /app/tests/gui_test.yaml"

Self-test Images
----------------

Each Dockerfile has a second stage, ``selftest``, that adds the bundled sample
(``docker_non_gui_test/`` or ``docker_gui_test/``) and runs it as the default command.
Use it to check that an image works before pointing it at your own tests:

.. code-block:: bash

   docker build -f Dockerfile_NonGUI --target selftest -t testpioneer-nongui-selftest .
   docker run --rm testpioneer-nongui-selftest

   docker build -f Dockerfile_GUI --target selftest -t testpioneer-gui-selftest .
   docker run --rm testpioneer-gui-selftest

The GUI self-test starts Xvfb on display ``:99`` when the container starts. A build
without ``--target`` produces the plain base image described above.

CI/CD Integration
-----------------

The project includes GitHub Actions CI that runs both unit and integration tests on
Python 3.10, 3.11, and 3.12. See ``.github/workflows/ci.yml`` for the full configuration.

Test artifacts (videos and logs) are uploaded automatically on each CI run.
