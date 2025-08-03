from test_pioneer.executor.run.parallel_run import parallel_run

if __name__ == "__main__":
    script_list1 = ["./test/test1.json", "./test/test2.json"]
    runner_list1 = ["gui-runner", "gui-runner"]
    parallel_run({"runners": runner_list1, "scripts": script_list1}, enable_logging=True)
