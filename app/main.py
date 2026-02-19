"""
Liquid Glass App Entry Point

Author: Amirhosein Rezapour | techili.ir | tayberry.ir | tayberry.dev
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QIcon
from .window import TayberryWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Tayberry Backup Studio")
    app.setOrganizationName("Techili")
    app.setOrganizationDomain("tayberry.dev")
    app.setApplicationDisplayName("Tayberry Backup Studio")
    
    # Create Window
    window = TayberryWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
