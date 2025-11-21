"""
Unit tests for the scanner module.
"""
from constantipy.scanner import scan_file
from constantipy.common import Config
from .mock_args import MockArgs


# --- Basic Scanner Tests ---


def test_scan_file_empty_file(tmp_path):
    """Test that scan_file handles empty files gracefully."""
    empty_file = tmp_path / "empty.py"
    empty_file.write_text("", encoding="utf-8")

    args = MockArgs(path=tmp_path)
    found, names = scan_file(empty_file, Config(args))

    assert len(found) == 0  # No literals should be found
    assert len(names) == 0  # No top-level names should be found


def test_scan_file_with_syntax_error(tmp_path):
    """Ensure scan_file skips files with syntax errors."""
    bad_file = tmp_path / "bad_syntax.py"
    bad_file.write_text(
        "def foo(:", encoding="utf-8"
    )  # Syntax error in function definition

    args = MockArgs(path=tmp_path)
    found, names = scan_file(bad_file, Config(args))

    assert len(found) == 0  # No literals should be found
    assert len(names) == 0  # No top-level names should be found


def test_scan_file_with_large_file(tmp_path):
    """Test that scan_file handles large files without memory issues."""
    large_file = tmp_path / "large_file.py"
    large_content = "x = 'some_large_string'\n" * 10000
    large_file.write_text(large_content, encoding="utf-8")

    args = MockArgs(path=tmp_path)
    found, names = scan_file(large_file, Config(args))

    assert len(found) > 0  # At least one constant should be found
    assert len(names) > 0  # There should be at least one top-level name


def test_scan_file_with_comments_only(tmp_path):
    """Test that scan_file correctly handles files with only comments."""
    comment_file = tmp_path / "comments_only.py"
    comment_content = "# This is a comment\n# Another comment"
    comment_file.write_text(comment_content, encoding="utf-8")

    args = MockArgs(path=tmp_path)
    found, names = scan_file(comment_file, Config(args))

    assert len(found) == 0  # No literals should be found
    assert len(names) == 0  # No top-level names should be found


# --- Advanced Scanner Tests ---


def test_scanner_imports(tmp_path):
    """Test collection of top-level names from imports."""
    f = tmp_path / "imports.py"
    f.write_text(
        "import os\nfrom sys import argv\nimport numpy as np", encoding="utf-8"
    )

    args = MockArgs(path=tmp_path)
    _, names = scan_file(f, Config(args))

    assert "os" in names
    assert "argv" in names
    assert "np" in names


def test_scanner_complex_calls(tmp_path):
    """Test deep attribute calls for ignore check."""
    f = tmp_path / "complex_call.py"
    # If we ignore 'logging.info', the arg 'ignored_msg' should be skipped
    f.write_text('import logging\nlogging.info("ignored_msg")', encoding="utf-8")

    args = MockArgs(path=tmp_path, ignore_call=["logging.info"])
    found, _ = scan_file(f, Config(args))

    values = [x["value"] for x in found]
    assert "ignored_msg" not in values


def test_scanner_async_and_class_docstrings(tmp_path):
    """Test scanning of async functions and classes."""
    f = tmp_path / "structures.py"
    content = '''
class MyClass:
    """Class Doc"""
    x = "class_var"

async def my_async():
    """Async Doc"""
    y = "async_var"
'''
    f.write_text(content, encoding="utf-8")
    args = MockArgs(path=tmp_path)
    found, _ = scan_file(f, Config(args))

    values = [x["value"] for x in found]
    # Docstrings are filtered by _mark_docstring logic
    assert "Class Doc" not in values
    assert "Async Doc" not in values
    # Body vars should be found
    assert "class_var" in values
    assert "async_var" in values


def test_scanner_f_strings(tmp_path):
    """Test that f-strings are visited but ignored."""
    f = tmp_path / "fstr.py"
    # 'val ' inside f-string is a Constant, but visit_JoinedStr does 'pass'
    f.write_text('x=1\ns = f"val {x}"', encoding="utf-8")

    args = MockArgs(path=tmp_path)
    found, _ = scan_file(f, Config(args))

    values = [x["value"] for x in found]
    assert "val " not in values


