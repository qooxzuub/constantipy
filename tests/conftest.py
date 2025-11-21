"""
Shared Pytest fixtures for Constantipy tests.
"""

import pytest


@pytest.fixture
def simple_report_maker():
    """
    Returns a function that generates a standard report dictionary
    to avoid code duplication in tests.
    """

    def _make(filepath, const_name="CONST_FOO", value="foo"):
        return {
            const_name: {
                "value": value,
                "is_new": True,
                "scope": "local",
                "source_path": str(filepath),
                "occurrences": [
                    {
                        "filepath": str(filepath),
                        "lineno": 1,
                        "col_offset": 4,
                        "end_lineno": 1,
                        "end_col_offset": 4 + len(repr(value)),
                    }
                ],
            }
        }

    return _make
