"""
Galaxy Background Widget

Animated particle simulation for the liquid glass effect.
Features parallax, glowing nebula, and starfields.

Author: Amirhosein Rezapour | techili.ir | tayberry.ir | tayberry.dev
"""

import math
import random
import time
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QBrush, QPixmap, QImage, QPen

class Nebula:
    def __init__(self, color, center, radius, drift):
        self.color = color
        self.center = list(center)
        self.radius = radius
        self.drift = drift
        self.phase = random.random() * math.pi * 2
        
    def update(self):
        self.phase += 0.01
        self.center[0] += math.sin(self.phase) * self.drift
        self.center[1] += math.cos(self.phase) * self.drift

class GalaxyBackgound(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stars = []
        self.nebulae = []
        self.mouse_pos = QPointF(0, 0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(16)  # ~60 FPS
        
        self.init_universe()
        
    def init_universe(self):
        w = self.width() if self.width() > 0 else 1200
        h = self.height() if self.height() > 0 else 800
        
        # Stars
        for _ in range(300):
            self.stars.append({
                'x': random.uniform(0, w),
                'y': random.uniform(0, h),
                'size': random.uniform(1.0, 3.0),
                'depth': random.uniform(0.1, 1.0), # parallax depth
                'alpha': random.uniform(0.5, 1.0),
                'twinkle': random.choice([True, False]),
                'velocity': random.uniform(0.1, 0.5)
            })
            
        # Nebulae
        self.nebulae.append(Nebula(QColor(60, 0, 100, 40), (w/2, h/2), 600, 0.5))
        self.nebulae.append(Nebula(QColor(0, 100, 255, 30), (w/4, h/4), 400, 0.3))
        self.nebulae.append(Nebula(QColor(255, 0, 150, 20), (3*w/4, h/4), 500, 0.4))

    def update_simulation(self):
        w = self.width()
        h = self.height()
        
        if random.random() < 0.05: # Random meteor-like flash?
            pass
            
        # Update Stars
        for s in self.stars:
            # Twinkle
            if s['twinkle']:
                s['alpha'] += random.uniform(-0.02, 0.02)
                s['alpha'] = max(0.4, min(1.0, s['alpha']))
                
            # Move
            s['y'] += s['velocity'] * s['depth']
            if s['y'] > h:
                s['y'] = -10
                s['x'] = random.uniform(0, w)
                
        # Update Nebulae
        for n in self.nebulae:
            n.update()
            
        self.update() # Trigger repaint
        
    def mouseMoveEvent(self, event):
        self.mouse_pos = event.position()
        self.update() # Parallax update
        super().mouseMoveEvent(event)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw Background (Deep Space)
        painter.fillRect(self.rect(), QColor(5, 5, 20)) # Very dark blue/black
        
        mx = self.mouse_pos.x()
        my = self.mouse_pos.y()
        cx = self.width() / 2
        cy = self.height() / 2
        
        # Draw Nebulae (Glows)
        for n in self.nebulae:
            parallax_x = (mx - cx) * 0.02 * (1.0 / n.radius) * 100
            parallax_y = (my - cy) * 0.02 * (1.0 / n.radius) * 100
            
            grad = QRadialGradient(n.center[0] + parallax_x, n.center[1] + parallax_y, n.radius)
            grad.setColorAt(0, n.color)
            grad.setColorAt(1, Qt.GlobalColor.transparent)
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(n.center[0] + parallax_x, n.center[1] + parallax_y), n.radius, n.radius)
            
        # Draw Stars
        painter.setPen(Qt.PenStyle.NoPen)
        for s in self.stars:
            # Parallax Logic
            px_off = (mx - cx) * 0.05 * s['depth']
            py_off = (my - cy) * 0.05 * s['depth']
            
            x = s['x'] + px_off
            y = s['y'] + py_off
            
            # Simple bounds check for wrap around (for smooth parallax feel)
            if x < 0: x += self.width()
            if x > self.width(): x -= self.width()
            
            opacity = int(s['alpha'] * 255)
            color = QColor(255, 255, 255, opacity)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(x, y), s['size'], s['size'])
            
            # Extra glare/star shape for larger stars
            if s['size'] > 2.5:
                painter.setPen(QPen(QColor(255, 255, 255, int(opacity * 0.3)), 0.5))
                painter.drawLine(int(x - 5), int(y), int(x + 5), int(y))
                painter.drawLine(int(x), int(y - 5), int(x), int(y + 5))
                painter.setPen(Qt.PenStyle.NoPen)