def test_scanner_regex_context(tmp_path):
    """Test regex argument detection."""
    f = tmp_path / "regex.py"
    f.write_text('import re\nre.compile("regex_pattern")', encoding="utf-8")

    args = MockArgs(path=tmp_path)
    found, _ = scan_file(f, Config(args))

    assert len(found) == 1
    assert found[0]["value"] == "regex_pattern"
    assert found[0]["is_regex_arg"] is True


def test_scanner_string_filtering(tmp_path):
    """Test min_len and ignored_strings."""
    f = tmp_path / "strs.py"
    f.write_text('a = "short"\nb = "ignored"', encoding="utf-8")

    # "short" is 5 chars. min_length=6 should skip it.
    args = MockArgs(path=tmp_path, min_length=6, ignore_str=["ignored"])
    found, _ = scan_file(f, Config(args))

    assert len(found) == 0


def test_scanner_numeric_filtering(tmp_path):
    """Test filtering of ints."""
    f = tmp_path / "nums.py"
    f.write_text("a = 10\nb = 30", encoding="utf-8")

    # 1. Test no_ints
    args = MockArgs(path=tmp_path, no_ints=True, scan_ints=False)
    found, _ = scan_file(f, Config(args))
    assert len(found) == 0

    # 2. Test ignored_numbers (pass as string because Config parses them)
    args2 = MockArgs(path=tmp_path, ignore_num=["30"])
    found2, _ = scan_file(f, Config(args2))
    values2 = [x["value"] for x in found2]
    assert 30 not in values2
    assert 10 in values2


def test_scanner_float_filtering(tmp_path):
    """Test filtering of floats."""
    f = tmp_path / "floats.py"
    f.write_text("a = 1.1\nb = 2.2", encoding="utf-8")

    # Test no_floats
    args = MockArgs(path=tmp_path, no_floats=True, scan_floats=False)
    found, _ = scan_file(f, Config(args))
    assert len(found) == 0

    # Test ignore specific float
    args2 = MockArgs(path=tmp_path, ignore_num=["1.1"])
    found2, _ = scan_file(f, Config(args2))
    values2 = [x["value"] for x in found2]
    assert 1.1 not in values2
    assert 2.2 in values2


def test_scanner_bytes_short(tmp_path):
    """Test short bytes filtering."""
    f = tmp_path / "bytes.py"
    f.write_text('b = b"12"', encoding="utf-8")

    # min_length=3, so b"12" (len 2) should be skipped
    args = MockArgs(path=tmp_path, min_length=3, scan_bytes=True)
    found, _ = scan_file(f, Config(args))
    assert len(found) == 0


def test_scanner_ignores_docstrings(tmp_path):
    """Test that docstrings are not scanned as constants."""
    d = tmp_path
    f = d / "docs.py"
    f.write_text(
        '"""Module Doc"""\ndef func():\n    """Func Doc"""\n    pass', encoding="utf-8"
    )

    args = MockArgs(path=d)
    config = Config(args)

    found, _ = scan_file(f, config)
    # Should be empty because both strings are docstrings
    assert not found


def test_scanner_ignored_calls(tmp_path):
    """Test that arguments to ignored calls are skipped."""
    d = tmp_path
    f = d / "calls.py"
    f.write_text('print("ignored")\nother("kept")', encoding="utf-8")

    args = MockArgs(path=d, ignore_call=["print"])
    config = Config(args)

    found, _ = scan_file(f, config)
    values = [x["value"] for x in found]
    assert "ignored" not in values
    assert "kept" in values


def test_scanner_bytes_handling(tmp_path):
    """Test scanning of bytes literals."""
    d = tmp_path
    f = d / "bytes.py"
    f.write_text('x = b"12345"', encoding="utf-8")

    args = MockArgs(path=d, scan_bytes=True)
    config = Config(args)

    found, _ = scan_file(f, config)
    assert len(found) == 1
    assert found[0]["value"] == b"12345"
    assert found[0]["type"] == "bytes"
