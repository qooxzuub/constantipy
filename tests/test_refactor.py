import pytest
import ast
from unittest import mock
from pathlib import Path
from constantipy.refactor import (
    process_report,
    find_insertion_line,
    get_import_module_path,
)
from constantipy.exceptions import ConstantipyError
from constantipy.common import Config


class MockArgs:
    """Helper for creating config objects."""

    def __init__(self, path, **kwargs):
        self.path = str(path)
        self.constants_file = "constants.py"
        self.min_length = 3
        self.min_count = 1
        # Set defaults
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
        }
        for k, v in defaults.items():
            setattr(self, k, v)
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, "constants_path"):
            self.constants_path = Path(self.path) / self.constants_file


# --- Insertion Logic Tests ---


def test_find_insertion_line_shebang():
    code = "#!/usr/bin/env python\nx = 1"
    assert find_insertion_line(code) == 1


def test_find_insertion_line_imports():
    code = "import os\nimport sys\n\nx = 1"
    # Should insert after imports (line 2)
    assert find_insertion_line(code) == 2


def test_find_insertion_line_docstring():
    code = '"""Docstring"""\nimport os'
    # Should be after import (line 2)
    assert find_insertion_line(code) == 2


def test_find_insertion_line_docstring_only():
    code = '"""Docstring"""\n'
    # Should be after docstring (line 1)
    assert find_insertion_line(code) == 1


def test_get_import_module_path_error():
    """Test fallback when relative path fails."""
    # /tmp/file.py relative to /etc/ will raise ValueError
    res = get_import_module_path("/tmp/file.py", Path("/etc"))
    assert res == "file"


# --- Report Processing Tests ---


def test_process_report_file_read_error(tmp_path, capsys):
    """Test that file read errors during refactor are handled gracefully."""
    bad_file = tmp_path / "locked_file.py"
    bad_file.write_text("x='foo'", encoding="utf-8")

    args = MockArgs(path=tmp_path)
    config = Config(args)

    report = {
        "CONST_FOO": {
            "value": "foo",
            "is_new": True,
            "scope": "local",
            "source_path": str(bad_file),
            "occurrences": [
                {
                    "filepath": str(bad_file),
                    "lineno": 1,
                    "col_offset": 2,
                    "end_lineno": 1,
                    "end_col_offset": 5,
                }
            ],
        }
    }

    with mock.patch("builtins.open", side_effect=OSError("Permission denied")):
        process_report(config, report, apply=True)

    captured = capsys.readouterr()
    assert f"Error reading {bad_file}" in captured.err


def test_process_report_malformed_report(tmp_path, capsys):
    """Test that malformed reports are handled correctly."""
    args = MockArgs(path=tmp_path)
    config = Config(args)

    report = {
        "CONST_FOO": {
            "is_new": True,
            "scope": "local",
            "source_path": "foo.py",
            "occurrences": [{"filepath": "foo.py", "lineno": 1, "col_offset": 2}],
            # Missing 'value'
        }
    }

    with mock.patch("builtins.open", side_effect=OSError("Permission denied")):
        with pytest.raises(ConstantipyError, match="Malformed report"):
            process_report(config, report, apply=True)


def test_process_report_missing_key(tmp_path, capsys):
    """Test that missing keys in the report raise an appropriate error."""
    args = MockArgs(path=tmp_path)
    config = Config(args)

    report = {
        "CONST_FOO": {
            "value": "foo",
            "is_new": True,
            "scope": "local",
            "source_path": "foo.py",
            # Missing 'occurrences'
        }
    }

    with mock.patch("builtins.open", side_effect=OSError("Permission denied")):
        with pytest.raises(ConstantipyError, match="Malformed report"):
            process_report(config, report, apply=True)


def test_process_report_append_newline(tmp_path):
    """Test that process_report adds a newline if the constants file lacks one."""
    d = tmp_path
    const_file = d / "constants.py"
    with open(const_file, "wb") as f:
        f.write(b"EXISTING=1")

    args = MockArgs(path=d)
    config = Config(args)

    report = {
        "NEW_CONST": {
            "value": "val",
            "is_new": True,
            "scope": "global",
            "source_path": str(const_file),
            "occurrences": [],
        }
    }

    process_report(config, report, apply=True)

    content = const_file.read_text(encoding="utf-8")
    assert "EXISTING=1\nNEW_CONST = 'val'\n" in content


# --- Multiline Replacement Tests ---


def test_multiline_replacement_list(tmp_path):
    """Test replacing a multi-line list definition."""
    f = tmp_path / "multiline.py"
    content = "x = [\n    1,\n    2\n]\n"
    f.write_text(content, encoding="utf-8")

    report = {
        "CONST_LIST": {
            "value": [1, 2],
            "is_new": True,
            "scope": "local",
            "source_path": str(f),
            "occurrences": [
                {
                    "filepath": str(f),
                    "lineno": 1,
                    "col_offset": 4,
                    "end_lineno": 4,
                    "end_col_offset": 1,
                }
            ],
        }
    }

    args = MockArgs(path=tmp_path)
    config = Config(args)
    process_report(config, report, apply=True)

    new_content = f.read_text(encoding="utf-8")
    assert "x = CONST_LIST" in new_content
    assert "CONST_LIST = [1, 2]" in new_content
    assert "    1," not in new_content


def test_multiline_replacement_dict(tmp_path):
    """Test replacing a multi-line dictionary."""
    f = tmp_path / "multiline_dict.py"
    content = "d = {\n  'a': 1,\n  'b': 2\n}"
    f.write_text(content, encoding="utf-8")

    report = {
        "CONST_DICT": {
            "value": {"a": 1, "b": 2},
            "is_new": True,
            "scope": "local",
            "source_path": str(f),
            "occurrences": [
                {
                    "filepath": str(f),
                    "lineno": 1,
                    "col_offset": 4,
                    "end_lineno": 4,
                    "end_col_offset": 1,
                }
            ],
        }
    }

    args = MockArgs(path=tmp_path)
    config = Config(args)
    process_report(config, report, apply=True)

    new_content = f.read_text(encoding="utf-8")
    assert "d = CONST_DICT" in new_content
    assert "CONST_DICT = {'a': 1, 'b': 2}" in new_content
