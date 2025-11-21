"""
Unit tests for the refactor module.
"""

from unittest import mock
from pathlib import Path
import pytest
from constantipy.refactor import (
    process_report,
    find_insertion_line,
    get_import_module_path,
)
from constantipy.exceptions import ConstantipyError
from constantipy.common import Config
from .mock_args import MockArgs

# --- Insertion Logic Tests ---


def test_find_insertion_line_shebang():
    """Test insertion line calculation with a shebang present."""
    code = "#!/usr/bin/env python\nx = 1"
    assert find_insertion_line(code) == 1


def test_find_insertion_line_imports():
    """Test insertion line calculation with existing imports."""
    code = "import os\nimport sys\n\nx = 1"
    # Should insert after imports (line 2)
    assert find_insertion_line(code) == 2


def test_find_insertion_line_docstring():
    """Test insertion line calculation with a docstring and imports."""
    code = '"""Docstring"""\nimport os'
    # Should be after import (line 2)
    assert find_insertion_line(code) == 2


def test_find_insertion_line_docstring_only():
    """Test insertion line calculation with only a docstring."""
    code = '"""Docstring"""\n'
    # Should be after docstring (line 1)
    assert find_insertion_line(code) == 1


def test_get_import_module_path_error():
    """Test fallback when relative path fails."""
    # /tmp/file.py relative to /etc/ will raise ValueError
    res = get_import_module_path("/tmp/file.py", Path("/etc"))
    assert res == "file"


# --- Report Processing Tests ---


def test_process_report_file_read_error(tmp_path, capsys, simple_report_maker):
    """Test that file read errors during refactor are handled gracefully."""
    bad_file = tmp_path / "locked_file.py"
    bad_file.write_text("x='foo'", encoding="utf-8")

    args = MockArgs(path=tmp_path)
    config = Config(args)

    report = simple_report_maker(bad_file, "CONST_FOO", "foo")

    with mock.patch("builtins.open", side_effect=OSError("Permission denied")):
        process_report(config, report, apply=True)

    captured = capsys.readouterr()
    assert f"Error reading {bad_file}" in captured.err


def test_process_report_malformed_report(tmp_path):
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


def test_process_report_missing_key(tmp_path):
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


def test_process_report_append_newline(tmp_path, simple_report_maker):
    """Test that process_report adds a newline if the constants file lacks one."""
    d = tmp_path
    const_file = d / "constants.py"
    with open(const_file, "wb") as f:
        f.write(b"EXISTING=1")

    args = MockArgs(path=d)
    config = Config(args)

    # Use fixture
    report = simple_report_maker(const_file, "NEW_CONST", "val")

    # --- FIX: Ensure it is treated as global AND has no occurrences to refactor ---
    report["NEW_CONST"]["scope"] = "global"
    report["NEW_CONST"][
        "occurrences"
    ] = []  # Critical: Don't try to "replace" text in constants.py

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
