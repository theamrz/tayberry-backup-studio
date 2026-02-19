#!/usr/bin/env python3
"""
Simple build script to create a standalone .app bundle for Liquid Glass Demo
and package it into a .dmg using hdiutil.

Author: Amirhosein Rezapour | techili.ir
"""

import os
import sys
import shutil
import subprocess

def create_dmg(app_path):
    """Create a DMG from the .app bundle."""
    dmg_name = "LiquidGlassDemo.dmg"
    print(f"Creating {dmg_name}...")
    
    # Create a temporary folder to prepare the DMG content
    dmg_source = "dmg_source"
    if os.path.exists(dmg_source):
        shutil.rmtree(dmg_source)
    os.makedirs(dmg_source)
    
    # Copy the .app to the source folder
    app_base_name = os.path.basename(app_path)
    shutil.copytree(app_path, os.path.join(dmg_source, app_base_name))
    
    # Create a symlink to /Applications
    os.symlink("/Applications", os.path.join(dmg_source, "Applications"))
    
    # Remove existing DMG
    if os.path.exists(dmg_name):
        os.remove(dmg_name)
    
    # Run hdiutil (macOS specific)
    try:
        subprocess.check_call([
            "hdiutil", "create",
            "-volname", "Liquid Glass Demo Installer",
            "-srcfolder", dmg_source,
            "-ov",
            "-format", "UDZO",
            dmg_name
        ])
        print(f"DMG created at {os.path.abspath(dmg_name)}")
    except FileNotFoundError:
        print("Warning: hdiutil not found. DMG can only be created on macOS.")
    except Exception as e:
        print(f"Warning: Failed to create DMG: {e}")
    finally:
        # Cleanup
        if os.path.exists(dmg_source):
            shutil.rmtree(dmg_source)

def build():
    # Ensure dependencies
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
    
    # Check if entry point exists
    if not os.path.exists(main_script):
        print(f"Error: {main_script} does not exist.")
        sys.exit(1)
        
    # Resources
    resources_path = os.path.join("app", "resources")
    icon_path = os.path.join(resources_path, "icon.icns")
    
    # PyInstaller arguments
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",  # No console window
        "--name", "Liquid Glass Demo",
        "--add-data", f"{resources_path}:app/resources",  # Include resources folder
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "PyQt6.QtWidgets",
    ]
    
    # Add icon if exists
    if os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])
        
    cmd.append(main_script)
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    
    app_path = os.path.join("dist", "Liquid Glass Demo.app")
    if os.path.exists(app_path):
        print(f"Success! App created at: {os.path.abspath(app_path)}")
        create_dmg(app_path)
    else:
        print("Build failed: App bundle not found in dist/")

if __name__ == "__main__":
    # Ensure we are in the project root
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # os.chdir(script_dir)
        
    build()
