from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Set

import os


DEFAULT_SKIP_DIRS: Set[str] = {
    "node_modules",
    ".next",
    ".turbo",
    "dist",
    "build",
    ".git",
    ".cache",
    "coverage",
    ".output",
    ".nx",
    ".vercel",
    ".expo",
    ".vscode",
    "tmp",
    "__pycache__",
    "venv",
    ".idea",
    "vendor",
    "Pods",
}

DEFAULT_SKIP_FILES: Set[str] = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "LICENSE",
    "CHANGELOG",
    ".DS_Store",
    "README.md",
}

DEFAULT_TEST_PATTERNS: Sequence[str] = (".spec.", ".test.", ".e2e-spec.")


@dataclass(frozen=True)
class ScanConfig:
    root: Path
    allowed_extensions: Optional[Set[str]] = None
    skip_dirs: Set[str] = frozenset(DEFAULT_SKIP_DIRS)
    skip_files: Set[str] = frozenset(DEFAULT_SKIP_FILES)
    skip_if_contains: Sequence[str] = DEFAULT_TEST_PATTERNS


def iter_files(config: ScanConfig) -> Iterator[Path]:
    """
    Walk the project tree under config.root, yielding files
    while skipping heavy or irrelevant directories and files.
    """
    root = config.root
    allowed_exts = config.allowed_extensions

    for dirpath, dirnames, filenames in os.walk(root):
        # Strip skipped directories in-place so os.walk does not enter them.
        dirnames[:] = [
            d for d in dirnames if d not in config.skip_dirs
        ]

        current_dir = Path(dirpath)
        for filename in filenames:
            if filename in config.skip_files:
                continue
            if any(pattern in filename for pattern in config.skip_if_contains):
                continue
            path = current_dir / filename
            if allowed_exts is not None and path.suffix not in allowed_exts:
                continue
            yield path


def iter_files_for_extensions(root: Path, exts: Iterable[str]) -> Iterator[Path]:
    return iter_files(ScanConfig(root=root, allowed_extensions=set(exts)))


def iter_project_areas(project_root: Path) -> List[Path]:
    """
    Return standard TBcms areas under a monorepo-style project.
    """
    areas: List[Path] = []
    for rel in ("apps/admin", "apps/api", "apps/site", "libs"):
        p = project_root / rel
        if p.is_dir():
            areas.append(p)
    return areas
