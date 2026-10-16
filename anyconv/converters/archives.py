from __future__ import annotations

import zipfile
from pathlib import Path

from ..core import human_size


def zip_path(src: Path, dst: Path) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
        if src.is_dir():
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(src.parent))
        else:
            zf.write(src, src.name)
    return human_size(dst.stat().st_size)


def unzip_path(src: Path, dst_dir: Path) -> str:
    dst_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as zf:
        names = zf.namelist()
        zf.extractall(dst_dir)
    return f"{len(names)} записей"
