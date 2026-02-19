"""
Liquid Glass Main Window

The central assembly of the application.
Connects the Galaxy background, Glass surfaces, and controls.

Author: Amirhosein Rezapour | techili.ir | tayberry.ir | tayberry.dev
"""

from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QAction

from .widgets.galaxy_background import GalaxyBackgound
from .widgets.glass_surface import GlassSurface
from .widgets.star_border_button import StarBorderButton
from .widgets.controls_pill import ControlPill
from .widgets.fluid_glass import FluidInput, FluidGlassButton

class LiquidWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TBcms Backup Studio - Liquid Edition")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 700)
        
        # 1. Background Layer = Galaxy
        self.background = GalaxyBackgound(self)
        self.setCentralWidget(self.background)
        
        # Top-Left Logo Branding
        self.logo_brand = QLabel(self.background)
        logo_pix = QPixmap("app/resources/logo.png")
        if not logo_pix.isNull():
            scaled_logo = logo_pix.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_brand.setPixmap(scaled_logo)
            self.logo_brand.move(40, 40)
            
            # Add Brand Name next to logo
            self.brand_text = QLabel("TBcms Backup Studio", self.background)
            self.brand_text.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 24px; font-weight: bold; font-family: 'Segoe UI', sans-serif;")
            self.brand_text.move(130, 65)

        # 2. Main Glass Card (Floating Center)
        self.card = GlassSurface(self.background, blur_radius=40, frost_opacity=0.15)
        self.card.setFixedSize(500, 600)
        
        # Card Layout
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(50, 50, 50, 50)
        card_layout.setSpacing(25)
        
        # Center Logo
        center_logo = QLabel()
        if not logo_pix.isNull():
            center_logo.setPixmap(logo_pix.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        center_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(center_logo)

        # Title
        title = QLabel("Backup Operations")
        title.setStyleSheet("color: white; font-size: 28px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)
        
        subtitle = QLabel("Select an action below")
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 14px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)
        
        card_layout.addSpacing(20)
        
        # Inputs (Mock Project Selection)
        self.project_input = FluidInput("Select Project Path...")
        card_layout.addWidget(self.project_input)
        
        card_layout.addSpacing(10)

        # Action Buttons
        # Row 1: Primary Actions
        btn_row = QHBoxLayout()
        
        self.btn_diff = StarBorderButton("Diff Check")
        self.btn_backup = StarBorderButton("Write Backup")
        
        # Adjust button styles if needed, or just let them be consistent
        btn_row.addWidget(self.btn_diff)
        btn_row.addSpacing(20)
        btn_row.addWidget(self.btn_backup)
        
        card_layout.addLayout(btn_row)
        
        # Row 2: Secondary / Quick
        btn_row_2 = QHBoxLayout()
        self.btn_settings = FluidGlassButton("Settings")
        self.btn_sync = FluidGlassButton("Cloud Sync")
        
        btn_row_2.addWidget(self.btn_settings)
        btn_row_2.addSpacing(10)
        btn_row_2.addWidget(self.btn_sync)
        
        card_layout.addSpacing(10)
        card_layout.addLayout(btn_row_2)

        card_layout.addStretch()
        
        # 3. Control Pill (Floating Top-Right)
        self.controls = ControlPill(self.background)
        self.controls.move(self.width() - 250, 40)
        
        # Connect Controls
        self.controls.settingsChanged.connect(self.update_settings)
        
        self.center_card()

    def resizeEvent(self, event):
        self.center_card()
        # Keep controls anchored
        self.controls.move(self.width() - 250, 40)
        super().resizeEvent(event)
        
    def center_card(self):
        cx = (self.width() - self.card.width()) // 2
        cy = (self.height() - self.card.height()) // 2
        self.card.move(cx, cy)
        
    def update_settings(self, settings):
        # Apply changes to the card
        if "blur" in settings:
            self.card.blur_radius = settings["blur"]
        if "frost" in settings:
            self.card.frost_opacity = settings["frost"]
        
        # Trigger repaint
        self.card.update()

