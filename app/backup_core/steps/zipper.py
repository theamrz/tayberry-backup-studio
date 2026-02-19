from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import zipfile
import os

import shutil


@dataclass
class ZipStats:
    zip_path: Optional[Path] = None


def create_zip(backup_dir: Path, output_dir: Path, compression_level: int = 6) -> ZipStats:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"{backup_dir.name}.zip"
    archive_path = output_dir / archive_name
    
    # Use zipfile directly to support compression levels
    with zipfile.ZipFile(
        archive_path, 
        'w', 
        compression=zipfile.ZIP_DEFLATED, 
        compresslevel=compression_level
    ) as zf:
        # Walk the directory and add files
        for root, _, files in os.walk(backup_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(backup_dir.parent)
                zf.write(file_path, arcname)
                
    return ZipStats(zip_path=archive_path)
