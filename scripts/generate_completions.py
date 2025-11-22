#!/usr/bin/env python3
"""
Generates shell completion scripts for Bash, Zsh, and Tcsh.
Also generates a README.md with installation instructions.
"""
from pathlib import Path
import shtab
from constantipy.cli import get_parser

# Define output filenames
SHELL_MAP = {
    "bash": "constantipy.bash",
    "zsh": "_constantipy",
    "tcsh": "constantipy.tcsh",
}

ROOT_DIR = Path(__file__).parent.parent
COMPLETIONS_DIR = ROOT_DIR / "completions"

README_TEMPLATE = """# Shell Completions

This directory contains auto-generated shell completion scripts for `constantipy`.

## Installation

### Bash

Source the script in your `~/.bashrc`:

```bash
source /path/to/constantipy/completions/{bash_file}
````

### Zsh

Add this directory to your `$fpath` in `~/.zshrc` **before** `compinit` is called:

```zsh
fpath=(/path/to/constantipy/completions $fpath)
autoload -Uz compinit && compinit
```

### Tcsh

Source the script in your `~/.tcshrc` or `~/.cshrc`:

```tcsh
source /path/to/constantipy/completions/{tcsh_file}
```

"""


def main():
    """Main"""
    print(f"Generating completions in {COMPLETIONS_DIR}...")
    COMPLETIONS_DIR.mkdir(exist_ok=True)

    parser = get_parser()

    for shell, filename in SHELL_MAP.items():
        out_file = COMPLETIONS_DIR / filename
        print(f"  - {shell} -> {filename}")

        # shtab.complete generates the raw script content
        content = shtab.complete(parser, shell=shell)
        out_file.write_text(content, encoding="utf-8")

    # Generate README
    readme_path = COMPLETIONS_DIR / "README.md"
    print(f"  - Documentation -> {readme_path.name}")

    readme_content = README_TEMPLATE.format(
        bash_file=SHELL_MAP["bash"], tcsh_file=SHELL_MAP["tcsh"]
    )
    readme_path.write_text(readme_content, encoding="utf-8")


if __name__ == "__main__":
    main()
