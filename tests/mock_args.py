"""Define the MockArgs class, used in several tests"""

from pathlib import Path


# pylint: disable=too-few-public-methods
class MockArgs:
    """A class to mock arguments"""

    def __init__(self, path=None, **kwargs):
        self.path = str(path or ".")
        self.constants_file = "constants.py"
        self.min_length = 3
        self.min_count = 1  # Set low to trigger detection easily
        defaults = {
            "no_local_scope": False,
            "no_numbers": False,
            "no_ints": False,
            "no_floats": False,
            "no_bytes": False,
            "ignore_call": [],
            "exclude": [],
            "ignore_num": [],
            "include_num": [],
            "ignore_str": [],
            "extra_constants": [],
            "naming": "derived",
            "command": "report",
            "report_file": "report.json",
            "apply": False,
        }
        for k, v in defaults.items():
            setattr(self, k, v)
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, "constants_path"):
            self.constants_path = Path(self.path) / self.constants_file
