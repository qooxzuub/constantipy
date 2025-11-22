#!/usr/bin/env python3
"""
Constantipy: The magic removal tool.
"""
import argparse
import json
import os
import sys

from constantipy.analysis import analyze_codebase
from constantipy.common import Config, eprint
from constantipy.exceptions import ConstantipyError
from constantipy.refactor import process_report


def handle_validate(config: Config) -> bool:
    """Validates the schema of a JSON report file."""
    if not os.path.exists(config.report_file):
        eprint(f"Report file not found: {config.report_file}")
        return False
    try:
        with open(config.report_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        errors = []
        required = ["value", "is_new", "scope", "occurrences"]
        for name, props in data.items():
            for field in required:
                if field not in props:
                    errors.append(f"Constant '{name}' missing '{field}'")
            if props.get("scope") == "global" and "source_path" not in props:
                errors.append(f"Constant '{name}' (global) missing 'source_path'")

        if errors:
            eprint(f"Validation failed with {len(errors)} errors:")
            for e in errors[:5]:
                eprint(f"  - {e}")
            return False

        eprint(f"Valid Report. Contains {len(data)} constants.")
        return True
    except json.JSONDecodeError:
        eprint("Invalid JSON syntax.")
        return False


def handle_refactor(config: Config, apply: bool = False) -> bool:
    """Reads report from stdin and triggers refactoring."""
    try:
        # Read from stdin
        input_data = sys.stdin.read()
        if not input_data:
            eprint("No input provided on stdin.")
            return False
        report = json.loads(input_data)
        process_report(config, report, apply=apply)
        return True
    except json.JSONDecodeError:
        eprint("Invalid JSON on stdin.")
        return False
    except ConstantipyError as e:
        eprint(f"Refactor error: {e}")
        return False


def get_parser() -> argparse.ArgumentParser:
    """
    Constructs and returns the argument parser.
    Exposed for documentation and shell completion generation (shtab).
    """
    parser = argparse.ArgumentParser(
        description="Constantipy: Find and refactor magic literals.", prog="constantipy"
    )

    # Global Arguments
    parser.add_argument(
        "--path",
        default=".",
        help="Path to scan/refactor (default: current directory)",
    )
    parser.add_argument(
        "--constants-file",
        default="constants.py",
        help="Name of the file to store global constants",
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=4,
        help="Minimum length for string literals (default: 4)",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=2,
        help="Minimum occurrences to be considered (default: 2)",
    )
    parser.add_argument(
        "--no-local-scope",
        action="store_true",
        help="Force all constants to be global",
    )
    parser.add_argument(
        "--report-file",
        default="constantipy_report.json",
        help="File used for validate/report",
    )

    # Filter/Ignore Arguments
    parser.add_argument(
        "--ignore-call", action="append", help="Ignore arguments inside specific calls"
    )
    parser.add_argument("--exclude", action="append", help="Exclude directories")
    parser.add_argument("--ignore-num", action="append", help="Ignore specific numbers")
    parser.add_argument(
        "--include-num", action="append", help="Include specific numbers (un-ignore)"
    )
    parser.add_argument("--ignore-str", action="append", help="Ignore specific strings")

    # Types
    parser.add_argument("--no-numbers", action="store_true", help="Do not scan numbers")
    parser.add_argument("--no-ints", action="store_true", help="Do not scan integers")
    parser.add_argument("--no-floats", action="store_true", help="Do not scan floats")
    parser.add_argument("--no-bytes", action="store_true", help="Do not scan bytes")

    parser.add_argument(
        "--naming",
        choices=["derived", "generic"],
        default="derived",
        help="Naming strategy",
    )
    parser.add_argument("--extra-constants", nargs="*")

    # For the implicit flow
    parser.add_argument(
        "--apply", action="store_true", help="Apply changes (files are modified)"
    )

    # Subcommands
    sub = parser.add_subparsers(dest="command")

    # Report (Output JSON to stdout)
    sub.add_parser("report", help="Generate JSON report to stdout")

    # Validate (Validate file)
    val = sub.add_parser("validate", help="Validate a report file")
    val.add_argument("--report-file", required=True)

    # Refactor (Input JSON from stdin -> Output diff or Apply)
    ref = sub.add_parser("refactor", help="Read report from stdin and output diff")
    ref.add_argument("--apply", action="store_true", help="Modify files")

    return parser


def run(args: argparse.Namespace, config: Config) -> bool:
    """
    Executes the logic corresponding to the parsed CLI arguments.
    Returns True on success, False on failure.
    """
    # Legacy/Validation override
    if args.command == "validate":
        config.report_file = args.report_file
        return handle_validate(config)

    if args.command == "refactor":
        return handle_refactor(config, apply=args.apply)

    # Default Flow or 'report' command
    # 1. Analyze
    report_data = analyze_codebase(config)

    if args.command == "report":
        json.dump(report_data, sys.stdout, indent=2, default=str)
        return True

    # Implicit Flow (No command) -> Report + Refactor
    # 2. Refactor (Internal pass)
    eprint("Analysis complete. Starting refactor...")
    process_report(config, report_data, apply=args.apply)
    return True


def main() -> None:
    """
    Main entry point for the Constantipy CLI.
    Parses arguments and delegates to the run function.
    """
    parser = get_parser()
    args = parser.parse_args()

    try:
        config = Config(args)
    except ValueError as exc:
        raise ConstantipyError(f"Invalid configuration: {exc}") from exc

    success = run(args, config)

    if not success:
        raise ConstantipyError("Run was not successful")


if __name__ == "__main__":
    try:
        main()
    except ConstantipyError as e_main:
        eprint(f"Error: {e_main}")
        sys.exit(1)
    except KeyboardInterrupt:
        eprint("\nInterrupted.")
        sys.exit(130)
