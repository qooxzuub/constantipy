"""
Tests for complex workflows: diff generation, idempotency, and incremental updates.
"""

from unittest import mock
from constantipy.common import Config
from constantipy.refactor import process_report
from constantipy.cli import main
from .mock_args import MockArgs


# (1) Test for files without newlines at EOF
def test_diff_no_trailing_newline(tmp_path, capsys, simple_report_maker):
    """Test diff generation for a file explicitly missing a trailing newline."""
    d = tmp_path
    f = d / "no_newline.py"
    # Write content WITHOUT a trailing \n
    f.write_bytes(b"x = 'magic'")

    args = MockArgs(path=d)
    config = Config(args)

    # Use fixture
    report = simple_report_maker(f, "MAGIC", "magic")

    process_report(config, report, apply=False)

    captured = capsys.readouterr()
    diff = captured.out

    # diff should now clearly show change
    assert "-x = 'magic'" in diff
    assert "+x = MAGIC" in diff


# (2) Test for valid unix patch input (Path headers)
def test_diff_patch_compatibility(tmp_path, capsys, simple_report_maker):
    """
    Test that generated diff headers use relative paths (a/subdir/file.py),
    not just filenames (a/file.py), so `patch -p1` works.
    """
    d = tmp_path
    subdir = d / "subdir"
    subdir.mkdir()
    f = subdir / "deep.py"
    f.write_text("x = 'magic'\n", encoding="utf-8")

    args = MockArgs(path=d)
    config = Config(args)

    # Use fixture
    report = simple_report_maker(f, "MAGIC", "magic")

    process_report(config, report, apply=False)

    captured = capsys.readouterr()
    diff = captured.out

    # The critical check: The header MUST include the subdir
    rel_path = f.relative_to(d)
    expected_header = f"a/{rel_path}"
    assert expected_header in diff, f"Diff header missing relative path. Got:\n{diff}"


# (3a) Idempotency
def test_idempotency_no_changes(tmp_path):
    """Test that running the tool a second time results in no changes."""
    d = tmp_path
    f = d / "script.py"
    f.write_text("x = 'magic'\n", encoding="utf-8")

    # First Run: Apply changes
    with mock.patch(
        "sys.argv", ["constantipy", "--path", str(d), "--apply", "--min-count", "1"]
    ):
        main()

    content_after_first = f.read_text(encoding="utf-8")
    assert "MAGIC" in content_after_first

    # Second Run
    with mock.patch(
        "sys.argv", ["constantipy", "--path", str(d), "--apply", "--min-count", "1"]
    ):
        main()

    content_after_second = f.read_text(encoding="utf-8")
    assert content_after_second == content_after_first


# (3b) Incremental / Promotion Flow
def test_incremental_promotion_scenario(tmp_path):
    """
    Scenario:
    1. old.py has a local constant STR_1 = "str1" (refactored previously).
    2. new.py is added using "str1".
    3. Tool runs.
    4. Expectation: STR_1 promoted to global constants.py, both files use it.
    """
    d = tmp_path

    # 1. Setup Initial State (Pre-refactored old.py)
    old_py = d / "old.py"
    old_py.write_text("STR_1 = 'str1'\nprint(STR_1)\n", encoding="utf-8")

    # 2. Add new file
    new_py = d / "new.py"
    new_py.write_text("y = 'str1'\n", encoding="utf-8")

    # 3. Run Tool
    with mock.patch(
        "sys.argv", ["constantipy", "--path", str(d), "--apply", "--min-count", "2"]
    ):
        main()

    # 4. Verify Global Constants
    const_file = d / "constants.py"
    assert const_file.exists()
    const_content = const_file.read_text(encoding="utf-8")

    # Check that STR1 (or STR_1) was moved here.
    # 'str1' heuristics -> STR1 (or STR_1 if forced).
    # Since we rely on defaults, and 'str1' -> 'STR1' (underscore stripped if valid)
    assert "STR1 = 'str1'" in const_content

    # 5. Verify new.py uses the constant
    new_content = new_py.read_text(encoding="utf-8")
    assert "y = STR1" in new_content

    # 6. Verify old.py handling
    old_content = old_py.read_text(encoding="utf-8")
    # The tool should replace 'str1' in the definition with STR1
    # so it becomes STR_1 = STR1 (aliasing the global).
    assert "STR_1 = STR1" in old_content or "STR1 = 'str1'" in old_content
