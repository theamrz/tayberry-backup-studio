from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from ..errors import BackupCancelled
from ..config import OutputConfig, OutputFormat, extension_for_format

from ..scanning import ScanConfig, iter_files


@dataclass
class TreeStats:
    files_written: int = 0


def _write_tree_content(path: Path, lines: List[str], output_config: OutputConfig) -> None:
    body = "\n".join(lines)
    fmt = output_config.format
    if fmt == OutputFormat.MD:
        body = f"```text\n{body}\n```\n"
    elif fmt == OutputFormat.HTML:
        body = f"<pre>{html.escape(body)}</pre>\n"
    else:
        body += "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _write_tree(
    root: Path,
    output_name: str,
    output_config: OutputConfig,
    name_builder: Callable[[str, Optional[str]], Path],
    ts_only: bool = False,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> int:
    scan_config = ScanConfig(
        root=root,
        allowed_extensions={".ts", ".tsx"} if ts_only else None,
    )
    rel_paths: List[str] = []
    for path in iter_files(scan_config):
        if cancel_check and cancel_check():
            raise BackupCancelled()
        rel_paths.append(str(path.relative_to(root)))

    rel_paths.sort()

    lines: List[str] = []
    last_parts: List[str] = []

    for rel in rel_paths:
        parts = rel.split("/")
        # Find common prefix with previous path to reduce repetition
        common = 0
        while common < len(parts) and common < len(last_parts) and parts[common] == last_parts[common]:
            common += 1
        for depth in range(common, len(parts)):
            indent = "  " * depth
            lines.append(f"{indent}{parts[depth]}")
        last_parts = parts

    ext = extension_for_format(output_config.format)
    output_file = name_builder(output_name, ext_override=ext)
    _write_tree_content(output_file, lines, output_config)
    return len(rel_paths)


def generate_trees(
    project_root: Path,
    backup_dir: Path,
    output_config: OutputConfig,
    name_builder: Callable[[str, Optional[str]], Path],
    cancel_check: Optional[Callable[[], bool]] = None,
) -> TreeStats:
    stats = TreeStats()
    _ = backup_dir

    area_map = {
        "apps/admin": "admin_tree",
        "apps/api": "api_tree",
        "apps/site": "site_tree",
        "libs": "libs_tree",
    }

    for rel, name in area_map.items():
        root = project_root / rel
        if root.is_dir():
            stats.files_written += _write_tree(
                root,
                name,
                output_config,
                name_builder,
                ts_only=False,
                cancel_check=cancel_check,
            )

    # Full project trees
    stats.files_written += _write_tree(
        project_root,
        "tree",
        output_config,
        name_builder,
        ts_only=False,
        cancel_check=cancel_check,
    )
    stats.files_written += _write_tree(
        project_root,
        "tree_ts",
        output_config,
        name_builder,
        ts_only=True,
        cancel_check=cancel_check,
    )

    return stats
