import sys


def pytest_ignore_collect(path, config):
    # Avoid collecting this file in Python >= 3.13
    if path.basename == "test_client.py" and sys.version_info >= (3, 13):
        return True
    return False
