import importlib.util
import sys
import sysconfig
from pathlib import Path

import pytest


def _is_stdlib_module(module_name: str) -> bool:
    """
    Returns True if `module_name` is part of the Python standard library.
    """
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None or spec.origin is None:
            return False
        # Standard library is usually under sysconfig.get_paths()["stdlib"]
        stdlib_path = Path(sysconfig.get_paths()["stdlib"]).resolve()
        return Path(spec.origin).resolve().is_relative_to(stdlib_path)
    except Exception:
        return False


def _get_project_modules(package_name: str) -> list[str]:
    """
    Return all top-level modules in the project package.
    """
    pkg = __import__(package_name)
    if hasattr(pkg, "__path__"):
        paths = list(pkg.__path__)
    else:
        paths = []
    modules = []
    for path in paths:
        for file in Path(path).rglob("*.py"):
            relative = file.relative_to(path)
            module = ".".join(relative.with_suffix("").parts)
            modules.append(module)
    return modules


def test_no_nonstdlib_dependencies():
    """
    Ensure the project does not import modules outside the Python standard library.
    """
    project_package = "constantipy"  # change to your package name
    project_modules = _get_project_modules(project_package)

    non_stdlib_imports = set()
    for mod in project_modules:
        try:
            imported = __import__(mod)
            for name, submod in vars(imported).items():
                if isinstance(submod, type(sys)):
                    if not _is_stdlib_module(submod.__name__):
                        non_stdlib_imports.add(submod.__name__)
        except Exception:
            continue

    assert (
        not non_stdlib_imports
    ), f"Non-stdlib dependencies found: {non_stdlib_imports}"
