#!/usr/bin/env python3
"""
Simple build script to create a standalone .app bundle for Liquid Glass Demo
using PyInstaller.

Author: Amirhosein Rezapour | techili.ir
"""

import os
import sys
import shutil
import subprocess

def build():
    try:
        import PyInstaller
    except ImportError:
        print("Error: PyInstaller is not installed.")
        print("Please run: pip install pyinstaller")
        sys.exit(1)

    print("Building Liquid Glass Demo.app...")
    
    # Clean previous builds
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")

    # Entry point
    main_script = os.path.join("app", "main.py")
    
    # PyInstaller arguments
    args = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--windowed",  # No console window
        "--name=Liquid Glass Demo",
        "--icon=app/resources/icon.icns" if os.path.exists("app/resources/icon.icns") else "",
        "--add-data=app/resources:app/resources",  # Include resources
        main_script
    ]
    
    # Filter empty args
    args = [a for a in args if a]
    
    subprocess.check_call(args)
    
    print("\nBuild complete!")
    print(f"Your app is located at: {os.path.abspath('dist/Liquid Glass Demo.app')}")
    print("You can double-click it to run.")

if __name__ == "__main__":
    build()
