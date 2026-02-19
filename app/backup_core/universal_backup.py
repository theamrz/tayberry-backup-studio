"""
Universal backup module.

Provides flexible backup functionality supporting:
- Custom file extensions
- Exclude patterns
- Multiple output formats (TXT, MD, HTML)
- Custom file separators
- Single file or multi-file output
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Set
import os
import re

from .config import (
    ExcludeConfig,
    OutputConfig,
    OutputFormat,
    SeparatorStyle,
    get_separator_format,
    FILE_EXTENSION_PRESETS,
    COMMON_EXCLUDE_FOLDERS,
)
from .errors import BackupCancelled, BackupIOError


@dataclass
class UniversalBackupConfig:
    """Configuration for universal backup."""
    source_root: Path
    output_dir: Path
    output_filename: str = "backup"
    
    # File selection
    extensions: List[str] = field(default_factory=lambda: [".ts", ".tsx", ".js", ".jsx"])
    extension_presets: List[str] = field(default_factory=list)
    
    # Exclusions
    exclude_folders: Set[str] = field(default_factory=lambda: set(COMMON_EXCLUDE_FOLDERS))
    exclude_files: Set[str] = field(default_factory=set)
    exclude_patterns: List[str] = field(default_factory=list)  # Regex patterns
    exclude_hidden: bool = True
    
    # Output settings
    output_format: OutputFormat = OutputFormat.TXT
    separator_style: SeparatorStyle = SeparatorStyle.EQUALS
    custom_separator: Optional[str] = None
    
    # Content options
    include_line_numbers: bool = False
    include_file_stats: bool = True
    wrap_in_code_block: bool = False
    max_file_kb: int = 256
    
    # Split options
    split_by_folder: bool = False  # Create separate files per top-level folder
    
    def get_all_extensions(self) -> Set[str]:
        """Get all extensions including presets."""
        exts = set(self.extensions)
        for preset_name in self.extension_presets:
            if preset_name in FILE_EXTENSION_PRESETS:
                exts.update(FILE_EXTENSION_PRESETS[preset_name])
        return exts


@dataclass
class BackupFileInfo:
    """Information about a file to backup."""
    path: Path
    relative_path: Path
    size_bytes: int
    line_count: int = 0


@dataclass
class UniversalBackupStats:
    """Statistics from backup operation."""
    total_files: int = 0
    total_size_bytes: int = 0
    files_included: int = 0
    files_excluded: int = 0
    files_truncated: int = 0
    output_files_created: int = 0
    output_paths: List[Path] = field(default_factory=list)


def _count_lines(content: str) -> int:
    """Count lines in content."""
    return content.count('\n') + (1 if content and not content.endswith('\n') else 0)


def _add_line_numbers(content: str) -> str:
    """Add line numbers to content."""
    lines = content.split('\n')
    width = len(str(len(lines)))
    numbered = []
    for i, line in enumerate(lines, 1):
        numbered.append(f"{i:>{width}} | {line}")
    return '\n'.join(numbered)


def _get_language_hint(path: Path) -> str:
    """Get language hint for code blocks based on file extension."""
    mapping = {
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".jsx": "jsx",
        ".py": "python",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".sql": "sql",
        ".sh": "bash",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".kt": "kotlin",
        ".vue": "vue",
        ".svelte": "svelte",
    }
    return mapping.get(path.suffix.lower(), "")


def _should_exclude(
    path: Path,
    config: UniversalBackupConfig,
) -> bool:
    """Check if a path should be excluded."""
    name = path.name
    
    # Check hidden files/folders
    if config.exclude_hidden and name.startswith('.') and name not in ['.env']:
        return True
    
    # Check excluded files
    if name in config.exclude_files:
        return True
    
    # Check excluded folders
    for part in path.parts:
        if part in config.exclude_folders:
            return True
    
    # Check exclude patterns (regex)
    str_path = str(path)
    for pattern in config.exclude_patterns:
        try:
            if re.search(pattern, str_path):
                return True
        except re.error:
            pass
    
    return False


def iter_backup_files(
    config: UniversalBackupConfig,
    cancel_check: Optional[Callable[[], None]] = None,
) -> Iterator[BackupFileInfo]:
    """
    Iterate over files to backup based on configuration.
    
    Yields BackupFileInfo for each matching file.
    """
    root = config.source_root
    allowed_exts = config.get_all_extensions()
    
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out excluded directories in-place
        dirnames[:] = [
            d for d in dirnames
            if d not in config.exclude_folders
            and not (config.exclude_hidden and d.startswith('.'))
        ]
        
        current_dir = Path(dirpath)
        
        for filename in filenames:
            if cancel_check:
                cancel_check()
            
            file_path = current_dir / filename
            
            # Check extension
            if allowed_exts and file_path.suffix.lower() not in allowed_exts:
                continue
            
            # Check exclusions
            if _should_exclude(file_path, config):
                continue
            
            # Get file info
            try:
                stat = file_path.stat()
                yield BackupFileInfo(
                    path=file_path,
                    relative_path=file_path.relative_to(root),
                    size_bytes=stat.st_size,
                )
            except (OSError, IOError):
                continue


def read_file_content(
    path: Path,
    max_kb: int = 256,
    add_line_numbers: bool = False,
) -> tuple[str, bool, int]:
    """
    Read file content with size limit.
    
    Returns: (content, was_truncated, line_count)
    """
    max_bytes = max_kb * 1024
    truncated = False
    
    try:
        data = path.read_bytes()
        if len(data) > max_bytes:
            data = data[:max_bytes]
            truncated = True
        
        content = data.decode("utf-8", errors="replace")
        line_count = _count_lines(content)
        
        if add_line_numbers:
            content = _add_line_numbers(content)
        
        return content, truncated, line_count
    except Exception as exc:
        return f"[Error reading file: {exc}]", False, 0


def format_file_header(
    file_info: BackupFileInfo,
    config: UniversalBackupConfig,
    line_count: int = 0,
) -> str:
    """Format the header for a file in the backup."""
    sep_format = get_separator_format(config.separator_style, config.custom_separator)
    header = sep_format.format(path=str(file_info.relative_path))
    
    if config.include_file_stats:
        size_kb = file_info.size_bytes / 1024
        stats_line = f"[Size: {size_kb:.1f}KB"
        if line_count > 0:
            stats_line += f" | Lines: {line_count}"
        stats_line += "]\n"
        header += stats_line
    
    return header


def format_file_content(
    content: str,
    file_info: BackupFileInfo,
    config: UniversalBackupConfig,
    truncated: bool = False,
) -> str:
    """Format file content for output."""
    output = []
    
    if config.wrap_in_code_block or config.output_format == OutputFormat.MD:
        lang = _get_language_hint(file_info.path)
        output.append(f"```{lang}\n")
        output.append(content)
        if not content.endswith('\n'):
            output.append('\n')
        output.append("```\n")
    else:
        output.append(content)
        if not content.endswith('\n'):
            output.append('\n')
    
    if truncated:
        output.append("\n[TRUNCATED DUE TO SIZE]\n")
    
    return ''.join(output)


def generate_html_wrapper(title: str, content: str) -> str:
    """Wrap content in HTML document."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: 'SF Mono', Monaco, 'Courier New', monospace; background: #1a1a2e; color: #eee; padding: 20px; }}
        .file-block {{ background: #16213e; border-radius: 8px; margin: 16px 0; padding: 16px; }}
        .file-header {{ color: #4fc3f7; font-weight: bold; border-bottom: 1px solid #333; padding-bottom: 8px; margin-bottom: 12px; }}
        .file-stats {{ color: #888; font-size: 0.85em; }}
        pre {{ margin: 0; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }}
        code {{ display: block; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>Generated: {datetime.now().isoformat()}</p>
    {content}
</body>
</html>"""


def run_universal_backup(
    config: UniversalBackupConfig,
    cancel_check: Optional[Callable[[], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> UniversalBackupStats:
    """
    Run a universal backup with the given configuration.
    
    Args:
        config: Backup configuration
        cancel_check: Optional callback to check for cancellation
        log_callback: Optional callback for logging
        progress_callback: Optional callback for progress (current, total, message)
        
    Returns:
        UniversalBackupStats with results
    """
    stats = UniversalBackupStats()
    
    def log(msg: str):
        if log_callback:
            log_callback(msg)
    
    log(f"Starting backup from: {config.source_root}")
    log(f"Extensions: {config.get_all_extensions()}")
    
    # Ensure output directory exists
    config.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Collect all files first for progress tracking
    log("Scanning files...")
    files_to_backup: List[BackupFileInfo] = []
    
    for file_info in iter_backup_files(config, cancel_check):
        files_to_backup.append(file_info)
        stats.total_files += 1
        stats.total_size_bytes += file_info.size_bytes
    
    log(f"Found {stats.total_files} files to backup")
    
    if not files_to_backup:
        log("No files found matching criteria")
        return stats
    
    # Determine output file extension
    ext_map = {
        OutputFormat.TXT: ".txt",
        OutputFormat.MD: ".md",
        OutputFormat.HTML: ".html",
    }
    ext = ext_map.get(config.output_format, ".txt")
    
    if config.split_by_folder:
        # Group files by top-level folder
        folder_groups: Dict[str, List[BackupFileInfo]] = {}
        for file_info in files_to_backup:
            parts = file_info.relative_path.parts
            top_folder = parts[0] if len(parts) > 1 else "_root"
            if top_folder not in folder_groups:
                folder_groups[top_folder] = []
            folder_groups[top_folder].append(file_info)
        
        total_files = len(files_to_backup)
        processed = 0
        
        for folder_name, files in folder_groups.items():
            if cancel_check:
                cancel_check()
            
            output_file = config.output_dir / f"{config.output_filename}_{folder_name}{ext}"
            _write_backup_file(output_file, files, config, stats, cancel_check, log)
            
            processed += len(files)
            if progress_callback:
                progress_callback(processed, total_files, f"Backed up {folder_name}")
    else:
        # Single output file
        output_file = config.output_dir / f"{config.output_filename}{ext}"
        _write_backup_file(output_file, files_to_backup, config, stats, cancel_check, log, progress_callback)
    
    log(f"Backup complete: {stats.files_included} files written to {stats.output_files_created} output file(s)")
    return stats


def _write_backup_file(
    output_path: Path,
    files: List[BackupFileInfo],
    config: UniversalBackupConfig,
    stats: UniversalBackupStats,
    cancel_check: Optional[Callable[[], None]] = None,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> None:
    """Write files to a single backup output file."""
    total = len(files)
    html_blocks = []
    
    try:
        with output_path.open("w", encoding="utf-8") as f:
            if config.output_format == OutputFormat.HTML:
                # We'll collect content and wrap in HTML at the end
                pass
            
            for i, file_info in enumerate(files, 1):
                if cancel_check:
                    cancel_check()
                
                if progress_callback:
                    progress_callback(i, total, str(file_info.relative_path))
                
                # Read content
                content, truncated, line_count = read_file_content(
                    file_info.path,
                    max_kb=config.max_file_kb,
                    add_line_numbers=config.include_line_numbers,
                )
                
                if truncated:
                    stats.files_truncated += 1
                
                # Format header
                header = format_file_header(file_info, config, line_count)
                
                # Format content
                formatted_content = format_file_content(content, file_info, config, truncated)
                
                if config.output_format == OutputFormat.HTML:
                    html_block = f"""
                    <div class="file-block">
                        <div class="file-header">{file_info.relative_path}
                            <span class="file-stats">[{file_info.size_bytes / 1024:.1f}KB | {line_count} lines]</span>
                        </div>
                        <pre><code>{_escape_html(content)}</code></pre>
                    </div>
                    """
                    html_blocks.append(html_block)
                else:
                    f.write(header)
                    f.write(formatted_content)
                    f.write("\n")
                
                stats.files_included += 1
            
            # Write HTML wrapper if HTML format
            if config.output_format == OutputFormat.HTML:
                html_content = generate_html_wrapper(
                    f"Backup: {config.source_root.name}",
                    "\n".join(html_blocks),
                )
                f.seek(0)
                f.truncate()
                f.write(html_content)
        
        stats.output_files_created += 1
        stats.output_paths.append(output_path)
        
    except Exception as exc:
        raise BackupIOError(f"Failed to write backup file: {output_path} - {exc}") from exc


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# Convenience functions for common backup patterns

def quick_backup_typescript(
    source: Path,
    output_dir: Path,
    filename: str = "ts_backup",
) -> UniversalBackupStats:
    """Quick backup of TypeScript/TSX files."""
    config = UniversalBackupConfig(
        source_root=source,
        output_dir=output_dir,
        output_filename=filename,
        extensions=[".ts", ".tsx"],
        output_format=OutputFormat.MD,
        separator_style=SeparatorStyle.MARKDOWN,
        wrap_in_code_block=True,
    )
    return run_universal_backup(config)


def quick_backup_python(
    source: Path,
    output_dir: Path,
    filename: str = "py_backup",
) -> UniversalBackupStats:
    """Quick backup of Python files."""
    config = UniversalBackupConfig(
        source_root=source,
        output_dir=output_dir,
        output_filename=filename,
        extensions=[".py", ".pyi"],
        output_format=OutputFormat.MD,
        separator_style=SeparatorStyle.MARKDOWN,
        wrap_in_code_block=True,
    )
    return run_universal_backup(config)


def quick_backup_all_code(
    source: Path,
    output_dir: Path,
    filename: str = "full_backup",
) -> UniversalBackupStats:
    """Quick backup of all common code files."""
    config = UniversalBackupConfig(
        source_root=source,
        output_dir=output_dir,
        output_filename=filename,
        extension_presets=["all_code", "config"],
        output_format=OutputFormat.TXT,
        separator_style=SeparatorStyle.EQUALS,
        include_file_stats=True,
    )
    return run_universal_backup(config)
