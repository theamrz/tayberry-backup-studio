from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Literal, Optional, Set
from zoneinfo import ZoneInfo

from .errors import BackupConfigError


# ------------------------------------------------------------------ #
# Enums for output formats and separator styles
# ------------------------------------------------------------------ #
class OutputFormat(str, Enum):
    TXT = "txt"
    MD = "md"
    HTML = "html"


def extension_for_format(fmt: OutputFormat) -> str:
    return {
        OutputFormat.TXT: ".txt",
        OutputFormat.MD: ".md",
        OutputFormat.HTML: ".html",
    }.get(fmt, ".txt")


class SeparatorStyle(str, Enum):
    EQUALS = "equals"        # ===== path/to/file.ts =====
    HASH = "hash"            # ##### path/to/file.ts #####
    MARKDOWN = "markdown"    # ## path/to/file.ts
    DASHED = "dashed"        # ----- path/to/file.ts -----
    COMMENT = "comment"      # // === path/to/file.ts ===
    XML_STYLE = "xml"        # <!-- path/to/file.ts -->
    CUSTOM = "custom"        # User defined


class ProjectType(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    FULLSTACK = "fullstack"
    PYTHON = "python"
    UNKNOWN = "unknown"


# ------------------------------------------------------------------ #
# Preset file extension groups
# ------------------------------------------------------------------ #
FILE_EXTENSION_PRESETS: Dict[str, List[str]] = {
    "typescript": [".ts", ".tsx"],
    "javascript": [".js", ".jsx"],
    "web_all": [".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte"],
    "styles": [".css", ".scss", ".sass", ".less", ".styl"],
    "config": [".json", ".yaml", ".yml", ".toml", ".ini", ".env"],
    "python": [".py", ".pyi", ".pyx"],
    "documentation": [".md", ".mdx", ".rst", ".txt"],
    "html": [".html", ".htm", ".ejs", ".hbs"],
    "all_code": [".ts", ".tsx", ".js", ".jsx", ".py", ".vue", ".svelte", ".go", ".rs", ".java", ".kt"],
}


# ------------------------------------------------------------------ #
# Common folders to exclude
# ------------------------------------------------------------------ #
COMMON_EXCLUDE_FOLDERS: Set[str] = {
    "node_modules", ".next", ".turbo", "dist", "build", ".git",
    ".cache", "coverage", ".output", ".nx", ".vercel", ".expo",
    ".vscode", "tmp", "__pycache__", "venv", ".idea", "vendor",
    "Pods", ".mypy_cache", ".pytest_cache", "htmlcov", ".tox",
    "egg-info", ".eggs", "target", "out", ".gradle", ".mvn",
}

COMMON_EXCLUDE_FILES: Set[str] = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "LICENSE",
    "CHANGELOG", ".DS_Store", ".gitignore", ".npmrc", "Thumbs.db",
}


# ------------------------------------------------------------------ #
# Separator format helpers
# ------------------------------------------------------------------ #
def get_separator_format(style: SeparatorStyle, custom_format: Optional[str] = None) -> str:
    """
    Returns a format string with {path} placeholder.
    """
    formats = {
        SeparatorStyle.EQUALS: "\n===== {path} =====\n",
        SeparatorStyle.HASH: "\n##### {path} #####\n",
        SeparatorStyle.MARKDOWN: "\n## {path}\n",
        SeparatorStyle.DASHED: "\n----- {path} -----\n",
        SeparatorStyle.COMMENT: "\n// === {path} ===\n",
        SeparatorStyle.XML_STYLE: "\n<!-- {path} -->\n",
    }
    if style == SeparatorStyle.CUSTOM and custom_format:
        return custom_format
    return formats.get(style, formats[SeparatorStyle.EQUALS])


BackupStepName = Literal[
    "trees",
    "code_txt",
    "ts_tsx_md_bundles",
    "full_ts_tsx_bundle",
    "configs",
    "tsconfig_bundle",
    "api_group_bundles",
    "paths",
    "project_root_files",
    "keyword_search",
]

DEFAULT_INCLUDE_STEPS: List[BackupStepName] = [
    "trees",
    "code_txt",
    "ts_tsx_md_bundles",
    "full_ts_tsx_bundle",
    "configs",
    "tsconfig_bundle",
    "api_group_bundles",
    "paths",
    "keyword_search",
]

ALLOWED_STEPS: Set[BackupStepName] = set(DEFAULT_INCLUDE_STEPS)
ALLOWED_STEPS.add("project_root_files")


