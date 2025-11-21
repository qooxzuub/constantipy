"""
Logic for generating diffs and applying changes.
"""

import ast
import sys
import difflib
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Tuple, Any, Set
from constantipy.exceptions import ConstantipyError
from constantipy.common import Config, eprint


def get_import_module_path(file_path: str, root: Path) -> str:
    """
    Calculates the python module path (dot-separated) for a given file
    relative to the project root.
    """
    try:
        rel = Path(file_path).relative_to(root)
        parts = list(rel.parts)
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        return ".".join(parts)
    except ValueError:
        return Path(file_path).stem


def find_insertion_line(source_code: str) -> int:
    """
    Determines the optimal line number to insert new import statements or constants.
    Prioritizes inserting after existing imports or module-level docstrings.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return 0

    last_import = 0
    has_imports = False
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            end = node.end_lineno or 0
            last_import = max(last_import, end)
            has_imports = True

    if has_imports:
        return last_import

    insert = 0
    lines = source_code.splitlines()
    if lines and lines[0].startswith("#!"):
        insert = 1

    doc = ast.get_docstring(tree, clean=False)
    if doc and tree.body and isinstance(tree.body[0], ast.Expr):
        end = tree.body[0].end_lineno or 0
        insert = max(insert, end)

    return insert


def _apply_replacements(lines: List[str], replacements: List[Dict[str, Any]]) -> bool:
    """
    Applies a list of text replacements to the source lines.
    Replacements must be sorted in reverse order of position.
    """
    modified = False
    for rep in replacements:
        # If the constant we are inserting (rep['name']) matches the variable
        # that this literal is defining (rep['definition_of']), skip replacement.
        # This prevents 'MAGIC = MAGIC' assignments.
        if rep.get("definition_of") == rep["name"]:
            continue

        s_line = rep["start_line"] - 1
        s_col = rep["start_col"]
        e_line = rep["end_line"] - 1
        e_col = rep["end_col"]
        name = rep["name"]

        if s_line < 0 or s_line >= len(lines):
            continue

        # Single line replacement
        if s_line == e_line:
            line = lines[s_line]
            if s_col < 0 or e_col > len(line):
                continue
            before = line[:s_col]
            after = line[e_col:]
            lines[s_line] = before + name + after
            modified = True
        else:
            # Multi-line replacement
            lines[s_line] = lines[s_line][:s_col] + name + "\n"
            for i in range(s_line + 1, e_line):
                lines[i] = ""  # Clear intermediate lines
            lines[e_line] = lines[e_line][e_col:]  # Keep suffix of last line
            modified = True
    return modified


def _insert_global_imports(
    lines: List[str], replacements: List[Dict[str, Any]], config: Config, content: str
) -> Tuple[bool, Set[str]]:
    """
    Identifies used global constants and inserts an import statement if needed.
    Returns (modified_bool, set_of_imported_names).
    """
    used_globals: Set[str] = set()
    for rep in replacements:
        if rep.get("scope") == "global":
            used_globals.add(rep["name"])

    if not used_globals:
        return False, set()

    module_name = config.target_file.rsplit(".", 1)[0]
    names_str = ", ".join(sorted(used_globals))
    import_stmt = f"from {module_name} import {names_str}\n"

    # Check if already imported to avoid duplication (naive check)
    for line in lines:
        if import_stmt.strip() in line:
            return False, used_globals

    insert_idx = find_insertion_line(content)
    lines.insert(insert_idx, import_stmt)
    return True, used_globals


def _remove_redundant_locals(lines: List[str], imported_names: Set[str]) -> bool:
    """
    Removes local definitions (e.g. 'MAGIC = ...') if 'MAGIC' is now imported globally.
    """
    if not imported_names:
        return False

    modified = False
    # Naive line-by-line check. Ideally we would use AST to find assignment nodes,
    # but we are working with a list of strings that might already be modified.
    # We scan for lines starting with "NAME =" matching imported names.

    # Iterate backwards to safely remove lines
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        for name in imported_names:
            # Check for simple assignment pattern "NAME ="
            if line.startswith(f"{name} =") or line.startswith(f"{name}="):
                # Ensure it's a top-level assignment or simple assignment
                # This is a heuristic; precise AST matching on modified code
                # is hard without re-parsing.
                lines.pop(i)
                modified = True
                break
    return modified


def _process_single_file(
    file_path: str,
    replacements: List[Dict[str, Any]],
    new_locals: List[Tuple[str, Any]],
    config: Config,
) -> Tuple[bool, List[str], List[str]]:
    """
    Reads a file, applies replacements, inserts imports, and inserts local definitions.
    Returns (modified_flag, original_lines, new_lines).
    """
    path_obj = Path(file_path)
    try:
        with open(path_obj, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        eprint(f"Error reading {path_obj}: {e}")
        return False, [], []

    lines = content.splitlines(keepends=True)

    # Ensure file ends with newline for clean diffs
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    original_lines = lines[:]

    changed = _apply_changes(lines, replacements, new_locals, config, content)

    if not changed:
        return False, [], []

    return True, original_lines, lines


def _apply_changes(
    lines: List[str],
    replacements: List[Dict[str, Any]],
    new_locals: List[Tuple[str, Any]],
    config: Config,
    content: str,
) -> bool:
    # Sort replacements reverse order to not mess up indices
    replacements.sort(key=lambda x: (x["start_line"], x["start_col"]), reverse=True)

    # 1. Apply Replacements
    replaced = _apply_replacements(lines, replacements)

    # 2. Insert Global Imports
    imported, imported_names = _insert_global_imports(
        lines, replacements, config, content
    )

    # 3. Remove Redundant Locals (Promotion cleanup)
    removed_locals = False
    if imported_names:
        removed_locals = _remove_redundant_locals(lines, imported_names)

    # 4. Insert locals
    inserted_locals = False
    if new_locals:
        insert_idx = find_insertion_line(content)
        # If imports inserted, list grew by 1.
        if imported:
            insert_idx += 1

        local_defs = [f"{n} = {repr(v)}\n" for n, v in new_locals]
        for line in reversed(local_defs):
            lines.insert(insert_idx, line)
        inserted_locals = True

    return replaced or imported or inserted_locals or removed_locals


def _handle_global_constants(
    config: Config, report: Dict[str, Any], apply: bool
) -> None:
    """Handles the generation and writing of global constants to the constants file."""
    new_globals = []
    needs_header = (
        not config.constants_path.exists() or config.constants_path.stat().st_size == 0
    )
    if needs_header:
        new_globals.append("# Generated by Constantipy\n")

    count = 0
    for name, data in report.items():
        if data.get("is_new") and data.get("scope") == "global":
            new_globals.append(f"{name} = {repr(data['value'])}")
            count += 1

    if count == 0:
        return

    global_text = "\n".join(new_globals) + "\n"

    if apply:
        prefix = ""
        if config.constants_path.exists() and config.constants_path.stat().st_size > 0:
            with open(config.constants_path, "rb") as f:
                f.seek(-1, 2)
                if f.read(1) != b"\n":
                    prefix = "\n"
        with open(config.constants_path, "a", encoding="utf-8") as f:
            f.write(prefix + global_text)
        eprint(f"Appended {count} globals to {config.constants_path}")
    else:
        print(f"--- PREVIEW: Append to {config.target_file} ---")
        print(global_text)


def _parse_occurrences(
    report: Dict[str, Any],
) -> Tuple[Dict[str, List[Dict]], Dict[str, List[Tuple]]]:
    """Parses the report to group replacements and local definitions by file."""
    rep_map = defaultdict(list)
    loc_map = defaultdict(list)

    for name, data in report.items():
        src = data.get("source_path")
        scope = data.get("scope", "global")
        if data.get("is_new") and scope == "local":
            loc_map[src].append((name, data["value"]))

        for occ in data["occurrences"]:
            rep_map[occ["filepath"]].append(
                {
                    "name": name,
                    "source_path": src,
                    "scope": scope,
                    "start_line": occ["lineno"],
                    "start_col": occ["col_offset"],
                    "end_line": occ["end_lineno"],
                    "end_col": occ["end_col_offset"],
                    # Pass definition info for idempotency checks
                    "definition_of": occ.get("definition_of"),
                }
            )
    return rep_map, loc_map


def process_report(config: Config, report: Dict[str, Any], apply: bool = False) -> None:
    """
    Processes a report to generate diffs or apply changes.
    """
    try:
        # 1. Handle Global Constants File
        _handle_global_constants(config, report, apply)

        # 2. Handle Source Files
        rep_map, loc_map = _parse_occurrences(report)
        files_to_process = set(rep_map.keys()) | set(loc_map.keys())

    except KeyError as e:
        raise ConstantipyError(f"Malformed report: Missing key {e}") from e

    for fp in files_to_process:
        modified, original, new_lines = _process_single_file(
            fp, rep_map[fp], loc_map[fp], config
        )

        if modified:
            if apply:
                with open(fp, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                eprint(f"Refactored {fp}")
            else:
                # Calculate relative path for diff header
                try:
                    rel_path = Path(fp).relative_to(config.root)
                except ValueError:
                    rel_path = Path(fp).name

                # Print diff to stdout
                sys.stdout.writelines(
                    difflib.unified_diff(
                        original,
                        new_lines,
                        fromfile=f"a/{rel_path}",
                        tofile=f"b/{rel_path}",
                    )
                )
