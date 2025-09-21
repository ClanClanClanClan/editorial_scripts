"""Storage utilities: checksum and mime helpers."""

import hashlib
import mimetypes
from pathlib import Path


def compute_checksum(path: Path, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def guess_mime_type(path: Path) -> str:
    mtype, _ = mimetypes.guess_type(str(path))
    return mtype or "application/octet-stream"
