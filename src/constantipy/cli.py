#!/usr/bin/env python3
"""
Constantipy: The magic removal tool.
"""
import argparse
import json
import logging
import os
import sys

from constantipy.analysis import analyze_codebase
from constantipy.args import get_parser
from constantipy.common import Config, eprint
from constantipy.exceptions import ConstantipyError
from constantipy.refactor import process_report

logger = logging.getLogger("constantipy")


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

    logging.basicConfig(
        level=logging.DEBUG,
        format="[{levelname}] {message}",
        style="{",
    )

    for i, arg in enumerate(sys.argv):
        logging.debug("<<<<< ARGV[{%s}]: {%s}", i, arg)

    parser = get_parser()
    args = parser.parse_args()
    # logging.debug(">>>>> ARGS: {%s}", args)
    logger.debug("vars(args)=%s", vars(args))
    logger.debug("Effective scan path: %s", args.path)

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
