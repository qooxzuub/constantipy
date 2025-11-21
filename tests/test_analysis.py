import pytest
import argparse
from constantipy.common import Config
from constantipy.analysis import RefactoringSession


def get_default_config():
    """Helper to generate a valid Config object with default settings."""
    args = argparse.Namespace(
        path=".",
        min_length=4,
        min_count=2,
        mode="scan",
        report_file="r.json",
        naming="derived",
        constants_file="c.py",
        extra_constants=[],
        no_local_scope=False,
        no_numbers=False,
        no_ints=False,
        no_floats=False,
        no_bytes=False,
        ignore_call=[],
        exclude=[],
        ignore_num=[],
        include_num=[],
        ignore_str=[],
    )
    return Config(args)


def test_name_collision_resolution():
    """Test that _resolve_collision correctly increments suffixes."""
    config = get_default_config()
    session = RefactoringSession(config)

    # Setup a scenario where Base, Base_1, and Base_2 are all taken
    blocked_names = {"MY_CONST", "MY_CONST_1", "MY_CONST_2"}

    # 1. First Attempt (Collision)
    # Should skip MY_CONST (base), MY_CONST_1 (blocked), MY_CONST_2 (blocked) -> MY_CONST_3
    result = session._resolve_collision("MY_CONST", blocked_names)
    assert result == "MY_CONST_3"

    # 2. Second Attempt (Simulate usage tracker incrementing)
    # If we try to use MY_CONST_3 again (e.g. another value generated the same name),
    # the name_tracker should force it to _4
    session.name_tracker["MY_CONST_3"] += 1
    result_next = session._resolve_collision("MY_CONST", blocked_names)
    assert result_next == "MY_CONST_4"


def test_process_item_existing_constant():
    """Test that _process_item reuses an existing constant if found."""
    config = get_default_config()
    session = RefactoringSession(config)

    # Pre-populate existing map (as if loaded from constants.py)
    # Key is (type, value)
    session.existing_map[(str, "foo")] = {
        "name": "EXISTING_FOO",
        "source": "constants.py",
        "scope": "global",
    }

    # Process "foo"
    occurrences = [{"filepath": "a.py", "is_regex_arg": False}]
    session._process_item("foo", occurrences)

    # Should reuse EXISTING_FOO
    assert "EXISTING_FOO" in session.report
    assert session.report["EXISTING_FOO"]["is_new"] is False
    assert session.report["EXISTING_FOO"]["scope"] == "global"