@dataclass
class ProjectConfig:
    id: str
    label: str
    project_root: Path
    backup_root: Path
    zip_output_dir: Path
    timezone: str = "Asia/Tehran"
    detected_type: ProjectType = ProjectType.UNKNOWN


@dataclass
class ExcludeConfig:
    """Configuration for excluding files and folders from backup."""
    exclude_folders: Set[str] = field(default_factory=lambda: set(COMMON_EXCLUDE_FOLDERS))
    exclude_files: Set[str] = field(default_factory=lambda: set(COMMON_EXCLUDE_FILES))
    exclude_patterns: List[str] = field(default_factory=lambda: [".spec.", ".test.", ".e2e-spec."])
    exclude_hidden: bool = True  # Exclude files/folders starting with .


@dataclass
class OutputConfig:
    """Configuration for backup output format."""
    format: OutputFormat = OutputFormat.TXT
    separator_style: SeparatorStyle = SeparatorStyle.EQUALS
    custom_separator: Optional[str] = None
    include_line_numbers: bool = False
    include_file_stats: bool = True  # Size, line count in header
    wrap_in_code_block: bool = False  # For markdown output
    dynamic_names: bool = True  # Include project + timestamp in filenames
    name_template: str = "{project}_{base}_{stamp}"  # Template for dynamic names


@dataclass
class BackupProfileConfig:
    id: str
    label: str
    use_network_time: bool = False
    skip_zip: bool = False
    max_file_kb: int = 256
    no_root_files: bool = False
    include_steps: List[BackupStepName] = field(
        default_factory=lambda: list(DEFAULT_INCLUDE_STEPS)
    )
    allowed_ts_extensions: List[str] = field(default_factory=lambda: [".ts", ".tsx"])
    allowed_full_extensions: List[str] = field(
        default_factory=lambda: [
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".json",
            ".md",
            ".yml",
            ".yaml",
            ".env",
            ".sh",
        ]
    )
    # New advanced options
    exclude_config: ExcludeConfig = field(default_factory=ExcludeConfig)
    output_config: OutputConfig = field(default_factory=OutputConfig)
    custom_extensions: Optional[List[str]] = None  # Override all extensions with custom list
    extension_presets: List[str] = field(default_factory=list)  # Use predefined extension groups


@dataclass
class AppConfig:
    projects: Dict[str, ProjectConfig]
    profiles: Dict[str, BackupProfileConfig]
    search_sets: Dict[str, "SearchSetConfig"]

    def get_project(self, project_id: str) -> ProjectConfig:
        return self.projects[project_id]

    def get_profile(self, profile_id: str) -> BackupProfileConfig:
        return self.profiles[profile_id]

    def get_search_set(self, search_id: str) -> "SearchSetConfig":
        return self.search_sets[search_id]


@dataclass
class SearchSetConfig:
    id: str
    label: str
    keywords: List[str]
    extensions: List[str] = field(default_factory=lambda: [".ts", ".tsx", ".js", ".jsx", ".json"])


