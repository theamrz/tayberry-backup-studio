from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from ..scanning import ScanConfig, iter_files
from ..config import (
    BackupProfileConfig,
    OutputConfig,
    OutputFormat,
    SeparatorStyle,
    get_separator_format,
    extension_for_format,
)
from ..errors import BackupCancelled
from .code_bundles import read_text_with_limit


CONFIG_FILENAMES = {
    "package.json",
    "nx.json",
    "next.config.js",
    "next.config.mjs",
    "jest.config.js",
    "jest.config.mjs",
    "jest.config.ts",
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.cjs",
    ".prettierrc",
    ".prettierrc.js",
    ".prettierrc.cjs",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Dockerfile",
}


TS_CONFIG_FILES = [
    "tsconfig.json",
    "tsconfig.base.json",
    "apps/admin/tsconfig.json",
    "apps/api/tsconfig.json",
    "apps/site/tsconfig.json",
]


@dataclass
class ConfigBundleStats:
    files_written: int = 0
    files_included: int = 0
    configs_written: int = 0
    tsconfig_written: int = 0


def _collect_configs(project_root: Path) -> List[Path]:
    scan = ScanConfig(root=project_root, allowed_extensions=None)
    result: List[Path] = []
    for path in iter_files(scan):
        if path.name in CONFIG_FILENAMES and not path.name.startswith("tsconfig"):
            result.append(path)
    return sorted(result)


def _format_header(rel: Path, output_config: OutputConfig) -> str:
    style = output_config.separator_style
    if output_config.format == OutputFormat.MD and style == SeparatorStyle.EQUALS:
        style = SeparatorStyle.MARKDOWN
    return get_separator_format(style, output_config.custom_separator).format(path=rel)


def _wrap_body(content: str, rel: Path, output_config: OutputConfig) -> str:
    if output_config.format == OutputFormat.MD:
        lang = rel.suffix.lower().lstrip(".")
        return f"```{lang}\n{content}\n```\n"
    if output_config.format == OutputFormat.HTML:
        return f"<pre>{html.escape(content)}</pre>\n"
    return content


def generate_config_bundles(
    project_root: Path,
    backup_dir: Path,
    profile: BackupProfileConfig,
    output_config: OutputConfig,
    name_builder: Callable[[str, Optional[str]], Path],
    warn: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> ConfigBundleStats:
    stats = ConfigBundleStats()
    _ = backup_dir

    ext = extension_for_format(output_config.format)

    configs = _collect_configs(project_root)
    out_file = name_builder("configs", ext_override=ext)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as f:
        for path in configs:
            if cancel_check and cancel_check():
                raise BackupCancelled()
            stats.files_included += 1
            rel = path.relative_to(project_root)
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
    stats.configs_written += 1

    ts_out = name_builder("tsconfigs", ext_override=ext)
    ts_out.parent.mkdir(parents=True, exist_ok=True)
    with ts_out.open("w", encoding="utf-8") as f:
        for rel in TS_CONFIG_FILES:
            path = project_root / rel
            if not path.is_file():
                continue
            if cancel_check and cancel_check():
                raise BackupCancelled()
            stats.files_included += 1
            header = _format_header(Path(rel), output_config)
            body = _wrap_body(
                read_text_with_limit(path, profile.max_file_kb, warn=warn, cancel_check=cancel_check),
                Path(rel),
                output_config,
            )
            if output_config.format == OutputFormat.HTML:
                f.write(f"<section><h3>{rel}</h3>{body}</section>\n")
            else:
                f.write(header)
                f.write(body)
                f.write("\n")
    stats.files_written += 1
    stats.tsconfig_written += 1

    return stats
