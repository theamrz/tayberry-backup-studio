#!/usr/bin/env python3
"""
Tayberry Backup Studio — macOS App Builder

Creates a native .app bundle WITHOUT PyInstaller.
The bundle uses a shell-script launcher that calls the system Python3,
which avoids all segfault/library-conflict issues that PyInstaller
has with PyQt6 on macOS with Xcode Python.

Usage:
    python3 build_mac_app.py              # build only → dist/
    python3 build_mac_app.py --install    # build + install to /Applications
    python3 build_mac_app.py --dmg        # build + create DMG

Author: Amirhosein Rezapour | techili.ir | tayberry.dev
"""

from __future__ import annotations
import os, sys, shutil, subprocess, argparse
from pathlib import Path

# ─────────────────────────── Config ───────────────────────────── #
APP_NAME       = "Tayberry Backup Studio"
APP_BUNDLE     = f"{APP_NAME}.app"
BUNDLE_ID      = "dev.tayberry.backup-studio"
APP_VERSION    = "1.0.0"
EXECUTABLE     = "TayberryBackupStudio"
PYTHON_BIN     = "/usr/bin/python3"   # system Python — always present on macOS
MODULE         = "app_src.main"
# ──────────────────────────────────────────────────────────────── #

ROOT   = Path(__file__).parent
DIST   = ROOT / "dist"
BUNDLE = DIST / APP_BUNDLE


def clean():
    if BUNDLE.exists():
        shutil.rmtree(BUNDLE)
    DIST.mkdir(exist_ok=True)


def build():
    print(f"Building {APP_BUNDLE} ...")

    # Directory structure
    macos_dir     = BUNDLE / "Contents" / "MacOS"
    resources_dir = BUNDLE / "Contents" / "Resources"
    macos_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)

    # 1. Copy app source into Resources/app_src
    src_app = ROOT / "app"
    dst_app = resources_dir / "app_src"
    shutil.copytree(src_app, dst_app,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))

    # 2. Copy icon
    icon_src = src_app / "resources" / "icon.icns"
    if icon_src.exists():
        shutil.copy2(icon_src, resources_dir / "AppIcon.icns")

    # 3. Shell launcher
    launcher = macos_dir / EXECUTABLE
    launcher.write_text(
        "#!/bin/bash\n"
        "# Tayberry Backup Studio launcher\n"
        'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
        'RESOURCES_DIR="$SCRIPT_DIR/../Resources"\n'
        'cd "$RESOURCES_DIR"\n'
        f'exec {PYTHON_BIN} -m {MODULE} "$@"\n'
    )
    launcher.chmod(0o755)

    # 4. Info.plist
    (BUNDLE / "Contents" / "Info.plist").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>{APP_NAME}</string>
    <key>CFBundleDisplayName</key>
    <string>{APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>{BUNDLE_ID}</string>
    <key>CFBundleVersion</key>
    <string>{APP_VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>{APP_VERSION}</string>
    <key>CFBundleExecutable</key>
    <string>{EXECUTABLE}</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
</dict>
</plist>
""")

    # 5. PkgInfo
    (BUNDLE / "Contents" / "PkgInfo").write_bytes(b"APPL????")

    print(f"  Built:  {BUNDLE}")
    return BUNDLE


def install(bundle: Path):
    dest = Path("/Applications") / APP_BUNDLE
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(bundle, dest)
    # Register with LaunchServices
    lsreg = ("/System/Library/Frameworks/CoreServices.framework"
             "/Versions/A/Frameworks/LaunchServices.framework"
             "/Versions/A/Support/lsregister")
    subprocess.run([lsreg, "-f", str(dest)], check=False)
    print(f"  Installed → {dest}")


def make_dmg(bundle: Path):
    dmg = ROOT / "TayberryBackupStudio.dmg"
    staging = ROOT / "_dmg_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    shutil.copytree(bundle, staging / APP_BUNDLE)
    (staging / "Applications").symlink_to("/Applications")
    if dmg.exists():
        dmg.unlink()
    subprocess.check_call([
        "hdiutil", "create",
        "-volname", f"{APP_NAME} Installer",
        "-srcfolder", str(staging),
        "-ov", "-format", "UDZO",
        str(dmg),
    ])
    shutil.rmtree(staging)
    print(f"  DMG:    {dmg}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help="Also install to /Applications")
    parser.add_argument("--dmg",     action="store_true", help="Also create a DMG")
    args = parser.parse_args()

    clean()
    bundle = build()

    if args.install:
        install(bundle)
    if args.dmg:
        make_dmg(bundle)

    if not args.install and not args.dmg:
        # Default: install
        install(bundle)

    print("\nDone! Launch 'Tayberry Backup Studio' from Launchpad or Spotlight.")