def _load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as exc:  # noqa: PERF203
        raise BackupConfigError(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BackupConfigError(f"Config file is not valid JSON: {path}") from exc


def _parse_output_config(raw: object) -> OutputConfig:
    if not isinstance(raw, dict):
        return OutputConfig()

    def _enum_value(value: object, enum_cls, default):
        try:
            return enum_cls(value)
        except Exception:  # noqa: BLE001
            return default

    fmt = _enum_value(raw.get("format", OutputFormat.TXT), OutputFormat, OutputFormat.TXT)
    sep = _enum_value(raw.get("separator_style", SeparatorStyle.EQUALS), SeparatorStyle, SeparatorStyle.EQUALS)

    return OutputConfig(
        format=fmt,
        separator_style=sep,
        custom_separator=raw.get("custom_separator"),
        include_line_numbers=bool(raw.get("include_line_numbers", False)),
        include_file_stats=bool(raw.get("include_file_stats", True)),
        wrap_in_code_block=bool(raw.get("wrap_in_code_block", False)),
        dynamic_names=bool(raw.get("dynamic_names", True)),
        name_template=str(raw.get("name_template", "{project}_{base}_{stamp}")),
    )


def _validate_step_list(values: List[str], config_path: Path) -> List[BackupStepName]:
    invalid = [v for v in values if v not in ALLOWED_STEPS]
    if invalid:
        raise BackupConfigError(
            f"Unknown include_steps in {config_path}: {', '.join(invalid)}"
        )
    return list(values)  # type: ignore[return-value]


def _expand_path(raw: object) -> Path:
    return Path(os.path.expandvars(str(raw))).expanduser()


def load_app_config(config_path: Path) -> AppConfig:
    raw = _load_json(config_path)

    if "projects" not in raw or "profiles" not in raw:
        raise BackupConfigError("Config must include 'projects' and 'profiles' keys.")

    base_dir = config_path.parent

    projects: Dict[str, ProjectConfig] = {}
    for proj in raw.get("projects", []):
        try:
            proj_id = proj["id"]
            project_root_raw = proj["project_root"]
            backup_root_raw = proj["backup_root"]
        except KeyError as exc:
            raise BackupConfigError(f"Project is missing required field: {exc}") from exc

        if proj_id in projects:
            raise BackupConfigError(f"Duplicate project id in config: {proj_id}")

        project_root = _expand_path(project_root_raw)
        if not project_root.is_absolute():
            project_root = base_dir / project_root
        backup_root = _expand_path(backup_root_raw)
        if not backup_root.is_absolute():
            backup_root = base_dir / backup_root
        zip_output_dir = _expand_path(proj.get("zip_output_dir", str(backup_root)))
        if not zip_output_dir.is_absolute():
            zip_output_dir = base_dir / zip_output_dir

        timezone = proj.get("timezone", "Asia/Tehran")
        try:
            ZoneInfo(timezone)
        except Exception as exc:  # noqa: BLE001
            raise BackupConfigError(f"Invalid timezone for project '{proj_id}': {timezone}") from exc

        pc = ProjectConfig(
            id=proj_id,
            label=proj.get("label", proj_id),
            project_root=project_root,
            backup_root=backup_root,
            zip_output_dir=zip_output_dir,
            timezone=timezone,
        )
        projects[pc.id] = pc

    profiles: Dict[str, BackupProfileConfig] = {}
    for prof in raw.get("profiles", []):
        try:
            prof_id = prof["id"]
        except KeyError as exc:
            raise BackupConfigError("Profile is missing required field 'id'") from exc
        if prof_id in profiles:
            raise BackupConfigError(f"Duplicate profile id in config: {prof_id}")

        include_steps_raw = prof.get("include_steps")
        include_steps: List[BackupStepName]
        if include_steps_raw is None:
            include_steps = list(DEFAULT_INCLUDE_STEPS)
        else:
            include_steps = _validate_step_list(list(include_steps_raw), config_path)

        try:
            max_file_kb = int(prof.get("max_file_kb", 256))
        except Exception as exc:  # noqa: BLE001
            raise BackupConfigError(f"Invalid max_file_kb for profile '{prof_id}'") from exc
        if max_file_kb <= 0:
            raise BackupConfigError(f"max_file_kb must be > 0 for profile '{prof_id}'")

        output_config = _parse_output_config(prof.get("output_config", {}))

        bpc = BackupProfileConfig(
            id=prof_id,
            label=prof.get("label", prof_id),
            use_network_time=prof.get("use_network_time", False),
            skip_zip=prof.get("skip_zip", False),
            max_file_kb=max_file_kb,
            no_root_files=prof.get("no_root_files", False),
            include_steps=include_steps,
            allowed_ts_extensions=prof.get("allowed_ts_extensions", [".ts", ".tsx"]),
            allowed_full_extensions=prof.get(
                "allowed_full_extensions",
                [
                    ".ts",
                    ".tsx",
                    ".js",
                    ".jsx",
                    ".json",
                    ".md",
                    ".yml",
                    ".yaml",
                    ".env",
                    ".sh",
                ],
            ),
            output_config=output_config,
        )
        profiles[bpc.id] = bpc

    search_sets: Dict[str, SearchSetConfig] = {}
    for search in raw.get("search_sets", []):
        try:
            sid = search["id"]
            keywords = list(search["keywords"])
        except KeyError as exc:
            raise BackupConfigError("Search set must include 'id' and 'keywords'") from exc
        if sid in search_sets:
            raise BackupConfigError(f"Duplicate search_set id: {sid}")
        extensions = search.get("extensions", [".ts", ".tsx", ".js", ".jsx", ".json"])
        search_sets[sid] = SearchSetConfig(
            id=sid,
            label=search.get("label", sid),
            keywords=keywords,
            extensions=extensions,
        )

    if not projects:
        raise BackupConfigError("No projects defined in configuration.")
    if not profiles:
        raise BackupConfigError("No profiles defined in configuration.")

    return AppConfig(projects=projects, profiles=profiles, search_sets=search_sets)
