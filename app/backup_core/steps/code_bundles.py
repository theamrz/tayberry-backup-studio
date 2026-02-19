from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple

from ..errors import BackupCancelled
from ..config import (
    BackupProfileConfig,
    OutputConfig,
    OutputFormat,
    SeparatorStyle,
    get_separator_format,
    extension_for_format,
)
from ..scanning import ScanConfig, iter_files


@dataclass
class CodeBundleStats:
    files_written: int = 0
    files_included: int = 0


def read_text_with_limit(
    path: Path,
    max_kb: int,
    warn: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> str:
    """
    Read a text file up to max_kb kilobytes.

    If the file is larger, truncate and append a comment line indicating truncation.
    """
    if cancel_check and cancel_check():
        raise BackupCancelled()
    max_bytes = max_kb * 1024
    try:
        data = path.read_bytes()
        truncated = False
        if len(data) > max_bytes:
            data = data[:max_bytes]
            truncated = True
        text = data.decode("utf-8", errors="replace")
        if truncated:
            text += "\n\n# [TRUNCATED DUE TO SIZE]\n"
        return text
    except BackupCancelled:
        raise
    except Exception as exc:  # noqa: BLE001
        if warn:
            warn(f"Warning: could not read {path}: {exc}")
        return f"# [UNREADABLE FILE: {path} | {exc}]"


def _add_line_numbers(text: str) -> str:
    lines = text.split("\n")
    width = len(str(len(lines) or 1))
    return "\n".join(f"{i:>{width}} | {line}" for i, line in enumerate(lines, 1))


def _collect_files(root: Path, exts: Iterable[str]) -> List[Path]:
    scan_config = ScanConfig(root=root, allowed_extensions=set(exts))
    return sorted(iter_files(scan_config))


def _format_header(rel: Path, output_config: OutputConfig) -> str:
    style = output_config.separator_style
    if output_config.format == OutputFormat.MD and style == SeparatorStyle.EQUALS:
        style = SeparatorStyle.MARKDOWN
    fmt = get_separator_format(style, output_config.custom_separator)
    return fmt.format(path=rel)


def _wrap_body(content: str, rel: Path, output_config: OutputConfig) -> str:
    if output_config.include_line_numbers:
        content = _add_line_numbers(content)

    if output_config.format == OutputFormat.MD or output_config.wrap_in_code_block:
        lang = rel.suffix.lower().lstrip(".")
        return f"```{lang}\n{content}\n```\n"
    if output_config.format == OutputFormat.HTML:
        return f"<pre>{html.escape(content)}</pre>\n"
    return content


def _write_markdown_bundle(
    files: Iterable[Path],
    root: Path,
    output_file: Path,
    max_kb: int,
    warn: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Tuple[int, int]:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    included = 0
    with output_file.open("w", encoding="utf-8") as f:
        for path in files:
            if cancel_check and cancel_check():
                raise BackupCancelled()
            included += 1
            rel = path.relative_to(root)
            f.write(f"## {rel}\n\n```ts\n")
            f.write(read_text_with_limit(path, max_kb, warn=warn, cancel_check=cancel_check))
            f.write("\n```\n\n")
    return 1, included


def _write_text_bundle(
    files: Iterable[Path],
    root: Path,
    output_file: Path,
    max_kb: int,
    output_config: OutputConfig,
    warn: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Tuple[int, int]:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    included = 0
    with output_file.open("w", encoding="utf-8") as f:
        for path in files:
            if cancel_check and cancel_check():
                raise BackupCancelled()
            included += 1
            rel = path.relative_to(root)
            header = _format_header(rel, output_config)
            content = read_text_with_limit(path, max_kb, warn=warn, cancel_check=cancel_check)
            body = _wrap_body(content, rel, output_config)

            if output_config.format == OutputFormat.HTML:
                f.write(f"<section><h3>{rel}</h3>{body}</section>\n")
            else:
                f.write(header)
                f.write(body)
                f.write("\n")
    return 1, included


def generate_ts_bundles(
    project_root: Path,
    backup_dir: Path,
    profile: BackupProfileConfig,
    stamp: str,
    name_builder: Callable[[str, Optional[str]], Path],
    warn: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> CodeBundleStats:
    stats = CodeBundleStats()
    _ = backup_dir
    ts_exts = profile.allowed_ts_extensions

    area_to_name = {
        "apps/admin": "admin",
        "apps/api": "api",
        "apps/site": "site",
        "libs": "libs",
    }

    ext_md = extension_for_format(OutputFormat.MD)
    for rel, filename in area_to_name.items():
        root = project_root / rel
        if not root.is_dir():
            continue
        files = _collect_files(root, ts_exts)
        if not files:
            continue
        fw, inc = _write_markdown_bundle(
            files,
            root=root,
            output_file=name_builder(filename, ext_override=ext_md),
            max_kb=profile.max_file_kb,
            warn=warn,
            cancel_check=cancel_check,
        )
        stats.files_written += fw
        stats.files_included += inc

    return stats


def generate_full_ts_bundle(
    project_root: Path,
    backup_dir: Path,
    profile: BackupProfileConfig,
    stamp: str,
    name_builder: Callable[[str, Optional[str]], Path],
    warn: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> CodeBundleStats:
    stats = CodeBundleStats()
    _ = backup_dir
    files = _collect_files(project_root, profile.allowed_ts_extensions)
    if files:
        ext_md = extension_for_format(OutputFormat.MD)
        fw, inc = _write_markdown_bundle(
            files,
            root=project_root,
            output_file=name_builder("ts_full_bundle", ext_override=ext_md),
            max_kb=profile.max_file_kb,
            warn=warn,
            cancel_check=cancel_check,
        )
        stats.files_written += fw
        stats.files_included += inc
    return stats


def generate_full_text_bundles(
    project_root: Path,
    backup_dir: Path,
    profile: BackupProfileConfig,
    stamp: str,
    output_config: OutputConfig,
    name_builder: Callable[[str, Optional[str]], Path],
    warn: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> CodeBundleStats:
    stats = CodeBundleStats()
    _ = backup_dir
    full_exts = profile.allowed_full_extensions
    ext = extension_for_format(output_config.format)

    area_to_name = {
        "apps/admin": "admin_code",
        "apps/api": "api_code",
        "apps/site": "site_code",
        "libs": "libs_code",
    }

    for rel, filename in area_to_name.items():
        root = project_root / rel
        if not root.is_dir():
            continue
        files = _collect_files(root, full_exts)
        if not files:
            continue
        fw, inc = _write_text_bundle(
            files,
            root=root,
            output_file=name_builder(filename, ext_override=ext),
            max_kb=profile.max_file_kb,
            output_config=output_config,
            warn=warn,
            cancel_check=cancel_check,
        )
        stats.files_written += fw
        stats.files_included += inc

    # Full project text bundle
    files = _collect_files(project_root, full_exts)
    if files:
        fw, inc = _write_text_bundle(
            files,
            root=project_root,
            output_file=name_builder("all_code", ext_override=ext),
            max_kb=profile.max_file_kb,
            output_config=output_config,
            warn=warn,
            cancel_check=cancel_check,
        )
        stats.files_written += fw
        stats.files_included += inc

    return stats
