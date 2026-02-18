"""
Fluid Glass Components

Interactive input fields and buttons with liquid-glass styling.

Author: Amirhosein Rezapour | techili.ir | tayberry.ir | tayberry.dev
"""

from PyQt6.QtWidgets import QLineEdit, QPushButton, QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush

class FluidInput(QLineEdit):
    def __init__(self, placeholder="Enter text...", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 50);
                background: rgba(0, 0, 0, 20);
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-bottom: 2px solid #00FFFF;
                background: rgba(0, 0, 0, 40);
            }
        """)
        
class FluidGlassButton(QPushButton):
    def __init__(self, text="Glass Button", parent=None):
        super().__init__(text, parent)
        self.setFixedSize(160, 45)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover_progress = 0.0
        
        self.bg_color = QColor(255, 255, 255, 15)
        self.hover_color = QColor(255, 255, 255, 30)
        self.border_color = QColor(255, 255, 255, 40)
        
    def enterEvent(self, event):
        self.bg_color = self.hover_color
        self.update()
        
    def leaveEvent(self, event):
        self.bg_color = QColor(255, 255, 255, 15)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        path = QRectF(rect)
        radius = 22.5
        
        # Glass Body
        painter.setBrush(QBrush(self.bg_color))
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRoundedRect(path, radius, radius)
        
        # Text
        painter.setPen(Qt.GlobalColor.white)
        font = QFont("Segoe UI", 10)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        
        # Shine
        if self.underMouse():
            shine_rect = QRectF(0, 0, rect.width(), rect.height() / 2)
            grad = QBrush(QColor(255, 255, 255, 10))
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(shine_rect, radius, radius)

