from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from .code_bundles import read_text_with_limit
from ..config import (
    BackupProfileConfig,
    OutputConfig,
    OutputFormat,
    SeparatorStyle,
    get_separator_format,
    extension_for_format,
)
from ..errors import BackupCancelled
from ..scanning import ScanConfig, iter_files


@dataclass
class ApiBundleStats:
    files_written: int = 0
    files_included: int = 0


PATTERNS = {
    "services": ".service.ts",
    "controllers": ".controller.ts",
    "entities": ".entity.ts",
    "dtos": ".dto.ts",
}


def _collect_group_files(api_root: Path, suffix: str) -> List[Path]:
    scan = ScanConfig(root=api_root, allowed_extensions={".ts"})
    result: List[Path] = []
    for path in iter_files(scan):
        if path.name.endswith(suffix):
            result.append(path)
    return sorted(result)


def _format_header(rel: Path, output_config: OutputConfig) -> str:
    style = output_config.separator_style
    if output_config.format == OutputFormat.MD and style == SeparatorStyle.EQUALS:
        style = SeparatorStyle.MARKDOWN
    return get_separator_format(style, output_config.custom_separator).format(path=rel)


def _wrap_body(content: str, rel: Path, output_config: OutputConfig) -> str:
    if output_config.format == OutputFormat.MD:
        return f"```ts\n{content}\n```\n"
    if output_config.format == OutputFormat.HTML:
        return f"<pre>{html.escape(content)}</pre>\n"
    return content


def generate_api_bundles(
    project_root: Path,
    backup_dir: Path,
    profile: BackupProfileConfig,
    output_config: OutputConfig,
    name_builder: Callable[[str, Optional[str]], Path],
    warn: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> ApiBundleStats:
    stats = ApiBundleStats()
    _ = backup_dir
    api_root = project_root / "apps/api"
    if not api_root.is_dir():
        return stats

    ext = extension_for_format(output_config.format)

    for group, suffix in PATTERNS.items():
        files = _collect_group_files(api_root, suffix)
        if not files:
            continue
        out_file = name_builder(f"api_{group}", ext_override=ext)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with out_file.open("w", encoding="utf-8") as f:
            for path in files:
                if cancel_check and cancel_check():
                    raise BackupCancelled()
                stats.files_included += 1
                rel = path.relative_to(api_root)
                header = _format_header(rel, output_config)
                body = _wrap_body(
                    read_text_with_limit(path, profile.max_file_kb, warn=warn, cancel_check=cancel_check),
                    rel,
                    output_config,
                )
                if output_config.format == OutputFormat.HTML:
                    f.write(f"<section><h3>{rel}</h3>{body}</section>\n")
                else:
                    f.write(header)
                    f.write(body)
                    f.write("\n")
        stats.files_written += 1

    return stats
