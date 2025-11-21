"""Tests for the loader module."""
from constantipy.loader import load_all_constants


def test_loader_syntax_error(tmp_path):
    """Test that loader skips files with syntax errors."""
    d = tmp_path
    bad_file = d / "constants.py"
    bad_file.write_text("INVALID SYNTAX", encoding="utf-8")

    # Should not raise exception
    consts, defined = load_all_constants(bad_file, [])
    assert not consts
    assert defined == set()


def test_loader_complex_assignments(tmp_path):
    """Test that loader ignores non-constant assignments."""
    d = tmp_path
    f = d / "constants.py"
    f.write_text("x, y = 1, 2\nz = [1, 2]\nw = func()", encoding="utf-8")

    consts, _ = load_all_constants(f, [])
    # None of these are simple constant assignments
    assert not consts


def test_loader_valid_constants(tmp_path):
    """Test loading valid constants."""
    d = tmp_path
    f = d / "constants.py"
    f.write_text("A = 'str'\nB = 123\nC = 1.5", encoding="utf-8")

    consts, defined = load_all_constants(f, [])
    assert "A" in defined
    assert "B" in defined
    assert "C" in defined
    assert consts[(str, "str")]["name"] == "A"
    assert consts[(int, 123)]["name"] == "B"
