from __future__ import annotations

import json
import os
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

_LOCKS: dict[Path, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def update_json_index(
    path: Path,
    *,
    load: Callable[[], T],
    save: Callable[[T], object],
    mutate: Callable[[T], T],
) -> T:
    lock = _lock_for(path)
    with lock:
        state = mutate(load())
        save(state)
        return state


def write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(payload, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def locked(path: Path) -> threading.RLock:
    return _lock_for(path)


def _lock_for(path: Path) -> threading.RLock:
    resolved = path.resolve()
    with _LOCKS_GUARD:
        lock = _LOCKS.get(resolved)
        if lock is None:
            lock = threading.RLock()
            _LOCKS[resolved] = lock
        return lock
