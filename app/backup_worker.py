"""
Backup Worker — QThread wrapper for BackupEngine

Runs the backup operation in a background thread so the UI
stays completely responsive during long operations.

Author: Amirhosein Rezapour | techili.ir | tayberry.ir | tayberry.dev
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from .backup_core.config import AppConfig, ProjectConfig, BackupProfileConfig
from .backup_core.engine import BackupEngine
from .backup_core.errors import BackupCancelled


class BackupWorker(QThread):
    log        = pyqtSignal(str)          # a log line
    progress   = pyqtSignal(int, int, str) # (current, total, label)
    finished_ok    = pyqtSignal(object)   # BackupResult
    finished_error = pyqtSignal(str)      # error message

    def __init__(
        self,
        app_config: AppConfig,
        project: ProjectConfig,
        profile: BackupProfileConfig,
        dry_run: bool = False,
        note: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._app_config = app_config
        self._project    = project
        self._profile    = profile
        self._dry_run    = dry_run
        self._note       = note
        self._engine: BackupEngine | None = None

    # ------------------------------------------------------------------ #
    def cancel(self) -> None:
        if self._engine:
            self._engine.cancel()

    # ------------------------------------------------------------------ #
    def run(self) -> None:
        try:
            self._engine = BackupEngine(
                project=self._project,
                profile=self._profile,
                app_config=self._app_config,
                log_callback=self._on_log,
                progress_callback=self._on_progress,
            )
            result = self._engine.run_backup(
                dry_run=self._dry_run,
                note=self._note,
            )
            self.finished_ok.emit(result)
        except BackupCancelled:
            self.finished_error.emit("⏹ Operation cancelled.")
        except Exception as exc:  # noqa: BLE001
            self.finished_error.emit(str(exc))

    # ------------------------------------------------------------------ #
    def _on_log(self, msg: str) -> None:
        self.log.emit(msg)

    def _on_progress(self, idx: int, total: int, label: str) -> None:
        self.progress.emit(idx, total, label)
