"""
Tayberry Backup Studio — Main Window (Liquid Glass Edition)

Merges the full Backup Engine with the Liquid Glass UI system.
Left panel: project list. Right panel: backup operations + live log.

Author: Amirhosein Rezapour | techili.ir | tayberry.ir | tayberry.dev
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QObject
from PyQt6.QtGui import QIcon, QPixmap, QColor, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QTextEdit,
    QComboBox, QProgressBar, QSplitter, QSizePolicy,
    QAbstractItemView, QFrame,
)

from .widgets.galaxy_background import GalaxyBackgound
from .widgets.glass_surface import GlassSurface
from .widgets.star_border_button import StarBorderButton
from .widgets.fluid_glass import FluidGlassButton
from .widgets.controls_pill import ControlPill
from .backup_core.config import load_app_config, AppConfig, ProjectConfig
from .backup_worker import BackupWorker


# --------------------------------------------------------------------------- #
# Helper: find the resources/ directory regardless of run mode
# --------------------------------------------------------------------------- #
def _resources_dir() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller bundle
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent
    return base / "resources"


# --------------------------------------------------------------------------- #
# Glass-styled List Widget
# --------------------------------------------------------------------------- #
_LIST_STYLE = """
QListWidget {
    background: transparent;
    border: none;
    outline: none;
    color: white;
    font-size: 13px;
}
QListWidget::item {
    padding: 10px 14px;
    border-radius: 10px;
    border: none;
}
QListWidget::item:selected {
    background: rgba(0, 200, 255, 0.25);
    color: #00FFFF;
}
QListWidget::item:hover:!selected {
    background: rgba(255, 255, 255, 0.08);
}
QScrollBar:vertical {
    background: rgba(255,255,255,0.04);
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.25);
    border-radius: 3px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""

_LOG_STYLE = """
QTextEdit {
    background: rgba(0,0,0,0.45);
    color: #88FF88;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 10px;
    font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
    font-size: 12px;
    padding: 8px;
}
"""

_COMBO_STYLE = """
QComboBox {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.20);
    border-radius: 10px;
    color: white;
    padding: 6px 14px;
    font-size: 13px;
    min-width: 180px;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid rgba(255,255,255,0.6);
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: rgba(20,20,40,0.95);
    border: 1px solid rgba(0,200,255,0.3);
    border-radius: 10px;
    color: white;
    selection-background-color: rgba(0,200,255,0.25);
    padding: 4px;
}
"""

_PROGRESS_STYLE = """
QProgressBar {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px;
    color: transparent;
    height: 12px;
}
QProgressBar::chunk {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #00BFFF, stop:0.5 #00FFFF, stop:1 #00E5FF
    );
    border-radius: 8px;
}
"""

_LABEL_STYLE      = "color: white; font-size: %spx; font-weight: %s;"
_DIVIDER_STYLE    = "color: rgba(255,255,255,0.12); background: rgba(255,255,255,0.10);"
_SUBTLE_LABEL     = "color: rgba(255,255,255,0.40); font-size: 11px;"


