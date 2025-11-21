import pytest
import argparse
from constantipy.common import Config


def make_args(**kwargs):
    """Helper to create a valid argparse Namespace with default values."""
    defaults = {
        "path": ".",
        "min_length": 4,
        "min_count": 2,
        "mode": "scan",
        "report_file": "report.json",
        "naming": "derived",
        "constants_file": "constants.py",
        "extra_constants": [],
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
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_config_invalid_argument():
    """Test that invalid arguments raise appropriate errors."""
    with pytest.raises(ValueError, match="Invalid argument for min_length"):
        Config(make_args(min_length=-1))
    with pytest.raises(ValueError, match="Invalid argument for min_count"):
        Config(make_args(min_count=-1))


def test_config_empty_ignore_num():
    """Test that an empty ignore_num list results in the default ignored numbers."""
    args = make_args(ignore_num=[])
    config = Config(args)
    assert 0 in config.ignored_numbers  # 0 is a trivial number by default


def test_config_include_num_removes_from_ignored():
    """Test that include_num removes values from ignored_numbers."""
    args = make_args(include_num=["2", "0", "99"])
    config = Config(args)

    assert 2 not in config.ignored_numbers
    assert 0 not in config.ignored_numbers
    assert 1 in config.ignored_numbers  # Default should still be present
    assert 99 not in config.ignored_numbers


def test_config_with_non_numeric_ignore_num_raises():
    """Test that invalid non-numeric values in ignore_num raise ValueError."""
    args = make_args(ignore_num=["10", "3.5", "not-a-number"])
    # The Config class casting currently raises ValueError for bad inputs
    with pytest.raises(ValueError):
        Config(args)
