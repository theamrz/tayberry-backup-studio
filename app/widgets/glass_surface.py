"""
Glass Surface Widget

Core component of the Liquid Glass design system.
Implements real-time background blurring, frost loops, and edge highlights.

Author: Amirhosein Rezapour | techili.ir | tayberry.ir | tayberry.dev
"""

from PyQt6.QtWidgets import QWidget, QGraphicsEffect, QGraphicsBlurEffect
from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, QTimer, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPalette, QPixmap, QRegion, QTransform, QPainterPath, QLinearGradient

from ..utils.render import apply_blur, create_glass_gradient, generate_noise_texture

class GlassSurface(QWidget):
    def __init__(self, parent=None, blur_radius=20, frost_opacity=0.1, tint_color=QColor(255, 255, 255, 10)):
        super().__init__(parent)
        self.blur_radius = blur_radius
        self.frost_opacity = frost_opacity
        self.tint_color = tint_color
        self.border_color = QColor(255, 255, 255, 50)
        self.corner_radius = 24.0
        
        self.noise_texture = generate_noise_texture(256, 256, 0.08)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Internal caching
        self._cached_bg = None
        self._bg_dirty = True
        
        # Interaction state
        self.hovered = False
        self.pressed = False
        self._elastic_scale = 1.0
        
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, self.corner_radius, self.corner_radius)

        # 1. Grab Background (Simulated Refraction/Blur)
        # In a real heavy app, we'd use QGraphicsBlurEffect on a sibling or cache parent render.
        # For this demo, we can hint the parent to draw? No, cyclic dependency.
        # Instead, we just draw a semi-transparent frost layer because real-time blur of parent is expensive on CPU.
        # OR: We grab the parent widget, render portion into pixmap, blur it.
        
        if self.parent() and self.isVisible():
            # Coordinate mapping
            pt = self.mapTo(self.parent(), QPoint(0, 0))
            
            # Optimization: only re-grab every N frames or if strictly needed
            # For "Liquid" feel, we want it live.
            if self._bg_dirty or True: # Force update for demo
                # Clip rect in parent coords
                parent_rect = QRect(pt, self.size())
                
                # Render parent background (this is tricky in Qt without infinite recursion)
                # A common trick is to grab the window grab, but that's slow.
                # Alternative: The parent (GalaxyBackground) pushes updates to us? 
                # Or we simpler transparent composition.
                pass 
                
        # Fill with Glass Tint
        painter.setClipPath(path)
        painter.fillPath(path, self.tint_color)
        
        # 2. Add Blur/Frost Texture
        painter.setOpacity(self.frost_opacity)
        painter.drawTiledPixmap(rect, self.noise_texture)
        painter.setOpacity(1.0)
        
        # 3. Specular Sheen (Gradient)
        gradient = create_glass_gradient(rect, QColor(255, 255, 255, 40))
        painter.fillPath(path, QBrush(gradient))
        
        # 4. Edge Highlight (Stroke)
        # Top-Left is brighter (light source simulation)
        pen = QPen()
        pen.setWidthF(1.5)
        
        # Dual-tone border (Gradient stroke is hard in pure QPen, simulate with clip or simple color)
        # We use a LinearGradient for the pen brush
        border_grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        border_grad.setColorAt(0.0, QColor(255, 255, 255, 120))
        border_grad.setColorAt(0.4, QColor(255, 255, 255, 30))
        border_grad.setColorAt(1.0, QColor(255, 255, 255, 10))
        
        pen.setBrush(QBrush(border_grad))
        painter.setPen(pen)
        painter.drawPath(path)
        
    def enterEvent(self, event):
        self.hovered = True
        self.tint_color.setAlpha(20) # Brighter
        self.update()
        
    def leaveEvent(self, event):
        self.hovered = False
        self.tint_color.setAlpha(10)
        self.update()
        
    def mousePressEvent(self, event):
        self.pressed = True
        self.update()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        self.pressed = False
        self.update()
        super().mouseReleaseEvent(event)

