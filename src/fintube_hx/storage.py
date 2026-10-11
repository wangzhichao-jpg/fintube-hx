"""UTF-8 project files with strict JSON and atomic writes."""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import tempfile


def _invalid_constant(value):
    raise ValueError(f"Non-standard JSON constant {value} is not allowed")


def _finite_json_float(text):
    value=float(text)
    if not math.isfinite(value):
        raise ValueError(f"Out-of-range JSON number: {text}")
    return value


def load_case(path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"), parse_constant=_invalid_constant, parse_float=_finite_json_float)
    if not isinstance(data, dict):
        raise ValueError("Project must contain a JSON object")
    return data


def save_json(path, data) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
    fd, temporary = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            file.write(text + "\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
