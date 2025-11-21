"""
Orchestration logic for scanning the codebase and generating the report.
"""

import os
from collections import defaultdict, Counter
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
        for root, dirs, files in os.walk(self.config.root):
            dirs[:] = [d for d in dirs if d not in self.config.excluded_dirs]
            for file in files:
                if file.endswith(".py"):
                    filepath = self.config.root / root / file
                    if (
                        filepath == self.config.constants_path
                        or filepath in self.config.extra_files
                    ):
                        continue

                    found, names = scan_file(filepath, self.config)
                    self.file_scope_names[str(filepath)] = names

                    for item in found:
                        key = (type(item["value"]), item["value"])
                        self.literal_map[key].append(item)

        self.global_reserved = reserved

    def _resolve_collision(self, base_name: str, blocked_names: Set[str]) -> str:
        if (base_name not in blocked_names) and (self.name_tracker[base_name] == 0):
            return base_name
        c = 1
        candidate = f"{base_name}_{c}"
        while (candidate in blocked_names) or (self.name_tracker[candidate] > 0):
            c += 1
            candidate = f"{base_name}_{c}"
        return candidate

    def _process_item(self, val: Any, occurrences: List[Dict]) -> None:
        unique_files = {occ["filepath"] for occ in occurrences}
        lookup_key = (type(val), val)

        if lookup_key in self.existing_map:
            details = self.existing_map[lookup_key]
            final_name = details["name"]
            source_path = str(details["source"])
            is_new = False
            scope = details.get("scope", "global")
        else:
            is_regex = any(occ.get("is_regex_arg", False) for occ in occurrences)
            type_hint = determine_type_hint(val, is_regex)
            base_name = generate_name(
                val, self.config.naming_strategy, self.idx, type_hint
            )

            force_global = not self.config.use_local_scope
            if force_global or len(unique_files) > 1:
                scope = "global"
                source_path = str(self.config.constants_path)
                final_name = self._resolve_collision(base_name, self.global_reserved)
            else:
                scope = "local"
                source_path = list(unique_files)[0]
                local_names = self.file_scope_names[source_path]
                final_name = self._resolve_collision(base_name, local_names)

            self.name_tracker[final_name] += 1
            is_new = True
            self.idx += 1

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
