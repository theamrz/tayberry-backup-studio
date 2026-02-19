from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Event
from time import perf_counter
from typing import Callable, Dict, List, Optional, Sequence

from .config import (
    ALLOWED_STEPS,
    BackupProfileConfig,
    BackupStepName,
    OutputFormat,
    OutputConfig,
    ProjectConfig,
    SearchSetConfig,
    extension_for_format,
)
from .errors import BackupCancelled, BackupConfigError, BackupError, BackupIOError
from .jalali import format_jalali_datetime, format_jalali_stamp
from .steps import api_bundles, code_bundles, configs, paths, root_files, trees, zipper, search
from .time_utils import get_current_time


LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, int, str], None]

logger = logging.getLogger(__name__)


@dataclass
class BackupResult:
    backup_root_path: Optional[Path]
    created_files: List[Path] = field(default_factory=list)
    created_directories: List[Path] = field(default_factory=list)
    zip_path: Optional[Path] = None
    stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    time_source: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    is_dry_run: bool = False


class BackupEngine:
    def __init__(
        self,
        project: ProjectConfig,
        profile: BackupProfileConfig,
        app_config: Optional["AppConfig"] = None,
        logger_instance: Optional[logging.Logger] = None,
        log_callback: Optional[LogCallback] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> None:
        self.project = project
        self.profile = profile
        self._app_config = app_config  # optional access to search_sets
        self.logger = logger_instance or logging.getLogger("pycdtweb_backup")
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.cancel_event: Event = Event()

        self._backup_dt: Optional[datetime] = None
        self._backup_dir: Optional[Path] = None
        self._name_builder: Optional[Callable[[str, Optional[str]], Path]] = None

    # ------------------------------------------------------------------ #
    # Logging and progress helpers
    # ------------------------------------------------------------------ #
    def _emit_progress(self, phase_index: int, phase_total: int, label: str) -> None:
        if self.progress_callback:
            self.progress_callback(phase_index, phase_total, label)

    def _log(self, level: int, tag: str, message: str) -> None:
        text = f"[{tag}] {message}"
        self.logger.log(level, text)
        if self.log_callback:
            self.log_callback(text)

    def _warn(self, message: str) -> None:
        self._log(logging.WARNING, "WARN", message)

    def cancel(self) -> None:
        self.cancel_event.set()

    def _check_cancelled(self) -> None:
        if self.cancel_event.is_set():
            raise BackupCancelled("Backup cancelled by user")

    # ------------------------------------------------------------------ #
    # Naming helpers
    # ------------------------------------------------------------------ #
    def _slugify(self, value: str) -> str:
        cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
        slug = "_".join(filter(None, cleaned.split("_")))
        return slug or "project"

    def _project_slug_for_names(self) -> str:
        candidates: List[str] = []
        if self.project.id and self.project.id.lower() != "dynamic":
            candidates.append(self.project.id)
        if self.project.label:
            candidates.append(self.project.label)
        if self.project.project_root.name:
            candidates.append(self.project.project_root.name)
        for candidate in candidates:
            slug = self._slugify(candidate)
            if slug and slug != "dynamic":
                return slug
        return "project"

    def _file_stamp(self) -> str:
        # Keep backup directory in Jalali, but use a compact Gregorian stamp for artifact filenames.
        return self._require_backup_dt().strftime("%Y%m%d_%H%M")

    def _build_name_builder(self) -> Callable[[str, Optional[str]], Path]:
        cfg: OutputConfig = self.profile.output_config
        project_slug = self._project_slug_for_names()
        stamp = self._file_stamp()
        template = cfg.name_template or "{project}_{base}_{stamp}"

        def builder(base: str, ext_override: Optional[str] = None) -> Path:
            ext = ext_override or extension_for_format(cfg.format)
            base_slug = self._slugify(base)
            if cfg.dynamic_names:
                try:
                    name = template.format(base=base_slug, project=project_slug, stamp=stamp)
                except Exception:
                    name = f"{project_slug}_{base_slug}_{stamp}"
            else:
                name = base_slug
            return self._require_backup_dir() / f"{name}{ext}"

        return builder

    def _name_builder_or_raise(self) -> Callable[[str, Optional[str]], Path]:
        if self._name_builder is None:
            raise BackupError("Filename builder not initialized")
        return self._name_builder

    # ------------------------------------------------------------------ #
    # Core execution
    # ------------------------------------------------------------------ #
    def run_backup(
        self,
        dry_run: bool = False,
        note: str | None = None,
        use_network_time_override: Optional[bool] = None,
        skip_zip_override: Optional[bool] = None,
        include_project_root_files: Optional[bool] = None,
        include_steps_override: Optional[Sequence[str]] = None,
        search_set_ids: Optional[Sequence[str]] = None,
        compression_level: int = 6,
    ) -> BackupResult:
        result = BackupResult(backup_root_path=None, is_dry_run=dry_run)
        result.started_at = datetime.now()
        start_perf = perf_counter()

        use_network_time = (
            use_network_time_override
            if use_network_time_override is not None
            else self.profile.use_network_time
        )
        skip_zip = (
            skip_zip_override
            if skip_zip_override is not None
            else self.profile.skip_zip
        )

        raw_steps = list(include_steps_override) if include_steps_override is not None else list(self.profile.include_steps)
        invalid_steps = [s for s in raw_steps if s not in ALLOWED_STEPS]
        if invalid_steps:
            self._warn(f"Ignoring unknown include_steps: {', '.join(invalid_steps)}")
        include_steps: List[BackupStepName] = [s for s in raw_steps if s in ALLOWED_STEPS]

        if include_project_root_files is False or self.profile.no_root_files:
            include_steps = [s for s in include_steps if s != "project_root_files"]

        phases: List[str] = ["Pre-checks"]
        step_to_label = {
            "trees": "Directory trees",
            "code_txt": "Code text bundles",
            "ts_tsx_md_bundles": "TS/TSX markdown bundles",
            "full_ts_tsx_bundle": "Full TS/TSX bundle",
            "configs": "Config bundles",
            "tsconfig_bundle": "TSConfig bundle",
            "api_group_bundles": "API grouped bundles",
            "paths": "Path listings",
            "project_root_files": "Project root helpers",
            "keyword_search": "Keyword search bundles",
        }
        for step in include_steps:
            if step in step_to_label:
                phases.append(step_to_label[step])
        if not skip_zip:
            phases.append("ZIP archive")
        phases.append("Summary")
        phase_total = len(phases)

        output_config = self.profile.output_config

        try:
            # Phase 1: pre-checks and setup
            self._emit_progress(1, phase_total, "Pre-checks")
            self._phase_prechecks(result, dry_run, use_network_time, skip_zip, output_config, note or "")

            phase_index = 2
            # Trees
            if "trees" in include_steps:
                self._emit_progress(phase_index, phase_total, step_to_label["trees"])
                self._check_cancelled()
                if dry_run:
                    self._log(logging.INFO, "TREES", "DRY RUN: would generate directory trees.")
                    result.stats["trees"] = {"planned": 1}
                else:
                    stats = trees.generate_trees(
                        self.project.project_root,
                        self._require_backup_dir(),
                        output_config,
                        self._name_builder_or_raise(),
                        cancel_check=self._check_cancelled,
                    )
                    result.stats["trees"] = {"files_written": stats.files_written}
                phase_index += 1

            # Code text bundles
            if "code_txt" in include_steps:
                self._emit_progress(phase_index, phase_total, step_to_label["code_txt"])
                self._check_cancelled()
                if dry_run:
                    self._log(logging.INFO, "CODE", "DRY RUN: would generate code text bundles.")
                    result.stats["code_txt"] = {"planned": 1}
                else:
                    stats = code_bundles.generate_full_text_bundles(
                        project_root=self.project.project_root,
                        backup_dir=self._require_backup_dir(),
                        profile=self.profile,
                        stamp=format_jalali_stamp(self._require_backup_dt()),
                        output_config=output_config,
                        name_builder=self._name_builder_or_raise(),
                        warn=self._warn,
                        cancel_check=self._check_cancelled,
                    )
                    result.stats["code_txt"] = {
                        "files_written": stats.files_written,
                        "files_included": stats.files_included,
                    }
                phase_index += 1

            # TS/TSX markdown bundles
            if "ts_tsx_md_bundles" in include_steps:
                self._emit_progress(phase_index, phase_total, step_to_label["ts_tsx_md_bundles"])
                self._check_cancelled()
                if dry_run:
                    self._log(logging.INFO, "CODE", "DRY RUN: would generate TS/TSX markdown bundles.")
                    result.stats["ts_tsx_md_bundles"] = {"planned": 1}
                else:
                    stats = code_bundles.generate_ts_bundles(
                        project_root=self.project.project_root,
                        backup_dir=self._require_backup_dir(),
                        profile=self.profile,
                        stamp=format_jalali_stamp(self._require_backup_dt()),
                        name_builder=self._name_builder_or_raise(),
                        warn=self._warn,
                        cancel_check=self._check_cancelled,
                    )
                    result.stats["ts_tsx_md_bundles"] = {
                        "files_written": stats.files_written,
                        "files_included": stats.files_included,
                    }
                phase_index += 1

            # Full TS/TSX bundle
            if "full_ts_tsx_bundle" in include_steps:
                self._emit_progress(phase_index, phase_total, step_to_label["full_ts_tsx_bundle"])
                self._check_cancelled()
                if dry_run:
                    self._log(logging.INFO, "CODE", "DRY RUN: would generate full TS/TSX bundle.")
                    result.stats["full_ts_tsx_bundle"] = {"planned": 1}
                else:
                    stats = code_bundles.generate_full_ts_bundle(
                        project_root=self.project.project_root,
                        backup_dir=self._require_backup_dir(),
                        profile=self.profile,
                        stamp=format_jalali_stamp(self._require_backup_dt()),
                        name_builder=self._name_builder_or_raise(),
                        warn=self._warn,
                        cancel_check=self._check_cancelled,
                    )
                    result.stats["full_ts_tsx_bundle"] = {
                        "files_written": stats.files_written,
                        "files_included": stats.files_included,
                    }
                phase_index += 1

            # Config bundles
            if "configs" in include_steps or "tsconfig_bundle" in include_steps:
                label = step_to_label["configs"] if "configs" in include_steps else step_to_label["tsconfig_bundle"]
                self._emit_progress(phase_index, phase_total, label)
                self._check_cancelled()
                if dry_run:
                    self._log(logging.INFO, "CONFIGS", "DRY RUN: would generate config bundles.")
                    result.stats["configs"] = {"planned": 1}
                else:
                    stats = configs.generate_config_bundles(
                        project_root=self.project.project_root,
                        backup_dir=self._require_backup_dir(),
                        profile=self.profile,
                        output_config=output_config,
                        name_builder=self._name_builder_or_raise(),
                        warn=self._warn,
                        cancel_check=self._check_cancelled,
                    )
                    result.stats["configs"] = {
                        "files_written": stats.files_written,
                        "files_included": stats.files_included,
                        "configs_written": stats.configs_written,
                    }
                    result.stats["tsconfig_bundle"] = {
                        "files_written": stats.tsconfig_written,
                        "files_included": stats.files_included,
                    }
                phase_index += 1

            # API bundles
            if "api_group_bundles" in include_steps:
                self._emit_progress(phase_index, phase_total, step_to_label["api_group_bundles"])
                self._check_cancelled()
                if dry_run:
                    self._log(logging.INFO, "API_BUNDLES", "DRY RUN: would generate API group bundles.")
                    result.stats["api_group_bundles"] = {"planned": 1}
                else:
                    stats = api_bundles.generate_api_bundles(
                        project_root=self.project.project_root,
                        backup_dir=self._require_backup_dir(),
                        profile=self.profile,
                        output_config=output_config,
                        name_builder=self._name_builder_or_raise(),
                        warn=self._warn,
                        cancel_check=self._check_cancelled,
                    )
                    result.stats["api_group_bundles"] = {
                        "files_written": stats.files_written,
                        "files_included": stats.files_included,
                    }
                phase_index += 1

            # Paths
            if "paths" in include_steps:
                self._emit_progress(phase_index, phase_total, step_to_label["paths"])
                self._check_cancelled()
                if dry_run:
                    self._log(logging.INFO, "PATHS", "DRY RUN: would generate path listings.")
                    result.stats["paths"] = {"planned": 1}
                else:
                    stats = paths.generate_paths_files(
                        project_root=self.project.project_root,
                        backup_dir=self._require_backup_dir(),
                        output_config=output_config,
                        name_builder=self._name_builder_or_raise(),
                        cancel_check=self._check_cancelled,
                    )
                    result.stats["paths"] = {
                        "files_written": stats.files_written,
                        "paths_total": stats.paths_total,
                        "ts_paths_total": stats.ts_paths_total,
                    }
                phase_index += 1

            # Keyword search bundles
            if "keyword_search" in include_steps and self._has_search_sets():
                self._emit_progress(phase_index, phase_total, step_to_label["keyword_search"])
                self._check_cancelled()
                active_sets = list(self._resolve_search_sets(search_set_ids))
                if dry_run:
                    self._log(
                        logging.INFO,
                        "SEARCH",
                        f"DRY RUN: would run keyword search for sets: {[s.id for s in active_sets]}",
                    )
                    result.stats["keyword_search"] = {"planned": len(active_sets)}
                else:
                    search_stats = search.run_search_sets(
                        project_root=self.project.project_root,
                        search_sets=active_sets,
                        max_kb=self.profile.max_file_kb,
                        output_dir=self._require_backup_dir() / "search",
                        warn=self._warn,
                        cancel_check=self._check_cancelled,
                    )
                    result.stats["keyword_search"] = {
                        sid: s.matches for sid, s in search_stats.items()
                    }
                phase_index += 1

            # Project root helper files
            if "project_root_files" in include_steps:
                self._emit_progress(phase_index, phase_total, step_to_label["project_root_files"])
                self._check_cancelled()
                if dry_run:
                    self._log(logging.INFO, "ROOT", "DRY RUN: would write Tree.md and AllCode_Backup.md.")
                    result.stats["project_root_files"] = {"planned": 1}
                else:
                    stats = root_files.write_project_root_files(
                        project_root=self.project.project_root,
                        backup_dir=self._require_backup_dir(),
                        backup_dt=self._require_backup_dt(),
                        note=note or "",
                        warn=self._warn,
                        cancel_check=self._check_cancelled,
                    )
                    result.stats["project_root_files"] = {
                        "files_written": stats.files_written,
                    }
                    result.created_files.extend(stats.files)
                phase_index += 1

            # ZIP
            if not skip_zip:
                self._emit_progress(phase_index, phase_total, "ZIP archive")
                self._check_cancelled()
                if dry_run:
                    self._log(logging.INFO, "ZIP", "DRY RUN: ZIP creation skipped.")
                    result.stats["zip"] = {"planned": 1}
                else:
                    zstats = zipper.create_zip(
                        self._require_backup_dir(), 
                        self.project.zip_output_dir,
                        compression_level=compression_level
                    )
                    result.zip_path = zstats.zip_path
                    result.stats["zip"] = {"created": 1 if zstats.zip_path else 0}
                phase_index += 1

            # Summary
            self._emit_progress(phase_index, phase_total, "Summary")
            self._log(
                logging.INFO,
                "SUMMARY",
                f"Backup completed. Dry run={dry_run}, zip={'created' if result.zip_path else 'skipped'}",
            )

        except BackupCancelled as exc:
            self._log(logging.WARNING, "CANCEL", str(exc))
            raise
        except BackupConfigError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise BackupIOError(str(exc)) from exc
        finally:
            result.finished_at = datetime.now()
            result.duration_seconds = round(perf_counter() - start_perf, 3)

        return result

    # ------------------------------------------------------------------ #
    # Helper phases
    # ------------------------------------------------------------------ #
    def _phase_prechecks(
        self,
        result: BackupResult,
        dry_run: bool,
        use_network_time: bool,
        skip_zip: bool,
        output_config: OutputConfig,
        note: str,
    ) -> None:
        self._log(logging.INFO, "PRECHECK", "Validating project paths...")
        self._check_cancelled()

        if not self.project.project_root.exists() or not self.project.project_root.is_dir():
            raise BackupConfigError(f"Project root does not exist or is not a directory: {self.project.project_root}")

        backup_root = self.project.backup_root
        if not backup_root.exists():
            if dry_run:
                self._log(logging.INFO, "PRECHECK", f"DRY RUN: would create backup root: {backup_root}")
            else:
                backup_root.mkdir(parents=True, exist_ok=True)
        elif not backup_root.is_dir():
            raise BackupConfigError(f"Backup root is not a directory: {backup_root}")

        if not skip_zip:
            zip_dir = self.project.zip_output_dir.expanduser()
            if not zip_dir.exists():
                if dry_run:
                    self._log(logging.INFO, "PRECHECK", f"DRY RUN: would create ZIP output dir: {zip_dir}")
                else:
                    zip_dir.mkdir(parents=True, exist_ok=True)
            elif not zip_dir.is_dir():
                raise BackupConfigError(f"ZIP output directory is invalid: {zip_dir}")

        self._log(logging.INFO, "PRECHECK", "Resolving time source...")
        time_result = get_current_time(self.project.timezone, use_network_time=use_network_time)
        self._backup_dt = time_result.dt
        result.time_source = time_result.source
        self._log(logging.INFO, "PRECHECK", f"Time source: {time_result.source} ({time_result.dt.isoformat()})")

        self._backup_dir = self.project.backup_root / f"Backup-{format_jalali_stamp(time_result.dt)}"
        result.backup_root_path = self._backup_dir
        if dry_run:
            self._log(logging.INFO, "PRECHECK", f"DRY RUN: backup directory planned at {self._backup_dir}")
        else:
            self._backup_dir.mkdir(parents=True, exist_ok=True)
            result.created_directories.append(self._backup_dir)
            self._log(logging.INFO, "PRECHECK", f"Backup directory: {self._backup_dir}")

        # Prepare filename builder early for note writing and subsequent steps
        self._name_builder = self._build_name_builder()

        if note:
            note_path = self._write_backup_note(
                backup_dir=self._backup_dir,
                dt=self._backup_dt,
                note=note,
                time_source=time_result.source,
                dry_run=dry_run,
                output_config=output_config,
            )
            if note_path is not None:
                result.created_files.append(note_path)

    def _write_backup_note(
        self,
        backup_dir: Path,
        dt: datetime,
        note: str,
        time_source: str,
        dry_run: bool,
        output_config: OutputConfig,
    ) -> Optional[Path]:
        if dry_run:
            return None
        backup_note = self._name_builder_or_raise()("backup_note", ext_override=extension_for_format(output_config.format))
        backup_note.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"Time source: {time_source}",
            f"ISO datetime: {dt.isoformat()}",
            f"Jalali datetime: {format_jalali_datetime(dt)}",
            "",
            note or "",
        ]

        if output_config.format == OutputFormat.MD:
            content = "\n".join(
                [
                    "# Backup Note",
                    "",
                    f"- **Time source:** {time_source}",
                    f"- **ISO datetime:** {dt.isoformat()}",
                    f"- **Jalali datetime:** {format_jalali_datetime(dt)}",
                    "",
                    note or "_No note provided._",
                ]
            )
        elif output_config.format == OutputFormat.HTML:
            content = (
                "<h2>Backup Note</h2>\n"
                f"<p><strong>Time source:</strong> {time_source}<br/>"
                f"<strong>ISO datetime:</strong> {dt.isoformat()}<br/>"
                f"<strong>Jalali datetime:</strong> {format_jalali_datetime(dt)}</p>\n"
                f"<p>{note or 'No note provided.'}</p>\n"
            )
        else:
            content = "\n".join(lines) + "\n"

        backup_note.write_text(content, encoding="utf-8")
        return backup_note

    def _require_backup_dir(self) -> Path:
        if self._backup_dir is None:
            raise BackupError("Backup directory was not prepared")
        return self._backup_dir

    def _require_backup_dt(self) -> datetime:
        if self._backup_dt is None:
            raise BackupError("Backup datetime not initialized")
        return self._backup_dt

    def _resolve_search_sets(self, search_set_ids: Optional[Sequence[str]]) -> List[SearchSetConfig]:
        if not self._app_config or not self._app_config.search_sets:
            return []
        if not search_set_ids:
            return list(self._app_config.search_sets.values())
        resolved: List[SearchSetConfig] = []
        for sid in search_set_ids:
            if sid in self._app_config.search_sets:
                resolved.append(self._app_config.search_sets[sid])
            else:
                self._warn(f"Search set '{sid}' not found; skipping.")
        return resolved

    def _has_search_sets(self) -> bool:
        return bool(self._app_config and self._app_config.search_sets)
