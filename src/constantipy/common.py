"""
Shared configuration, constants, and types for Constantipy.
"""

import argparse
import sys
from pathlib import Path
from typing import Any, List, Set, Union

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    "env",
    "node_modules",
    ".idea",
    ".vscode",
    "build",
    "dist",
    ".tox",
    ".eggs",
    "tests",
    "test",
    "docs",
}

REGEX_FUNCTIONS = {
    "compile",
    "search",
    "match",
    "fullmatch",
    "split",
    "findall",
    "finditer",
    "sub",
    "subn",
}

TRIVIAL_NUMBERS: Set[Union[int, float]] = {0, 1, 2, -1}


def eprint(*args: Any, **kwargs: Any) -> None:
    """Prints to stderr to avoid polluting stdout (which is used for piping)."""
    print(*args, file=sys.stderr, **kwargs)


class Config:
    """
    Holds configuration state for the refactoring session.
    """

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-few-public-methods
    def __init__(self, args: argparse.Namespace):
        # Base paths
        self.root = Path(args.path).resolve()
        self.target_file = args.constants_file
        self.constants_path = self.root / self.target_file

        # CLI State (Restored)
        # We check 'report_file' (default) or allow fallback
        self.report_file = getattr(args, "report_file", "constantipy_report.json")

        # We check 'command' (new CLI) -> 'mode' (legacy/tests) -> None
        self.mode = getattr(args, "command", getattr(args, "mode", None))

        # Scanning thresholds
        self.min_len = getattr(args, "min_length", 4)
        self.min_count = getattr(args, "min_count", 2)
        self.naming_strategy = getattr(args, "naming", "derived")

        if self.min_len <= 0:
            raise ValueError("Invalid argument for min_length: must be greater than 0.")
        if self.min_count <= 0:
            raise ValueError("Invalid argument for min_count: must be greater than 0.")

        # Scope and Type controls
        self.use_local_scope = not getattr(args, "no_local_scope", False)

        no_nums = getattr(args, "no_numbers", False)
        self.scan_ints = not getattr(args, "no_ints", False) and not no_nums
        self.scan_floats = not getattr(args, "no_floats", False) and not no_nums
        self.scan_bytes = not getattr(args, "no_bytes", False)

        # Ignores
        self.ignored_calls = set(getattr(args, "ignore_call", []) or [])

        self.excluded_dirs = IGNORED_DIRS.copy()
        if getattr(args, "exclude", None):
            self.excluded_dirs.update(args.exclude)

        # Ignored Numbers logic
        self.ignored_numbers: Set[Union[int, float]] = TRIVIAL_NUMBERS.copy()
        self._update_ignored_numbers(
            getattr(args, "ignore_num", []), getattr(args, "include_num", [])
        )

        self.ignored_strings = set(getattr(args, "ignore_str", []) or [])

        # Extra files
        self.extra_files = []
        if getattr(args, "extra_constants", None):
            for f in args.extra_constants:
                self.extra_files.append(Path(f))

    def _update_ignored_numbers(
        self, ignore_list: List[str], include_list: List[str]
    ) -> None:
        """Helper to update the ignored_numbers set based on string arguments."""
        if ignore_list:
            for n in ignore_list:
                if "." in n:
                    self.ignored_numbers.add(float(n))
                else:
                    self.ignored_numbers.add(int(n))

        if include_list:
            for n in include_list:
                if "." in n:
                    self.ignored_numbers.discard(float(n))
                else:
                    self.ignored_numbers.discard(int(n))
