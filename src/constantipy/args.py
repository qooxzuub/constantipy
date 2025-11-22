"""
Argument parsing
"""

import argparse


def _create_config_parent() -> argparse.ArgumentParser:
    """
    Creates a parent parser containing all configuration arguments.
    This allows these arguments to be shared between the main entry point
    and subcommands like 'refactor' and 'report'.
    """
    parser = argparse.ArgumentParser(add_help=False)

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
    filter_group = parser.add_argument_group("Filtering & Exclusion")
    filter_group.add_argument(
        "--ignore-call", action="append", help="Ignore arguments inside specific calls"
    )
    filter_group.add_argument("--exclude", action="append", help="Exclude directories")
    filter_group.add_argument(
        "--ignore-num", action="append", help="Ignore specific numbers"
    )
    filter_group.add_argument(
        "--include-num", action="append", help="Include specific numbers (un-ignore)"
    )
    filter_group.add_argument(
        "--ignore-str", action="append", help="Ignore specific strings"
    )

    # Types
    type_group = parser.add_argument_group("Type Selection")
    type_group.add_argument(
        "--no-numbers", action="store_true", help="Do not scan numbers"
    )
    type_group.add_argument(
        "--no-ints", action="store_true", help="Do not scan integers"
    )
    type_group.add_argument(
        "--no-floats", action="store_true", help="Do not scan floats"
    )
    type_group.add_argument("--no-bytes", action="store_true", help="Do not scan bytes")

    parser.add_argument(
        "--naming",
        choices=["derived", "generic"],
        default="derived",
        help="Naming strategy",
    )
    parser.add_argument("--extra-constants", nargs="*")

    return parser


def get_parser() -> argparse.ArgumentParser:
    """
    Constructs and returns the argument parser.

    - Global options are valid anywhere.
    - Commands are optional; default mode runs when no command is given.
    """
    # Parent parser containing all global options
    config_parent = _create_config_parent()

    description = """
Constantipy: Find and refactor magic literals.

MODES OF OPERATION:
  1. Direct Mode (Default):
     Run without a command to scan the path and preview changes.
     Use --apply to modify files in place.

     $ constantipy --path src/
     $ constantipy --path src/ --apply

  2. Pipeline Mode (Advanced):
     Use subcommands to generate, validate, and process JSON reports.
"""

    parser = argparse.ArgumentParser(
        description=description,
        prog="constantipy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[config_parent],
        usage="%(prog)s [options] [COMMAND]",
    )

    # Only meaningful in implicit/direct mode
    parser.add_argument(
        "--apply", action="store_true", help="Apply changes (files are modified)"
    )

    # Subparsers for advanced pipeline commands
    sub = parser.add_subparsers(
        dest="command",
        title="Advanced Pipeline Commands",
        description="Optional commands for CI/CD workflows.",
        metavar="COMMAND",
        required=False,
    )

    # REPORT command
    sub.add_parser(
        "report",
        help="Generate JSON report to stdout",
        parents=[config_parent],
        usage="%(prog)s report [options]",
    )

    # VALIDATE command
    sub.add_parser(
        "validate",
        help="Validate a report file",
        parents=[config_parent],  # inherits --report-file
        usage="%(prog)s validate [options]",
    )

    # REFACTOR command
    ref = sub.add_parser(
        "refactor",
        help="Read report from stdin and output diff",
        parents=[config_parent],
        usage="%(prog)s refactor [options]",
    )
    ref.add_argument("--apply", action="store_true", help="Modify files")

    return parser
