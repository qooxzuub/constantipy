"""
Argument parsing for Constantipy.

Global options work anywhere in the CLI. Subcommands are optional,
with a default direct mode when no command is specified.
"""

import argparse


def _create_global_parser() -> argparse.ArgumentParser:
    """
    Creates a parser with all global options.

    This parser is used as the parent for subcommands to inherit
    global options without duplicating them.
    """
    parser = argparse.ArgumentParser(add_help=False)

    # Base configuration
    parser.add_argument(
        "--path",
        default=".",
        help="Path to scan or refactor (default: current directory)",
    )
    parser.add_argument(
        "--constants-file",
        default="constants.py",
        help="File name for storing global constants",
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
        help="Minimum occurrences for a constant to be considered (default: 2)",
    )
    parser.add_argument(
        "--no-local-scope",
        action="store_true",
        help="Force all constants to be global (ignore local scope)",
    )

    # Filtering and exclusion
    parser.add_argument(
        "--ignore-call",
        action="append",
        help="Ignore specific function calls during scanning",
    )
    parser.add_argument("--exclude", action="append", help="Directories to exclude")
    parser.add_argument("--ignore-num", action="append", help="Numbers to ignore")
    parser.add_argument(
        "--include-num", action="append", help="Numbers to include (un-ignore)"
    )
    parser.add_argument("--ignore-str", action="append", help="Strings to ignore")

    # Type-specific scanning
    parser.add_argument(
        "--no-numbers", action="store_true", help="Skip number scanning"
    )
    parser.add_argument("--no-ints", action="store_true", help="Skip integer scanning")
    parser.add_argument("--no-floats", action="store_true", help="Skip float scanning")
    parser.add_argument("--no-bytes", action="store_true", help="Skip bytes scanning")

    # Naming strategy
    parser.add_argument(
        "--naming",
        choices=["derived", "generic"],
        default="derived",
        help="Strategy for naming generated constants",
    )

    # Extra files containing constants
    parser.add_argument(
        "--extra-constants",
        nargs="*",
        help="Additional Python files to scan for constants",
    )

    return parser


def get_parser() -> argparse.ArgumentParser:
    """
    Returns the main CLI parser.

    Option 2 semantics:
      - Global options work anywhere (before or after a subcommand)
      - Subcommands are optional
      - Default direct mode runs if no command is given
    """
    global_parser = _create_global_parser()

    description = """
Constantipy: Find and refactor magic literals.

MODES OF OPERATION:

1. Direct Mode (Default):
   Run without a command to scan the path and preview changes.
   Use --apply to modify files in place.

   Example:
       $ constantipy --path src/
       $ constantipy --path src/ --apply

2. Pipeline Mode (Advanced):
   Use subcommands to generate, validate, and process JSON reports.
"""

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[global_parser],
        usage="%(prog)s [OPTIONS] [COMMAND [COMMAND_OPTIONS]]",
    )

    # Apply changes in direct mode
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply detected changes to files (direct mode only)",
    )

    # Subparsers for pipeline commands
    sub = parser.add_subparsers(
        dest="command",
        title="Pipeline Commands",
        description="Advanced commands for CI/CD workflows",
        metavar="COMMAND",
        required=False,
    )

    # REPORT subcommand
    sub.add_parser(
        "report",
        help="Generate JSON report of constants to stdout",
        parents=[],  # Do not re-include global options to prevent conflicts
        usage="%(prog)s report [OPTIONS]",
    )

    # VALIDATE subcommand
    validate = sub.add_parser(
        "validate",
        help="Validate an existing JSON report file",
        parents=[],  # Global options not needed for validate
        usage="%(prog)s validate [OPTIONS]",
    )
    validate.add_argument(
        "--report-file",
        default="constantipy_report.json",
        required=True,
        help="Path to the report file to validate",
    )

    # REFACTOR subcommand
    refactor = sub.add_parser(
        "refactor",
        help="Read JSON report from stdin and apply refactoring",
        parents=[],  # Use direct mode globals only if needed
        usage="%(prog)s refactor [OPTIONS]",
    )
    refactor.add_argument(
        "--apply",
        action="store_true",
        help="Apply detected changes to files",
    )

    return parser
