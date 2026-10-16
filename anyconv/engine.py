from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

from .converters import archives
from .converters.html_pdf import close_batch_ctx
from .core import ConvertJob, Registry, human_size
from .registry import build_registry

SPECIAL_TARGETS = ("zip", "unpack")


@dataclass
class BatchResult:
    total: int = 0
    ok: int = 0
    fail: int = 0
    skip: int = 0
    cancelled: bool = False
    out_dir: Optional[Path] = None


def iter_files(src: Path, recursive: bool) -> list[Path]:
    if src.is_file():
        return [src]
    if not src.is_dir():
        return []
    found: list[Path] = []
    for root, dirs, files in os.walk(src):
        dirs.sort()
        found.extend(Path(root) / name for name in sorted(files))
        if not recursive:
            break
    return found


def expand_items(items: Sequence[Path], recursive: bool) -> list[tuple[Path, Path]]:
    seen: set[str] = set()
    out: list[tuple[Path, Path]] = []
    for it in items:
        for f in iter_files(it, recursive):
            key = os.path.normcase(str(f))
            if key in seen:
                continue
            seen.add(key)
            out.append((f, it))
    return out


def detect_exts(items: Sequence[Path], recursive: bool, cap: int = 4000) -> set[str]:
    exts: set[str] = set()
    count = 0
    for it in items:
        if it.is_file():
            exts.add(it.suffix.lower().lstrip("."))
            count += 1
            continue
        if not it.is_dir():
            continue
        for root, dirs, files in os.walk(it):
            dirs.sort()
            for name in files:
                exts.add(Path(name).suffix.lower().lstrip("."))
                count += 1
                if count >= cap:
                    return exts
            if not recursive:
                break
    return exts


def target_path(src: Path, owner: Path, out_dir: Optional[Path], to_ext: str) -> Path:
    if out_dir is None:
        return src.with_suffix("." + to_ext)
    base = owner if owner.is_dir() else owner.parent
    try:
        rel = src.relative_to(base)
    except ValueError:
        rel = Path(src.name)
    return out_dir / rel.with_suffix("." + to_ext)


def zip_dst_for(src: Path, out_dir: Optional[Path]) -> Path:
    base = out_dir if out_dir else src.parent
    if src.is_dir():
        return base / (src.name + ".zip")
    return base / (src.stem + ".zip")


def unpack_dir_for(src_zip: Path, out_dir: Optional[Path]) -> Path:
    name = src_zip.name
    stem = name[:-4] if name.lower().endswith(".zip") else src_zip.stem
    base = out_dir if out_dir else src_zip.parent
    return base / stem


def _unique_file(p: Path, used: set[str]) -> Path:
    key = os.path.normcase(str(p))
    if key not in used:
        used.add(key)
        return p
    n = 2
    while True:
        cand = p.with_name(f"{p.stem} ({n}){p.suffix}")
        k = os.path.normcase(str(cand))
        if k not in used:
            used.add(k)
            return cand
        n += 1


def _unique_dir(p: Path, used: set[str]) -> Path:
    key = os.path.normcase(str(p))
    if key not in used:
        used.add(key)
        return p
    n = 2
    while True:
        cand = p.with_name(f"{p.name} ({n})")
        k = os.path.normcase(str(cand))
        if k not in used:
            used.add(k)
            return cand
        n += 1


def _convert_one(
    f: Path,
    owner: Path,
    to_ext: str,
    out_dir: Optional[Path],
    overwrite: bool,
    reg: Registry,
    opts: dict,
    ctx: dict,
    used: set[str],
) -> tuple[str, str, Optional[Path]]:
    if not f.exists():
        return "skip", f"{f.name}: файл не найден", None
    frm = f.suffix.lower().lstrip(".")
    fn = reg.get(frm, to_ext)
    if fn is None:
        return "skip", f"{f.name}: нет конвертера {frm or '?'} → {to_ext}", None
    dst = target_path(f, owner, out_dir, to_ext)
    if dst == f:
        return "skip", f"{f.name}: совпадает с исходным файлом", None
    dst = _unique_file(dst, used)
    if dst.exists() and not overwrite:
        return "skip", f"{f.name}: уже существует — включите «Перезаписывать»", None
    job = ConvertJob(src=f, dst=dst, fmt_from=frm, fmt_to=to_ext, options=dict(opts), ctx=ctx)
    info = fn(job)
    msg = f"{f.name} → {dst.name}"
    if info:
        msg += f" · {info}"
    if dst.exists():
        msg += f" · {human_size(dst.stat().st_size)}"
    return "ok", msg, dst


