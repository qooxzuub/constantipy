"""
AST Scanner logic for identifying magic literals in source code.
"""

import ast
from pathlib import Path
from typing import List, Dict, Set, Tuple, Union, Any
from constantipy.common import Config, REGEX_FUNCTIONS

# Define types that can have docstrings
DocstringNode = Union[ast.AsyncFunctionDef, ast.FunctionDef, ast.ClassDef, ast.Module]


class CodebaseScanner(ast.NodeVisitor):
    """
    AST Visitor that scans source code for magic literals.
    """

    def __init__(self, config: Config):
        self.config = config
        self.literals: List[Dict[str, Any]] = []
        self.docstring_ranges: Set[Tuple[int, int]] = set()
        self.top_level_names: Set[str] = set()
        self.ignore_depth = 0
        self.in_regex_context = False

    def _mark_docstring(self, node: DocstringNode) -> None:
        doc_node = ast.get_docstring(node, clean=False)
        if not doc_node:
            return
        if node.body and isinstance(node.body[0], ast.Expr):
            expr = node.body[0]
            if isinstance(expr.value, ast.Constant) and isinstance(
                expr.value.value, str
            ):
                self.docstring_ranges.add((expr.value.lineno, expr.value.col_offset))

    def _collect_names(self, node: ast.Module) -> None:
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.top_level_names.add(child.name)
            elif isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        self.top_level_names.add(target.id)
            elif isinstance(child, (ast.Import, ast.ImportFrom)):
                for alias in child.names:
                    name = alias.asname or alias.name.split(".")[0]
                    self.top_level_names.add(name)

    def _get_call_name(self, node: ast.AST) -> Union[str, None]:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = self._get_call_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        return None

    # pylint: disable=invalid-name
    def visit_Module(self, node: ast.Module) -> None:
        """Visits a Module node, marking docstrings and collecting top-level names."""
        self._mark_docstring(node)
        self._collect_names(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visits a FunctionDef node, marking its docstring."""
        self._mark_docstring(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visits an AsyncFunctionDef node, marking its docstring."""
        self._mark_docstring(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visits a ClassDef node, marking its docstring."""
        self._mark_docstring(node)
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """Visits f-strings. Currently ignores them to avoid complexity."""

    def visit_Call(self, node: ast.Call) -> None:
        """
        Visits a Call node.
        Checks if the call should be ignored based on configuration.
        Detects Regex context.
        """
        call_name = self._get_call_name(node.func)
        is_ignored = call_name in self.config.ignored_calls

        if is_ignored:
            self.ignore_depth += 1

        is_regex = False
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "re"
            and node.func.attr in REGEX_FUNCTIONS
        ):
            is_regex = True

        if is_regex and node.args:
            self.in_regex_context = True
            self.visit(node.args[0])
            self.in_regex_context = False
            for arg in node.args[1:]:
                self.visit(arg)
            for k in node.keywords:
                self.visit(k)
        else:
            self.generic_visit(node)

        if is_ignored:
            self.ignore_depth -= 1

    def _handle_str_constant(self, node: ast.Constant, val: str) -> None:
        """Handles string constants."""
        if (node.lineno, node.col_offset) in self.docstring_ranges:
            return
        if len(val) < self.config.min_len:
            return
        if val in self.config.ignored_strings:
            return

        self.literals.append(
            {
                "value": val,
                "type": "str",
                "lineno": node.lineno,
                "col_offset": node.col_offset,
                "end_lineno": node.end_lineno,
                "end_col_offset": node.end_col_offset,
                "is_regex_arg": self.in_regex_context,
            }
        )

    def _handle_int_constant(self, node: ast.Constant, val: int) -> None:
        """Handles integer constants."""
        if not self.config.scan_ints:
            return
        if val in self.config.ignored_numbers:
            return
        self.literals.append(
            {
                "value": val,
                "type": "int",
                "lineno": node.lineno,
                "col_offset": node.col_offset,
                "end_lineno": node.end_lineno,
                "end_col_offset": node.end_col_offset,
            }
        )

    def _handle_float_constant(self, node: ast.Constant, val: float) -> None:
        """Handles float constants."""
        if not self.config.scan_floats:
            return
        if val in self.config.ignored_numbers:
            return
        self.literals.append(
            {
                "value": val,
                "type": "float",
                "lineno": node.lineno,
                "col_offset": node.col_offset,
                "end_lineno": node.end_lineno,
                "end_col_offset": node.end_col_offset,
            }
        )

    def _handle_bytes_constant(self, node: ast.Constant, val: bytes) -> None:
        """Handles bytes constants."""
        if not self.config.scan_bytes:
            return
        if len(val) < self.config.min_len:
            return
        self.literals.append(
            {
                "value": val,
                "type": "bytes",
                "lineno": node.lineno,
                "col_offset": node.col_offset,
                "end_lineno": node.end_lineno,
                "end_col_offset": node.end_col_offset,
            }
        )

    def visit_Constant(self, node: ast.Constant) -> None:
        """
        Visits a Constant node and records it if it meets criteria.
        Delegates to specific handlers based on type.
        """
        if self.ignore_depth > 0:
            return

        val = node.value

        if isinstance(val, str):
            self._handle_str_constant(node, val)
        elif isinstance(val, bool):
            # Boolean is a subclass of int, so check this first to ignore or handle
            pass
        elif isinstance(val, int):
            self._handle_int_constant(node, val)
        elif isinstance(val, float):
            self._handle_float_constant(node, val)
        elif isinstance(val, bytes):
            self._handle_bytes_constant(node, val)


def scan_file(filepath: Path, config: Config) -> Tuple[List[Dict], Set[str]]:
    """Scans a single file for literals and top-level names."""
    found = []
    names = set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(filepath))
        scanner = CodebaseScanner(config)
        scanner.visit(tree)
        found = scanner.literals
        for item in found:
            item["filepath"] = str(filepath)
        names = scanner.top_level_names
    except (SyntaxError, UnicodeDecodeError):
        pass
    return found, names
