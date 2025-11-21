"""Test heuristics module, for generating variable names"""
import pytest
from constantipy.heuristics import generate_name, determine_type_hint


def test_generate_name_invalid_type():
    """Test that generate_name raises an error for unsupported types."""
    with pytest.raises(TypeError):
        generate_name(None, "derived", 1)


def test_generate_name_special_characters():
    """Test that generate_name handles special characters in the string."""
    name = generate_name("special!@#chars", "derived", 1)
    assert name == "SPECIAL_CHARS"


def test_generate_name_long_string():
    """Test that generate_name handles very long strings."""
    long_str = "A" * 1000
    name = generate_name(long_str, "derived", 1)
    assert len(name) <= 50
    assert name.isidentifier()


def test_generate_name_empty_string():
    """Test that generate_name handles empty strings."""
    name = generate_name("", "derived", 1)
    assert name == "STR_EMPTY"


def test_generate_name_integer():
    """Test that generate_name correctly handles integers."""
    name = generate_name(1234, "derived", 1)
    assert name == "INT_1234"


def test_heuristics_type_hints():
    """Test detection of SQL, URL, and Path type hints."""
    assert determine_type_hint("SELECT * FROM x", False) == "sql"
    assert determine_type_hint("INSERT INTO x", False) == "sql"
    assert determine_type_hint("https://google.com", False) == "url"
    assert determine_type_hint("/usr/bin/env", False) == "path"
    assert determine_type_hint("random string", False) is None


def test_heuristics_bytes_md5():
    """Test fallback to MD5 for non-printable bytes."""
    # \x80 is non-ascii
    val = b"\x80\x81\x82"
    name = generate_name(val, "derived", 1)
    assert name.startswith("BYTES_")
    assert len(name) > 6


def test_heuristics_str_naming():
    """Test specific string naming logic."""
    # URL
    name = generate_name("https://api.com", "derived", 1, type_hint="url")
    assert name.endswith("_URL")
    # Path
    name = generate_name("/var/log", "derived", 1, type_hint="path")
    assert name.endswith("_PATH")


def test_naming_heuristics_core():
    """Basic sanity checks for naming (from test_core.py)."""
    assert generate_name("FieldStateOption", "derived", 1) == "FIELD_STATE_OPTION"
    assert (
        generate_name("https://google.com", "derived", 1, type_hint="url")
        == "HTTPS_GOOGLE_COM_URL"
    )
    assert generate_name(86400, "derived", 1) == "INT_86400"
