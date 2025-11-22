"""
Heuristics for generating constant names from literal values.
"""

import hashlib
import re
from typing import Any, Optional, Union


def split_camel_case(text: str) -> str:
    """Splits CamelCase strings into underscore_separated strings."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", text)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)


def _name_from_str(val: str, idx: int, type_hint: Optional[str]) -> str:
    """Generates a name for a string value."""
    # --- FIX: Handle empty strings explicitly ---
    if not val:
        return "STR_EMPTY"

    processed = split_camel_case(val)
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", processed)
    clean = re.sub(r"_+", "_", clean).strip("_").upper()

    if not clean or clean[0].isdigit():
        clean = f"STR_{clean}"

    if type_hint == "regex" and not clean.endswith("_RE"):
        clean += "_RE"
    elif type_hint == "sql" and not clean.endswith("_SQL"):
        clean += "_SQL"
    elif type_hint == "url" and not clean.endswith("_URL"):
        clean += "_URL"
    elif type_hint == "path" and not clean.endswith("_PATH"):
        clean += "_PATH"

    if len(clean) > 50:
        # --- FIX: Truncate to 46 chars so adding "_ETC" (4 chars) totals 50 ---
        clean = clean[:46] + "_ETC"
    if len(clean) < 3:
        clean = f"STR_CONST_{idx}"
    return clean


def _name_from_int(val: int) -> str:
    """Generates a name for an integer value."""
    s_val = str(val).replace("-", "NEG_")
    return f"INT_{s_val}"


def _name_from_float(val: float) -> str:
    """Generates a name for a float value."""
    s_val = str(val).replace(".", "_").replace("-", "NEG_").replace("+", "_")
    return f"FLOAT_{s_val}"


def _name_from_bytes(val: bytes) -> str:
    """Generates a name for a bytes value."""
    try:
        s_val = val.decode("ascii")
        if s_val.isprintable():
            clean = re.sub(r"[^a-zA-Z0-9]+", "_", s_val).strip("_").upper()
            if clean:
                return f"BYTES_{clean}"[:50]
    except UnicodeDecodeError:
        pass
    h = hashlib.md5(val).hexdigest()[:8].upper()
    return f"BYTES_{h}"


def generate_name(
    val: Union[str, int, float, bytes],
    strategy: str,
    idx: int,
    type_hint: Optional[str] = None,
) -> str:
    """Generates a valid Python identifier for a given constant value."""
    if strategy == "generic":
        return f"CONST_{idx}"

    if isinstance(val, str):
        return _name_from_str(val, idx, type_hint)
    if isinstance(val, int):
        return _name_from_int(val)
    if isinstance(val, float):
        return _name_from_float(val)
    if isinstance(val, bytes):
        return _name_from_bytes(val)

    # --- FIX: Raise TypeError for unsupported types ---
    raise TypeError(f"Unsupported type for constant generation: {type(val)}")


def determine_type_hint(val: Any, is_regex_arg: bool) -> Optional[str]:
    """Determines the type/context of a string (SQL, URL, Path) for naming."""
    if not isinstance(val, str):
        return None
    if is_regex_arg:
        return "regex"

    stripped = val.strip().upper()
    if stripped.startswith(("SELECT ", "INSERT ", "UPDATE ", "DELETE ", "CREATE ")):
        return "sql"
    if val.strip().startswith(("http://", "https://")):
        return "url"
    if val.strip().startswith(("/", "./", "../")):
        return "path"
    return None
