import pytest

from test_pioneer.process.process_manager import process_manager_instance


@pytest.fixture(autouse=True)
def reset_process_manager():
    """Reset global process manager state between tests."""
    process_manager_instance.name_set.clear()
    process_manager_instance.process_dict.clear()
    yield
    process_manager_instance.name_set.clear()
    process_manager_instance.process_dict.clear()
