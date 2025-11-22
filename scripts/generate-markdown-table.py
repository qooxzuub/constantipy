#!/usr/bin/env python3

import argparse

from constantipy.args import get_parser


def generate_markdown_table(parser: argparse.ArgumentParser):
    lines = ["| Flag | Description | Default |", "| :--- | :--- | :--- |"]
    for action in parser._actions:
        if action.option_strings:
            flags = ", ".join(f"`{opt}`" for opt in action.option_strings)
            default = (
                f"`{action.default}`"
                if action.default not in (None, False, True)
                else str(action.default)
            )
            lines.append(f"| {flags} | {action.help} | {default} |")
    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_markdown_table(get_parser()))
