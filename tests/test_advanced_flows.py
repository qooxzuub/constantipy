"""
Tests for complex workflows: diff generation, idempotency, and incremental updates.
This suite specifically targets regression cases like zombie imports and idempotency loops.
"""

from unittest import mock

from constantipy.cli import main
from constantipy.common import Config
from constantipy.refactor import process_report

from .mock_args import MockArgs

# --- 1. Diff & File Formatting Tests ---


def test_diff_no_trailing_newline(tmp_path, capsys, simple_report_maker):
    """
    Regression Test: Files without newlines caused malformed diffs and file corruption.
    Expectation: The tool appends a newline and generates a valid diff.
    """
    d = tmp_path
    f = d / "no_newline.py"
    # Write bytes to strictly control EOF
    f.write_bytes(b"x = 'magic'")

    args = MockArgs(path=d)
    config = Config(args)

    # Force a replacement
    report = simple_report_maker(f, "MAGIC", "magic")
    process_report(config, report, apply=False)

    captured = capsys.readouterr()
    diff = captured.out

    # Check for standard diff output indicating the line was changed
    assert "-x = 'magic'" in diff
    assert "+x = MAGIC" in diff
    # Implicitly checks that we didn't crash or produce binary garbage


def test_diff_patch_compatibility(tmp_path, capsys, simple_report_maker):
    """
    Regression Test: Diff headers used only filenames (b/file.py), breaking `patch -p1`.
    Expectation: Headers use relative paths (b/subdir/file.py).
    """
    d = tmp_path
    subdir = d / "subdir"
    subdir.mkdir()
    f = subdir / "deep.py"
    f.write_text("x = 'magic'\n", encoding="utf-8")

    args = MockArgs(path=d)
    config = Config(args)

    report = simple_report_maker(f, "MAGIC", "magic")
    process_report(config, report, apply=False)

    captured = capsys.readouterr()
    diff = captured.out

    # Critical: Header must contain the subdirectory
    rel_path = f.relative_to(d)
    expected_header = f"a/{rel_path}"
    assert expected_header in diff, f"Diff header missing relative path. Got:\n{diff}"


# --- 2. Idempotency & Recursion Tests ---


def test_idempotency_no_changes(tmp_path):
    """
    Regression Test: Running the tool twice creates `MAGIC = MAGIC` assignments or `MAGIC_1`.
    Expectation: Second run produces ZERO changes to the file content.
    """
    d = tmp_path
    f = d / "script.py"
    f.write_text("x = 'magic'\n", encoding="utf-8")

    # First Run: Replaces 'magic' -> MAGIC
    with mock.patch(
        "sys.argv", ["constantipy", "--path", str(d), "--apply", "--min-count", "1"]
    ):
        main()

    content_after_first = f.read_text(encoding="utf-8")
    assert "MAGIC" in content_after_first
    assert "x = MAGIC" in content_after_first

    # Second Run: Should NOT see "MAGIC = 'magic'" as a new occurrence of 'magic'
    with mock.patch(
        "sys.argv", ["constantipy", "--path", str(d), "--apply", "--min-count", "1"]
    ):
        main()

    content_after_second = f.read_text(encoding="utf-8")
    assert (
        content_after_second == content_after_first
    ), "Idempotency failed: File changed on second run!"


def test_idempotency_existing_definition(tmp_path):
    """
    Regression Test: Existing constant definitions were being replaced recursively.
    Input:  MAGIC = 'magic'
    Bad:    MAGIC = MAGIC
    Good:   MAGIC = 'magic' (Skipped)
    """
    d = tmp_path
    f = d / "defined.py"
    f.write_text("MAGIC = 'magic'\n", encoding="utf-8")

    # Run tool looking for 'magic'
    with mock.patch(
        "sys.argv", ["constantipy", "--path", str(d), "--apply", "--min-count", "1"]
    ):
        main()

    content = f.read_text(encoding="utf-8")
    # Should NOT contain "MAGIC = MAGIC"
    assert "MAGIC = MAGIC" not in content
    # Should retain original definition
    assert "MAGIC = 'magic'" in content


# --- 3. Promotion & Zombie Import Tests ---


def test_incremental_promotion_cleanup(tmp_path):
    """
    Regression Test: Local constants promoted to global left behind 'zombie' definitions.

    Scenario:
    1. old.py has `STR1 = 'str1'`.
    2. new.py uses `'str1'`.
    3. Tool runs -> Promotes `STR1` to global `constants.py`.

    Expectation for old.py:
    - Import added: `from constants import STR1`
    - Zombie removed: The line `STR1 = 'str1'` MUST be deleted.
    """
    d = tmp_path

    # 1. Setup Initial State
    old_py = d / "old.py"
    old_py.write_text("STR1 = 'str1'\nprint(STR1)\n", encoding="utf-8")

    new_py = d / "new.py"
    new_py.write_text("y = 'str1'\n", encoding="utf-8")

    # 2. Run Tool (min_count=2 forces global promotion)
    with mock.patch(
        "sys.argv", ["constantipy", "--path", str(d), "--apply", "--min-count", "2"]
    ):
        main()

    # 3. Verify Global Constants
    const_file = d / "constants.py"
    assert const_file.exists()
    const_content = const_file.read_text(encoding="utf-8")
    assert "STR1 = 'str1'" in const_content

    # 4. Verify old.py Cleanup (The Critical Check)
    old_content = old_py.read_text(encoding="utf-8")

    # Check Import exists
    assert "from constants import STR1" in old_content

    # Check Zombie is dead: The local definition line should be gone
    # We search specifically for the assignment line
    assert (
        "STR1 = 'str1'" not in old_content
    ), "Zombie definition found! Local assignment wasn't removed."

    # Check usage remains valid
    assert "print(STR1)" in old_content


def test_promotion_imports_generated(tmp_path):
    """
    Regression Test: Refactored files were missing import statements.
    Expectation: Any file receiving a global replacement gets a `from constants import ...` line.
    """
    d = tmp_path
    f1 = d / "f1.py"
    f1.write_text("x = 'shared'\n", encoding="utf-8")
    f2 = d / "f2.py"
    f2.write_text("y = 'shared'\n", encoding="utf-8")

    with mock.patch(
        "sys.argv", ["constantipy", "--path", str(d), "--apply", "--min-count", "2"]
    ):
        main()

    f1_content = f1.read_text(encoding="utf-8")
    f2_content = f2.read_text(encoding="utf-8")

    # Verify imports
    assert "from constants import SHARED" in f1_content
    assert "from constants import SHARED" in f2_content

    # Verify replacements
    assert "x = SHARED" in f1_content
    assert "y = SHARED" in f2_content
