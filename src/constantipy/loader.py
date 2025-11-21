"""
Logic for loading and parsing existing constants files.
"""

import ast
from pathlib import Path
from typing import Dict, Set, Tuple, Any, List, Optional


class ConstantLoader(ast.NodeVisitor):
    """
    AST Visitor that identifies existing constants in target files.
    """

    def __init__(self) -> None:
        self.value_to_details: Dict[Tuple[type, Any], Dict[str, Any]] = {}
        self.defined_names: Set[str] = set()
        self.current_file: Optional[Path] = None

    # pylint: disable=invalid-name
    def visit_Assign(self, node: ast.Assign) -> None:
        """Visits assignment nodes to find top-level constant definitions."""
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            const_name = node.targets[0].id
            self.defined_names.add(const_name)

            if isinstance(node.value, ast.Constant):
                val = node.value.value
                if isinstance(val, (str, int, float, bytes)):
                    self.value_to_details[(type(val), val)] = {
                        "name": const_name,
                        "source": self.current_file,
                        "scope": "global",
                    }
        self.generic_visit(node)


def load_all_constants(target_path: Path, extra_paths: List[Path]) -> Tuple[Dict, Set]:
    """
    Parses the target constants file and extra files to map existing constants.
    """
    loader = ConstantLoader()
    paths_to_check = extra_paths + ([target_path] if target_path.exists() else [])

    for path in paths_to_check:
        if path.exists():
            loader.current_file = path
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loader.visit(ast.parse(f.read()))
            except (SyntaxError, OSError):
                pass

    return loader.value_to_details, loader.defined_names
