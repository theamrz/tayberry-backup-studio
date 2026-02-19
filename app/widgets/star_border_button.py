"""
Star Border Button

Liquid style button with animated rotating gradient border.
Mimics the 'React Bits' StarBorder component.

Author: Amirhosein Rezapour | techili.ir | tayberry.ir | tayberry.dev
"""

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QConicalGradient, QBrush, QPen, QFont, QPainterPath

class StarBorderButton(QPushButton):
    def __init__(self, text="Click Me", parent=None):
        super().__init__(text, parent)
        self.setFixedSize(200, 50)
        self.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate_border)
        self.timer.start(16)
        
        # Colors
        self.bg_color = QColor(10, 10, 30)
        self.text_color = QColor(255, 255, 255)
        self.border_width = 3.0
        self.glow_color = QColor(0, 255, 255) # Cyan

    def rotate_border(self):
        self.angle = (self.angle + 2) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        radius = 24.0
        
        # 1. Clip to Rounded shape
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), radius, radius)
        painter.setClipPath(path)

        # 2. Draw animated border (Conical Gradient)
        # Use a square larger than rect to cover rotaton
        side = max(rect.width(), rect.height()) * 1.5
        grad_rect = QRectF(0, 0, side, side)
        grad_rect.moveCenter(QPointF(rect.center()))
        
        gradient = QConicalGradient(QPointF(rect.center()), self.angle)
        gradient.setColorAt(0.0, QColor("#00FFFF")) # Cyan
        gradient.setColorAt(0.25, Qt.GlobalColor.transparent)
        gradient.setColorAt(0.5, QColor("#FF00FF")) # Magenta
        gradient.setColorAt(0.75, Qt.GlobalColor.transparent)
        gradient.setColorAt(1.0, QColor("#00FFFF"))
        
        painter.fillRect(rect, QBrush(gradient))
        
        # 3. Draw Inner Background (Masking the center)
        # Indent by border width
        inner_rect = QRectF(rect).adjusted(3, 3, -3, -3)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner_rect, radius - 2, radius - 2)
        
        painter.fillPath(inner_path, self.bg_color)
        
        # 4. Draw Text
        painter.setPen(self.text_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        
        # 5. Optional: Glow overlay on hover
        if self.underMouse():
            painter.setBrush(QBrush(QColor(255, 255, 255, 20)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, radius, radius)
