"""Crash-safe file writes.

Every checkpoint and status file is written to a temporary file in the same
folder, flushed to disk, then renamed over the old file. A rename is atomic
on Linux, so a power cut or ``kill -9`` leaves either the old file or the
new one, never a half-written mixture.
"""

import json
import os
import tempfile


def atomic_write_text(path, text, durable=True):
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            if durable:
                os.fsync(f.fileno())
        os.replace(tmp, path)
        if durable:
            try:
                dfd = os.open(folder, os.O_RDONLY)
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
            except OSError:
                pass
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path, obj, durable=True, indent=None):
    atomic_write_text(path, json.dumps(obj, indent=indent, sort_keys=True) + "\n", durable)


def read_json(path, default=None):
    """Read a JSON file; return ``default`` if it is missing or unreadable."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default