# --------------------------------------------------------------------------- #
# Main Window
# --------------------------------------------------------------------------- #
class TayberryWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tayberry Backup Studio")
        self.resize(1280, 820)
        self.setMinimumSize(1100, 700)

        # ── State ──────────────────────────────────────────────────────── #
        self._app_config: AppConfig | None = None
        self._projects: list[ProjectConfig] = []
        self._selected_project: ProjectConfig | None = None
        self._worker: BackupWorker | None = None

        # ── Background ─────────────────────────────────────────────────── #
        self.bg = GalaxyBackgound(self)
        self.setCentralWidget(self.bg)

        # ── Root overlay (transparent, fills bg) ───────────────────────── #
        self.overlay = QWidget(self.bg)
        self.overlay.setStyleSheet("background: transparent;")
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        root_vbox = QVBoxLayout(self.overlay)
        root_vbox.setContentsMargins(24, 24, 24, 24)
        root_vbox.setSpacing(16)

        # ── Top Bar ────────────────────────────────────────────────────── #
        self.top_bar = GlassSurface(self.overlay, blur_radius=20, frost_opacity=0.12)
        self.top_bar.setFixedHeight(72)
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(20, 0, 20, 0)
        top_layout.setSpacing(14)

        res = _resources_dir()
        logo_pix = QPixmap(str(res / "logo.png"))
        logo_lbl = QLabel()
        if not logo_pix.isNull():
            logo_lbl.setPixmap(logo_pix.scaled(52, 52, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation))
        top_layout.addWidget(logo_lbl)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)
        brand_title = QLabel("Tayberry Backup Studio")
        brand_title.setStyleSheet(_LABEL_STYLE % ("20", "bold"))
        brand_sub   = QLabel("by Amirhosein Rezapour  ·  techili.ir  ·  tayberry.dev")
        brand_sub.setStyleSheet(_SUBTLE_LABEL)
        brand_col.addWidget(brand_title)
        brand_col.addWidget(brand_sub)
        top_layout.addLayout(brand_col)
        top_layout.addStretch()

        # Profile selector in top bar
        profile_lbl = QLabel("Profile:")
        profile_lbl.setStyleSheet(_SUBTLE_LABEL)
        top_layout.addWidget(profile_lbl)
        self.profile_combo = QComboBox()
        self.profile_combo.setStyleSheet(_COMBO_STYLE)
        top_layout.addWidget(self.profile_combo)

        root_vbox.addWidget(self.top_bar)

        # ── Body: left + right ─────────────────────────────────────────── #
        body_row = QHBoxLayout()
        body_row.setSpacing(16)

        # Left — Project List ──────────────────────────────────────────── #
        self.left_panel = GlassSurface(self.overlay, blur_radius=24, frost_opacity=0.12)
        self.left_panel.setFixedWidth(280)
        left_vbox = QVBoxLayout(self.left_panel)
        left_vbox.setContentsMargins(16, 20, 16, 20)
        left_vbox.setSpacing(10)

        proj_header = QLabel("Projects")
        proj_header.setStyleSheet(_LABEL_STYLE % ("15", "bold"))
        left_vbox.addWidget(proj_header)

        self._divider(left_vbox)

        self.project_list = QListWidget()
        self.project_list.setStyleSheet(_LIST_STYLE)
        self.project_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.project_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.project_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.project_list.currentRowChanged.connect(self._on_project_changed)
        left_vbox.addWidget(self.project_list)

        body_row.addWidget(self.left_panel)

        # Right — Operations ───────────────────────────────────────────── #
        self.right_panel = GlassSurface(self.overlay, blur_radius=30, frost_opacity=0.12)
        self.right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_vbox = QVBoxLayout(self.right_panel)
        right_vbox.setContentsMargins(28, 24, 28, 24)
        right_vbox.setSpacing(14)

        # Selected project header
        self.proj_title_lbl = QLabel("← Select a project")
        self.proj_title_lbl.setStyleSheet(_LABEL_STYLE % ("18", "bold"))
        self.proj_path_lbl = QLabel("")
        self.proj_path_lbl.setStyleSheet(_SUBTLE_LABEL)
        right_vbox.addWidget(self.proj_title_lbl)
        right_vbox.addWidget(self.proj_path_lbl)

        self._divider(right_vbox)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        self.btn_diff   = StarBorderButton("⚡  Diff Check")
        self.btn_backup = StarBorderButton("🗂  Write Backup")
        self.btn_cancel = FluidGlassButton("⏹  Cancel")
        self.btn_cancel.setEnabled(False)

        self.btn_diff.clicked.connect(self._run_diff)
        self.btn_backup.clicked.connect(self._run_backup)
        self.btn_cancel.clicked.connect(self._cancel_operation)

        btn_row.addWidget(self.btn_diff)
        btn_row.addWidget(self.btn_backup)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)
        right_vbox.addLayout(btn_row)

        # Progress area
        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(_PROGRESS_STYLE)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        self.progress_label = QLabel("Idle")
        self.progress_label.setStyleSheet(_SUBTLE_LABEL)
        self.progress_label.setFixedWidth(240)
        progress_row.addWidget(self.progress_bar)
        progress_row.addWidget(self.progress_label)
        right_vbox.addLayout(progress_row)

        self._divider(right_vbox)

        # Log output
        log_header = QLabel("Operation Log")
        log_header.setStyleSheet(_LABEL_STYLE % ("13", "600"))
        right_vbox.addWidget(log_header)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(_LOG_STYLE)
        self.log_output.setPlaceholderText("Select a project and run an operation…")
        right_vbox.addWidget(self.log_output)

        # Bottom: status strip
        self._divider(right_vbox)
        self.status_lbl = QLabel("Ready  ·  Tayberry Backup Studio")
        self.status_lbl.setStyleSheet(_SUBTLE_LABEL)
        right_vbox.addWidget(self.status_lbl)

        body_row.addWidget(self.right_panel)
        root_vbox.addLayout(body_row)

        # ── Load config ────────────────────────────────────────────────── #
        self._load_config()

        # ── Controls Pill (absolute, top-right) — optional ─────────────── #
        # (omit in the merged app to keep UI focused)

        # ── Initial resize ─────────────────────────────────────────────── #
        self._fit_overlay()

    # ---------------------------------------------------------------------- #
    # Layout helpers
    # ---------------------------------------------------------------------- #
    def _divider(self, layout: QVBoxLayout) -> None:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(_DIVIDER_STYLE)
        layout.addWidget(line)

    def _fit_overlay(self) -> None:
        self.overlay.setGeometry(0, 0, self.width(), self.height())

    def resizeEvent(self, event) -> None:
        self._fit_overlay()
        super().resizeEvent(event)

    # ---------------------------------------------------------------------- #
    # Config / project loading
    # ---------------------------------------------------------------------- #
    def _load_config(self) -> None:
        config_path = _resources_dir() / "backup_projects.json"
        if not config_path.exists():
            self._log_line("⚠️  backup_projects.json not found — place it in app/resources/")
            return
        try:
            self._app_config = load_app_config(config_path)
            self._projects   = list(self._app_config.projects.values())
            self._populate_projects()
            self._populate_profiles()
            self._log_line(f"✅  Loaded {len(self._projects)} projects from config.")
        except Exception as exc:  # noqa: BLE001
            self._log_line(f"❌  Config error: {exc}")

    def _populate_projects(self) -> None:
        self.project_list.clear()
        for proj in self._projects:
            item = QListWidgetItem(f"  {proj.label}")
            item.setData(Qt.ItemDataRole.UserRole, proj.id)
            item.setSizeHint(item.sizeHint().__class__(0, 38))
            self.project_list.addItem(item)

    def _populate_profiles(self) -> None:
        if not self._app_config:
            return
        self.profile_combo.clear()
        for pid, prof in self._app_config.profiles.items():
            self.profile_combo.addItem(prof.label, userData=pid)

    # ---------------------------------------------------------------------- #
    # Project selection
    # ---------------------------------------------------------------------- #
    def _on_project_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._projects):
            return
        self._selected_project = self._projects[row]
        p = self._selected_project
        self.proj_title_lbl.setText(p.label)
        self.proj_path_lbl.setText(str(p.project_root))
        self.status_lbl.setText(f"Selected: {p.label}  ·  {p.project_root}")

    # ---------------------------------------------------------------------- #
    # Operations
    # ---------------------------------------------------------------------- #
    def _current_profile(self):
        if not self._app_config:
            return None
        pid = self.profile_combo.currentData()
        return self._app_config.profiles.get(pid)

    def _run_diff(self) -> None:
        self._start_operation(dry_run=True)

    def _run_backup(self) -> None:
        self._start_operation(dry_run=False)

    def _start_operation(self, dry_run: bool) -> None:
        if not self._selected_project:
            self._log_line("⚠️  Please select a project first.")
            return
        if not self._app_config:
            self._log_line("⚠️  Config not loaded.")
            return
        profile = self._current_profile()
        if not profile:
            self._log_line("⚠️  No profile selected.")
            return
        if self._worker and self._worker.isRunning():
            self._log_line("⚠️  An operation is already running.")
            return

        self.log_output.clear()
        label = "Diff Check" if dry_run else "Write Backup"
        self._log_line(f"▶  Starting {label}  ·  {self._selected_project.label}  ·  profile: {profile.label}")

        self._set_busy(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting…")

        self._worker = BackupWorker(
            app_config=self._app_config,
            project=self._selected_project,
            profile=profile,
            dry_run=dry_run,
            note="",
            parent=self,
        )
        self._worker.log.connect(self._log_line)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished_ok)
        self._worker.finished_error.connect(self._on_finished_error)
        self._worker.start()

    def _cancel_operation(self) -> None:
        if self._worker:
            self._worker.cancel()
            self._log_line("⏹  Cancel requested…")

    # ---------------------------------------------------------------------- #
    # Worker callbacks
    # ---------------------------------------------------------------------- #
    def _log_line(self, msg: str) -> None:
        self.log_output.append(msg)

    def _on_progress(self, idx: int, total: int, label: str) -> None:
        pct = int((idx / total) * 100) if total else 0
        self.progress_bar.setValue(pct)
        self.progress_label.setText(f"{label}  ({idx}/{total})")

    def _on_finished_ok(self, result) -> None:
        self._set_busy(False)
        self.progress_bar.setValue(100)
        self.progress_label.setText("Done ✓")
        files = len(result.created_files) if result.created_files else 0
        dry = " [DRY RUN]" if result.is_dry_run else ""
        self._log_line(f"✅  Completed{dry}  ·  {files} files  ·  "
                       f"{result.duration_seconds:.1f}s" if result.duration_seconds else "✅  Completed.")
        self.status_lbl.setText(f"Last operation finished{dry}")

    def _on_finished_error(self, msg: str) -> None:
        self._set_busy(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Error")
        self._log_line(f"❌  {msg}")
        self.status_lbl.setText("Error during operation")

    # ---------------------------------------------------------------------- #
    # UI state helpers
    # ---------------------------------------------------------------------- #
    def _set_busy(self, busy: bool) -> None:
        self.btn_diff.setEnabled(not busy)
        self.btn_backup.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy)
        self.profile_combo.setEnabled(not busy)
        self.project_list.setEnabled(not busy)
