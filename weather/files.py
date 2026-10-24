"""Saving text files safely."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_safely(path: Path, text: str) -> None:
    """Write to a temporary file, then swap it in, so a crash half way
    through never leaves a broken file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp_", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as temp_file:
            temp_file.write(text)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise
