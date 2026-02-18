"""
Liquid Glass App Entry Point

Author: Amirhosein Rezapour | techili.ir | tayberry.ir | tayberry.dev
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QIcon
from .window import LiquidWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Liquid Glass Demo")
    app.setOrganizationName("TBcms")
    app.setOrganizationDomain("tayberry.dev")
    
    # Load default font
    # font_db = QFontDatabase()
    # If font file existed, we'd load it. Using system fonts for now.
    
    # Create Window
    window = LiquidWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
