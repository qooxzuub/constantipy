import ast
import importlib.util
import sysconfig
from pathlib import Path

# Whitelist your own package
WHITELIST = {"constantipy"}

# Path to your project source code
PROJECT_PACKAGE_PATH = "src/constantipy"


def is_relative_to(path: Path, other: Path) -> bool:
    """Helper needed for Python 3.8 compatibility"""
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False


def _is_stdlib_module(module_name: str) -> bool:
    """Return True if the module is part of the standard library or whitelisted."""
    if module_name in WHITELIST:
        return True
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return False
    if spec.origin in (None, "built-in", "frozen"):
        return True
    stdlib_path = Path(sysconfig.get_paths()["stdlib"]).resolve()
    return is_relative_to(Path(spec.origin).resolve(), stdlib_path)


def _get_py_files(package_path: str):
    """Yield all Python files in the package."""
    return Path(package_path).rglob("*.py")


def _find_imports_in_file(py_file: Path):
    """Return all top-level imports in a Python file."""
    with py_file.open("r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(py_file))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports


def test_no_nonstdlib_dependencies():
    """Fail if any non-stdlib imports exist, reporting the file and offending module."""
    offending = []

    for py_file in _get_py_files(PROJECT_PACKAGE_PATH):
        for mod in _find_imports_in_file(py_file):
            if not _is_stdlib_module(mod):
                offending.append((py_file, mod))

    assert not offending, "Non-stdlib dependencies found:\n" + "\n".join(
        f" - {file}: {mod}" for file, mod in offending
    )
