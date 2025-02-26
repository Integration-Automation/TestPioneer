from __future__ import annotations

from typing import Set, Dict, TYPE_CHECKING

from test_pioneer.logging.loggin_instance import test_pioneer_logger

if TYPE_CHECKING:
    from test_pioneer.process.execute_process import ExecuteProcess


class ProcessManager(object):

    def __init__(self):
        self.name_set: Set[str] = set()
        self.process_dict: Dict[str, ExecuteProcess] = dict()

    def close_process(self, job_name):
        execute_process = self.process_dict.get(job_name, None)
        if execute_process is None:
            test_pioneer_logger.error(f"Process not found {job_name}")
        else:
            execute_process.exit_program()


process_manager_instance = ProcessManager()
