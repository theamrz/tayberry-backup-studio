from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from ..scanning import ScanConfig, iter_files
from ..config import OutputConfig, OutputFormat, extension_for_format
from ..errors import BackupCancelled


@dataclass
class PathsStats:
    files_written: int = 0
    paths_total: int = 0
    ts_paths_total: int = 0


def _write_content(
    path: Path,
    body: str,
    output_config: OutputConfig,
    heading: str | None = None,
) -> None:
    fmt = output_config.format

    if fmt == OutputFormat.MD:
        header = f"### {heading}\n\n" if heading else ""
        body = f"{header}```text\n{body}\n```\n"
    elif fmt == OutputFormat.HTML:
        header = f"<h3>{heading}</h3>\n" if heading else ""
        body = f"{header}<pre>{html.escape(body)}</pre>\n"
    else:
        if not body.endswith("\n"):
            body += "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def generate_paths_files(
    project_root: Path,
    backup_dir: Path,
    output_config: OutputConfig,
    name_builder: Callable[[str, Optional[str]], Path],
    cancel_check: Optional[Callable[[], bool]] = None,
) -> PathsStats:
    stats = PathsStats()
    _ = backup_dir

    ext = extension_for_format(output_config.format)

    scan_all = ScanConfig(root=project_root, allowed_extensions=None)
    all_paths: List[Path] = list(iter_files(scan_all))
    all_paths.sort()

    # paths: one path per line
    if cancel_check and cancel_check():
        raise BackupCancelled()
    path_lines = "\n".join(str(p) for p in all_paths)
    test_path_file = name_builder("paths", ext_override=ext)
    _write_content(test_path_file, path_lines, output_config, heading="All paths")
    stats.files_written += 1
    stats.paths_total = len(all_paths)

    # paths_ts: TS/TSX, single line, separated by /|\
    ts_paths = [p for p in all_paths if p.suffix in {".ts", ".tsx"}]
    ts_paths.sort()
    if cancel_check and cancel_check():
        raise BackupCancelled()
    joined = "/|\\".join(str(p) for p in ts_paths)
    ts_path_file = name_builder("paths_ts", ext_override=ext)
    _write_content(ts_path_file, joined, output_config, heading="TypeScript-only paths")
    stats.files_written += 1
    stats.ts_paths_total = len(ts_paths)

    return stats
