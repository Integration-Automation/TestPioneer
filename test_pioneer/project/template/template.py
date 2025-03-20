template_1_str: str = \
"""
# log file path
pioneer_log: "test_pioneer.log"
# test start
jobs:
    # test steps
    steps:
        # use gui runner to run gui test
        - name: run_test_script_1
          run: test/test1.json
          with: gui-runner
        # use web runner to run gui test
        - name: run_test_script_2
          run: test/test2.json
          with: web-runner
        # use api runner to run gui test  
        - name: run_test_script_3
          run: test/test3.json
          with: api-runner
        # use load runner to run gui test
        - name: run_test_script_4
          run: test/test4.json
          with: load-runner
        # open program and redirect stdout and stderr to path
        - name: open_test_program
          open_program: test_path/test_file
          redirect_stdout: "test_std.log"
          redirect_stderr: "test_err.log"
        # stop 5 sec  s
        - name: wait_seconds
          wait: 5
        # use default browser to open url 
        - name: open_test_url
          open_url: https://www.google.com
        # close program that open use {name}
        - name: close_test_program
          close_program: open_test_program

"""
