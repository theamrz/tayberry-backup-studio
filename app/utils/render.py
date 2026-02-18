"""
Liquid Glass Rendering Utilities

This module provides optimized rendering helpers for:
- Gaussian Blur (simulated or real)
- Noise Generation
- Color Utilities
- Offscreen Rendering

Author: Amirhosein Rezapour
Web: techili.ir | tayberry.ir | tayberry.dev
"""

from PyQt6.QtGui import QImage, QColor, QPainter, QBrush, QPixmap, QLinearGradient, QRadialGradient
from PyQt6.QtCore import Qt, QRectF, QPointF
import random
import math

def apply_blur(pixmap: QPixmap, radius: float) -> QPixmap:
    """
    Applies a gaussian blur to a QPixmap using QImage processing.
    For performance, we downscale, blur, and upscale.
    """
    if radius <= 0:
        return pixmap
    
    # Downscale for performance (and to simulate blur)
    scale = max(0.1, 1.0 - (radius / 50.0))
    w = pixmap.width()
    h = pixmap.height()
    
    downscaled = pixmap.scaled(
        int(w * scale), int(h * scale),
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )
    
    # Upscale back to original size + extra smooth
    blurred = downscaled.scaled(
        w, h,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )
    
    return blurred

def generate_noise_texture(width: int, height: int, opacity: float = 0.05) -> QPixmap:
    """ Generates a subtle grain/noise texture. """
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(image)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
    
    # Create random noise pixels
    for _ in range(int(width * height * 0.1)):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        val = random.randint(200, 255)
        color = QColor(val, val, val, int(255 * opacity))
        painter.setPen(color)
        painter.drawPoint(x, y)
        
    painter.end()
    return QPixmap.fromImage(image)

def create_glass_gradient(rect: QRectF, color: QColor, angle: float = 45) -> QLinearGradient:
    """ Creates a standard glass sheen gradient. """
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, QColor(255, 255, 255, 30))
    gradient.setColorAt(0.5, color)
    gradient.setColorAt(1.0, QColor(255, 255, 255, 10))
    return gradient

class PerformanceMonitor:
    """ Tracks FPS and rendering stats. """
    def __init__(self):
        self.frame_count = 0
        self.last_time = 0
        self.fps = 0.0
        
    def update(self, current_time: float):
        self.frame_count += 1
        delta = current_time - self.last_time
        if delta >= 1.0:
            self.fps = self.frame_count / delta
            self.frame_count = 0
            self.last_time = current_time
            return True # FPS updated
        return False
