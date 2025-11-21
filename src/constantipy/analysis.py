"""
Orchestration logic for scanning the codebase and generating the report.
"""

import os
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, Any, Set, Tuple, List
from constantipy.common import Config, eprint
from constantipy.loader import load_all_constants
from constantipy.scanner import scan_file
from constantipy.heuristics import generate_name, determine_type_hint


class RefactoringSession:
    """
    Manages the state of a refactoring session.
    """

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-few-public-methods
    def __init__(self, config: Config):
        self.config = config
        self.existing_map: Dict[Tuple[type, Any], Dict[str, Any]] = {}
        self.global_reserved: Set[str] = set()
        self.file_scope_names: Dict[str, Set[str]] = defaultdict(set)
        self.literal_map: Dict[Tuple[type, Any], List[Dict]] = defaultdict(list)
        self.name_tracker: Counter[str] = Counter()
        self.report: Dict[str, Any] = {}
        self.idx = 1

    def _load_and_scan(self) -> None:
        eprint(f"Loading constants from {self.config.target_file}...")
        self.existing_map, reserved = load_all_constants(
            self.config.constants_path, self.config.extra_files
        )

        # Scan Codebase
        eprint(f"Scanning {self.config.root}...")
        for root, _, files in os.walk(self.config.root):
            # Check exclusion
            parts = Path(root).parts
            if any(p in self.config.excluded_dirs for p in parts):
                continue

            for file in files:
                if not file.endswith(".py"):
                    continue
                fp = Path(root) / file
                if fp == self.config.constants_path:
                    continue

                literals, names = scan_file(fp, self.config)
                self.file_scope_names[str(fp)].update(names)

                # Pre-reserve existing global constants to avoid conflicts
                self.file_scope_names[str(fp)].update(reserved)
                self.global_reserved.update(reserved)

                for lit in literals:
                    val = lit["value"]
                    self.literal_map[(type(val), val)].append(lit)

    def _resolve_collision(self, base_name: str, reserved_names: Set[str]) -> str:
        name = base_name
        count = self.name_tracker[base_name]
        # If we have seen this base_name before in this run, start suffixing
        if count > 0:
            name = f"{base_name}_{count + 1}"

        # If it collides with existing code, keep incrementing
        while name in reserved_names:
            self.name_tracker[base_name] += 1
            name = f"{base_name}_{self.name_tracker[base_name] + 1}"
        return name

    def _create_new_constant(
        self, val: Any, occurrences: List[Dict]
    ) -> Tuple[str, str, str, bool]:
        """
        Determines the name, scope, source path, and whether it is new.
        """
        unique_files = {o["filepath"] for o in occurrences}
        is_regex = any(o.get("is_regex_arg") for o in occurrences)
        type_hint = determine_type_hint(val, is_regex)

        base_name = generate_name(val, self.config.naming_strategy, self.idx, type_hint)

        # Check if this constant is defined in the code already (e.g. MAGIC = 'magic')
        existing_defs = {
            o["definition_of"] for o in occurrences if o.get("definition_of")
        }

        force_global = not self.config.use_local_scope
        is_new = True

        if force_global or len(unique_files) > 1:
            scope = "global"
            source_path = str(self.config.constants_path)
            reserved = self.global_reserved.copy()
            if base_name in existing_defs:
                reserved.discard(base_name)
            final_name = self._resolve_collision(base_name, reserved)
        else:
            scope = "local"
            source_path = list(unique_files)[0]
            reserved = self.file_scope_names[source_path].copy()
            if base_name in existing_defs:
                reserved.discard(base_name)
            final_name = self._resolve_collision(base_name, reserved)
            
            # If the resolved name matches an existing definition in this file,
            # it is NOT new (it's already defined here).
            if final_name in existing_defs:
                is_new = False

        self.name_tracker[final_name] += 1
        if is_new:
            self.idx += 1
            
        return final_name, scope, source_path, is_new

    def _process_item(self, val: Any, occurrences: List[Dict]) -> None:
        """
        Decides the name and scope for a constant value and adds it to the report.
        """
        if (type(val), val) in self.existing_map:
            entry = self.existing_map[(type(val), val)]
            final_name = entry["name"]
            scope = entry["scope"]
            source_path = str(entry["source"]) if entry["source"] else None
            is_new = False
        else:
            final_name, scope, source_path, is_new = self._create_new_constant(val, occurrences)

        self.report[final_name] = {
            "value": val,
            "occurrences": occurrences,
            "is_new": is_new,
            "source_path": source_path,
            "scope": scope,
        }

    def analyze(self) -> Dict[str, Any]:
        """
        Runs the full analysis pipeline: load, scan, process, and return report.
        """
        self._load_and_scan()
        sorted_items = sorted(
            self.literal_map.items(), key=lambda x: len(x[1]), reverse=True
        )

        for (_, val), occurrences in sorted_items:
            if len(occurrences) < self.config.min_count:
                continue
            self._process_item(val, occurrences)

        return self.report


def analyze_codebase(config: Config) -> Dict[str, Any]:
    """Wrapper function to start a refactoring session."""
    session = RefactoringSession(config)
    return session.analyze()