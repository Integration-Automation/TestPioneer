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

- Ubuntu (latest)
- Python 3.11 (compiled from source)
- TestPioneer with non-GUI dependencies

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

CI/CD Integration
-----------------

The project includes GitHub Actions CI that runs both unit and integration tests on
Python 3.10, 3.11, and 3.12. See ``.github/workflows/ci.yml`` for the full configuration.

Test artifacts (videos and logs) are uploaded automatically on each CI run.
