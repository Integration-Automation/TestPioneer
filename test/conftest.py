import pytest

from test_pioneer.process.process_manager import process_manager_instance
from test_pioneer.report.repeats import in_process_records


@pytest.fixture(autouse=True)
def reset_process_manager():
    """Reset global process manager state between tests."""
    process_manager_instance.name_set.clear()
    process_manager_instance.process_dict.clear()
    yield
    process_manager_instance.name_set.clear()
    process_manager_instance.process_dict.clear()


@pytest.fixture(autouse=True)
def forget_reported_records():
    """Start each test as a fresh process would: no runner has reported anything yet."""
    in_process_records.reset()


@pytest.fixture(autouse=True)
def run_in_a_scratch_directory(tmp_path, monkeypatch):
    """Run each test in its own empty directory.

    ``execute_yaml`` writes artifacts below the working directory, which must not be the checkout.
    """
    monkeypatch.chdir(tmp_path)
