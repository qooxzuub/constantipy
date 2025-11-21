"""
Unit tests for the CLI module.
"""

import sys
import json
import io
from unittest.mock import patch
import pytest
from constantipy.exceptions import ConstantipyError
from constantipy.cli import main, handle_validate
from constantipy.common import Config
from .mock_args import MockArgs


def test_main_report_command(tmp_path, capsys):
    """Test 'report' subcommand outputs JSON to stdout."""
    d = tmp_path
    # Create a file with a string > min_length(4)
    (d / "t.py").write_text('x="magic_string"\ny="magic_string"', encoding="utf-8")

    # Argparse strict order: global flags BEFORE subcommand
    test_args = ["constantipy", "--path", str(d), "report"]

    with patch.object(sys, "argv", test_args):
        main()

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    # Expect heuristic name (no STR_ prefix for valid identifiers)
    assert "MAGIC_STRING" in data


def test_main_refactor_stdin(tmp_path):
    """Test 'refactor' subcommand reading from stdin."""
    d = tmp_path
    t_file = d / "t.py"
    t_file.write_text('x="refactor_me"', encoding="utf-8")

    report_data = {
        "STR_REFACTOR_ME": {
            "value": "refactor_me",
            "is_new": True,
            "scope": "local",
            "source_path": str(t_file),
            "occurrences": [
                {
                    "filepath": str(t_file),
                    "lineno": 1,
                    "col_offset": 2,
                    "end_lineno": 1,
                    "end_col_offset": 15,
                }
            ],
        }
    }
    stdin_input = json.dumps(report_data)
    test_args = ["constantipy", "--path", str(d), "refactor", "--apply"]

    with patch.object(sys, "argv", test_args):
        with patch("sys.stdin", io.StringIO(stdin_input)):
            main()

    assert "STR_REFACTOR_ME" in t_file.read_text(encoding="utf-8")


def test_main_implicit_flow_apply(tmp_path):
    """Test implicit flow (no subcommand) with --apply."""
    d = tmp_path
    (d / "t.py").write_text('x="magic"\ny="magic"', encoding="utf-8")

    test_args = ["constantipy", "--path", str(d), "--apply", "--min-count", "1"]
    with patch.object(sys, "argv", test_args):
        main()

    assert "MAGIC" in (d / "t.py").read_text(encoding="utf-8")


def test_apply_report_preview_mode(tmp_path, capsys):
    """Test implicit flow without --apply (preview mode)."""
    d = tmp_path
    (d / "t.py").write_text('x="preview"\ny="preview"', encoding="utf-8")

    test_args = ["constantipy", "--path", str(d), "--min-count", "1"]
    with patch.object(sys, "argv", test_args):
        main()

    captured = capsys.readouterr()
    assert "PREVIEW" in captured.out
    # File should NOT be modified
    assert '"preview"' in (d / "t.py").read_text(encoding="utf-8")


def test_main_invalid_json(capsys):
    """Test that invalid JSON input is properly handled."""
    bad_json = "{ bad json"
    test_args = ["constantipy", "refactor"]

    with patch.object(sys, "argv", test_args):
        with patch("sys.stdin", io.StringIO(bad_json)):
            with pytest.raises(ConstantipyError) as err:
                main()
            assert "Run was not successful" in str(err.value)

    captured = capsys.readouterr()
    assert "Invalid JSON" in captured.err


def test_main_report_invalid_config(tmp_path):
    """Test invalid config passed to report command."""
    d = tmp_path
    # Force min-length to 0 to trigger ValueError in Config
    test_args = ["constantipy", "--path", str(d), "--min-length", "0", "report"]

    with patch.object(sys, "argv", test_args):
        with pytest.raises(ConstantipyError) as exc:
            main()
        assert "Invalid configuration" in str(exc.value)


def test_validate_mode(tmp_path, capsys):
    """Test valid validation."""
    d = tmp_path
    report = d / "report.json"
    valid_data = {
        "CONST_1": {"value": "foo", "occurrences": [], "is_new": True, "scope": "local"}
    }
    report.write_text(json.dumps(valid_data), encoding="utf-8")

    args = MockArgs(path=d, report_file=str(report))
    config = Config(args)

    assert handle_validate(config) is True
    captured = capsys.readouterr()
    assert "Valid Report" in captured.err


def test_validate_bad_json(tmp_path, capsys):
    """Test validation with bad JSON."""
    d = tmp_path
    report = d / "bad.json"
    report.write_text("{bad", encoding="utf-8")

    args = MockArgs(path=d, report_file=str(report))
    config = Config(args)

    assert handle_validate(config) is False
    captured = capsys.readouterr()
    assert "Invalid JSON syntax" in captured.err


def test_handle_validate_errors_missing_file(tmp_path, capsys):
    """Test validation with missing file."""
    d = tmp_path
    args = MockArgs(path=d, report_file="missing.json")
    config = Config(args)
    assert handle_validate(config) is False
    captured = capsys.readouterr()
    assert "Report file not found" in captured.err


def test_handle_validate_errors_schema(tmp_path, capsys):
    """Test validation schema errors."""
    d = tmp_path
    bad_schema = d / "schema.json"
    bad_schema.write_text('{"C1": {}}', encoding="utf-8")
    args = MockArgs(path=d, report_file=str(bad_schema))
    config = Config(args)
    assert handle_validate(config) is False
    captured = capsys.readouterr()
    assert "Validation failed" in captured.err