def _zip_one(
    src: Path, out_dir: Optional[Path], overwrite: bool, used: set[str]
) -> tuple[str, str, Optional[Path]]:
    if not src.exists():
        return "skip", f"{src.name}: не найден", None
    dst = zip_dst_for(src, out_dir)
    if dst == src:
        return "skip", f"{src.name}: совпадает с исходным файлом", None
    dst = _unique_file(dst, used)
    if dst.exists() and not overwrite:
        return "skip", f"{src.name}: уже существует — включите «Перезаписывать»", None
    info = archives.zip_path(src, dst)
    return "ok", f"{src.name} → {dst.name} · {info}", dst


def _unpack_one(
    src: Path, out_dir: Optional[Path], overwrite: bool, used: set[str]
) -> tuple[str, str, Optional[Path]]:
    if not src.exists():
        return "skip", f"{src.name}: не найден", None
    if src.suffix.lower() != ".zip":
        return "skip", f"{src.name}: не ZIP-файл", None
    dst_dir = _unique_dir(unpack_dir_for(src, out_dir), used)
    if dst_dir.exists() and not overwrite:
        return "skip", f"{src.name}: папка уже существует — включите «Перезаписывать»", None
    info = archives.unzip_path(src, dst_dir)
    return "ok", f"{src.name} → {dst_dir.name}/ · {info}", dst_dir


def run_batch(
    items: Sequence[Path],
    to_ext: str,
    out_dir: Optional[Path],
    recursive: bool = True,
    overwrite: bool = False,
    options: Optional[dict] = None,
    registry: Optional[Registry] = None,
    on_start: Optional[Callable[[int], None]] = None,
    on_progress: Optional[Callable[[int, int, Path, Path], None]] = None,
    on_result: Optional[Callable[[Path, Path, str, str, int], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> BatchResult:
    to_ext = to_ext.lower().lstrip(".")
    reg = registry or build_registry()
    opts = dict(options or {})
    cancel = is_cancelled or (lambda: False)
    res = BatchResult()

    if to_ext == "zip":
        jobs = [(it, it) for it in items if it.exists()]
    else:
        jobs = expand_items(items, recursive)
    res.total = len(jobs)
    if on_start:
        on_start(len(jobs))

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

    used: set[str] = set()
    ctx: dict = {}
    try:
        for i, (f, owner) in enumerate(jobs, start=1):
            if cancel():
                res.cancelled = True
                break
            try:
                if to_ext == "unpack":
                    status, message, out_path = _unpack_one(f, out_dir, overwrite, used)
                elif to_ext == "zip":
                    status, message, out_path = _zip_one(f, out_dir, overwrite, used)
                else:
                    status, message, out_path = _convert_one(
                        f, owner, to_ext, out_dir, overwrite, reg, opts, ctx, used
                    )
            except Exception as e:
                status = "error"
                message = f"{f.name}: {str(e) or type(e).__name__}"
                out_path = None

            if status == "ok":
                res.ok += 1
                if res.out_dir is None and out_path is not None:
                    res.out_dir = out_path if out_path.is_dir() else out_path.parent
            elif status == "skip":
                res.skip += 1
            else:
                res.fail += 1

            if on_result:
                on_result(f, owner, status, message, i)
            if on_progress:
                on_progress(i, res.total, f, owner)
    finally:
        close_batch_ctx(ctx)
    return res
