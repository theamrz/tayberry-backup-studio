from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

from ..config import SearchSetConfig
from ..errors import BackupCancelled
from ..scanning import ScanConfig, iter_files
from .code_bundles import read_text_with_limit


@dataclass
class SearchStats:
    files_written: int = 0
    matches: int = 0


def _search_files(
    root: Path,
    search_set: SearchSetConfig,
    max_kb: int,
    output_dir: Path,
    warn: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> SearchStats:
    stats = SearchStats()
    scan = ScanConfig(root=root, allowed_extensions=set(search_set.extensions))
    keywords_lower = [k.lower() for k in search_set.keywords]
    matches: List[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"Search_{search_set.id}.md"
    with out_file.open("w", encoding="utf-8") as f:
        for path in iter_files(scan):
            if cancel_check and cancel_check():
                raise BackupCancelled()
            text = read_text_with_limit(path, max_kb, warn=warn, cancel_check=cancel_check)
            lower = text.lower()
            if any(k in lower for k in keywords_lower):
                rel = path.relative_to(root)
                f.write(f"## {rel}\n\n")
                f.write("```text\n")
                f.write(text)
                f.write("\n```\n\n")
                matches.append(str(rel))
    stats.files_written += 1
    stats.matches = len(matches)
    return stats


def run_search_sets(
    project_root: Path,
    search_sets: Iterable[SearchSetConfig],
    max_kb: int,
    output_dir: Path,
    warn: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Dict[str, SearchStats]:
    results: Dict[str, SearchStats] = {}
    for sset in search_sets:
        stats = _search_files(
            project_root,
            sset,
            max_kb=max_kb,
            output_dir=output_dir,
            warn=warn,
            cancel_check=cancel_check,
        )
        results[sset.id] = stats
    return results
