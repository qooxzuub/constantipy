# Constantipy 🪄

**The Magic Removal Tool.**

Constantipy is a CLI tool that automatically refactors "magic" literals (strings, numbers, bytes) in your Python codebase into named constants.

It scans your project, identifies repeated literals, names them intelligently (e.g., `"SELECT *"` &rarr; `STR_SELECT_SQL`), and refactors your code to import them from a central `constants.py` or define them locally.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Zero Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)

---

## Features

* **Zero Runtime Dependencies**: Runs on standard library only.
* **Smart Naming Heuristics**:
    * Auto-detects SQL (`STR_SELECT_SQL`), URLs (`HTTPS_GOOGLE_COM_URL`), and Regex patterns.
    * Splits CamelCase (`FieldState` &rarr; `STR_FIELD_STATE`).
* **Scope Detection**:
    * **Global**: Strings used in multiple files are moved to `constants.py`.
    * **Local**: Strings used in only one file are defined at the top of that file (keeps your global constants file clean).
* **Safety First**:
    * Ignores f-strings (`f"Hello {name}"`) to prevent breaking interpolation.
    * Ignores docstrings.
    * Checks for variable name collisions before generating constants.
    * Ignores structural numbers (0, 1, 2, -1) by default.
* **Granular Control**:
    * Ignore specific values (`--ignore-str desc`, `--ignore-num 404`).
    * Ignore specific types (`--no-ints`, `--no-floats`).
    * Ignore specific function calls (like `logging.debug`).

## Installation

```bash
pip install constantipy
```

## ⚡️ Quick Example

**Before Constantipy:**

```python
# db_utils.py
import time
import logging

def fetch_users(retries=3):
    # Magic String (SQL)
    query = "SELECT * FROM users WHERE active = 1"

    if retries > 0:
        # Magic String inside logging (can be ignored via config)
        logging.debug("Attempting connection...")
        # Magic Number
        time.sleep(60)

    return "Success"
```

**After running `constantipy apply`:**

```python
# db_utils.py
import time
import logging
from constants import STR_SELECT_SQL, STR_SUCCESS, INT_60

def fetch_users(retries=3):
    # Magic String (SQL)
    query = STR_SELECT_SQL

    if retries > 0:
        # Magic String inside logging (can be ignored via config)
        logging.debug("Attempting connection...")
        # Magic Number
        time.sleep(INT_60)

    return STR_SUCCESS
```

---

## Usage

### 1. Direct Mode
Scan the codebase and preview or apply changes

#### Dry Run (Preview changes to stdout)
```bash
constantipy
```

#### Apply changes to files
```bash
constantipy --apply
```

### 2. Pipeline Mode
Generate a JSON report, review/edit it manually, and then apply the refactoring.

#### Generate Report
```bash
constantipy report > report.json
```
#### Edit report manually (optional)
#### Validate Report
```bash
constantipy validate < report.json
```
#### Apply refactoring from report
```bash
constantipy refactor --apply < report.json
```

## Configuration

You can fine-tune the extraction process using command-line flags:

| Flag | Description | Default |
| :--- | :--- | :--- |
| `--apply` | Apply detected changes to files (direct mode only) | False |
| `--constants-file` | File name for storing global constants | `constants.py` |
| `--exclude` | Directories to exclude | None |
| `--extra-constants` | Additional Python files to scan for constants | None |
| `--ignore-call` | Ignore specific function calls during scanning | None |
| `--min-count` | Minimum occurrences for a constant to be considered | `2` |
| `--min-length` | Minimum length for string literals | `4` |
| `--naming {generic,derived}` | Strategy for naming generated constants | `derived` |
| `--no-local-scope` | Force all constants to be global (ignore local scope) | False |
| `--path` | Path to scan or refactor (default: current directory) | `.` |

### Numeric & Type Controls

| Flag | Description |
| :--- | :--- |
| `--ignore-num X` | Explicitly ignore number X (e.g. `--ignore-num 42`) |
| `--ignore-str S` | Explicitly ignore string S (e.g. `--ignore-str "foo"`) |
| `--include-num X` | Explicitly extract number X (overrides default ignore) |
| `--no-bytes` | Skip bytes scanning |
| `--no-floats` | Skip float scanning |
| `--no-ints` | Skip integer scanning |
| `--no-numbers` | Disable ALL magic number extraction |

## Safety Warning ⚠️

**Constantipy modifies your source code.**

While it contains safety checks (AST parsing, collision detection), automated refactoring always carries risk.

1.  Always commit your changes to git before running with `--apply`.
2.  Run your test suite immediately after applying.

## License

MIT
