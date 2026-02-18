"""
Liquid Glass Main Window

The central assembly of the application.
Connects the Galaxy background, Glass surfaces, and controls.

Author: Amirhosein Rezapour | techili.ir | tayberry.ir | tayberry.dev
"""

from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon

from .widgets.galaxy_background import GalaxyBackgound
from .widgets.glass_surface import GlassSurface
from .widgets.star_border_button import StarBorderButton
from .widgets.controls_pill import ControlPill
from .widgets.fluid_glass import FluidInput, FluidGlassButton

class LiquidWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Liquid Glass Demo - techili.ir")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 700)
        
        # 1. Background Layer = Galaxy
        self.background = GalaxyBackgound(self)
        self.setCentralWidget(self.background)
        
        # 2. Main Glass Card (Floating Center)
        self.card = GlassSurface(self.background, blur_radius=30, frost_opacity=0.1)
        self.card.setFixedSize(400, 500)
        
        # Card Layout
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(20)
        
        # Title
        title = QLabel("Liquid Glass")
        title.setStyleSheet("color: white; font-size: 32px; font-weight: bold; font-family: 'Segoe UI', sans-serif;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("A PyQt6 Concept by Amirhosein Rezapour")
        subtitle.setStyleSheet("color: #aaa; font-size: 14px; font-style: italic;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(20)
        
        # Inputs
        self.input1 = FluidInput("Email Address")
        self.input2 = FluidInput("Password")
        self.input2.setEchoMode(FluidInput.EchoMode.Password)
        
        card_layout.addWidget(self.input1)
        card_layout.addWidget(self.input2)
        card_layout.addSpacing(30)
        
        # Buttons
        btn_row = QHBoxLayout()
        self.btn_primary = StarBorderButton("Login")
        self.btn_secondary = FluidGlassButton("Forgot?")
        
        # Just center align these or stack them? Let's stack them for mobile feel or row.
        # Given fixed size, let's stack.
        # Actually row looks better if they fit.
        # But StarBorder is fixed 200px wide. FluidGlass is 160. 
        # 400 total width - 80 margin = 320 available. They won't fit side-by-side.
        # Stack them.
        
        # Re-layout
        h_center1 = QHBoxLayout()
        h_center1.addStretch()
        h_center1.addWidget(self.btn_primary)
        h_center1.addStretch()
        
        h_center2 = QHBoxLayout()
        h_center2.addStretch()
        h_center2.addWidget(self.btn_secondary)
        h_center2.addStretch()
        
        card_layout.addLayout(h_center1)
        card_layout.addLayout(h_center2)
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

