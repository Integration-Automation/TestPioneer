from typing import List


class ProcessManager(object):

    def __init__(self):
        super().__init__()
        self.process_list: List = []


process_manager = ProcessManager()
