"""Find regular descendant files without traversing redirected paths."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path


def is_local_entry(path: Path) -> bool:
    try:
        # On Python 3.11 a Windows junction can resolve elsewhere without
        # being reported as a symbolic link.
        return not path.is_symlink() and path.resolve() == path
    except (OSError, RuntimeError):
        return False


def iter_local_files(
    root: Path, repo: Path, should_skip: Callable[[Path], bool]
) -> Iterator[Path]:
    for directory, dirs, files in os.walk(root):
        current = Path(directory)
        for folder in dirs[:]:
            child = current / folder
            if should_skip(child.relative_to(repo)) or not is_local_entry(child):
                dirs.remove(folder)
        for filename in files:
            child = current / filename
            if not should_skip(child.relative_to(repo)) and is_local_entry(child):
                yield child
