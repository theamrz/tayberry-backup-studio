"""
Control Pill Widget

Floating glass panel for adjusting rendering parameters.

Author: Amirhosein Rezapour | techili.ir | tayberry.ir | tayberry.dev
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from .glass_surface import GlassSurface

class ControlPill(GlassSurface):
    settingsChanged = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent, blur_radius=30, frost_opacity=0.15, tint_color=QColor(0, 0, 0, 50))
        self.setFixedWidth(220)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Liquid Controls")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(title)
        
        # Function to create slider row
        def add_slider(label, key, min_val, max_val, default):
            lbl = QLabel(f"{label}: {default}")
            lbl.setStyleSheet("color: #aaa; font-size: 11px;")
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(default)
            slider.valueChanged.connect(lambda v: [
                lbl.setText(f"{label}: {v}"),
                self.emit_change(key, v)
            ])
            self.layout.addWidget(lbl)
            self.layout.addWidget(slider)
            
        add_slider("Blur Radius", "blur", 0, 100, 20)
        add_slider("Frost Opacity", "frost", 0, 100, 10) # 0.0 - 1.0 mapped to 0-100
        add_slider("Edge Brightness", "edge", 0, 255, 120)
        
        # Toggles
        self.gpu_check = QCheckBox("GPU Acceleration (Sim)")
        self.gpu_check.setStyleSheet("color: white;")
        self.gpu_check.setChecked(False) # Default OFF for stability
        self.layout.addWidget(self.gpu_check)
        
        self.layout.addStretch()
        
    def emit_change(self, key, value):
        # Convert range if needed
        real_val = value
        if key == "frost":
            real_val = value / 100.0
            
        self.settingsChanged.emit({key: real_val})

