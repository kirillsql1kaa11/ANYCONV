from __future__ import annotations
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

from .core import ConvertJob
from .registry import build_registry

app = typer.Typer(add_completion=False)
console = Console()
reg = build_registry()

def iter_files(src: Path, recursive: bool) -> list[Path]:
    if src.is_file():
        return [src]
    pat = "**/*" if recursive else "*"
    return [p for p in src.glob(pat) if p.is_file()]

def build_dst(src_file: Path, out_dir: Path | None, to_ext: str) -> Path:
    if out_dir:
        return out_dir / (src_file.stem + "." + to_ext)
    return src_file.with_suffix("." + to_ext)

@app.command()
def list():
    """Показать поддерживаемые конвертации."""
    t = Table(title="Supported conversions")
    t.add_column("from")
    t.add_column("to")
    for frm, to in reg.supported():
        t.add_row(frm, to)
    console.print(t)

@app.command()
def convert(
    src: Path = typer.Argument(..., help="Файл или папка"),
    to: str = typer.Argument(..., help="Целевое расширение (например: pdf, html, xlsx)"),
    out: Path | None = typer.Option(None, "--out", "-o", help="Папка вывода (по умолчанию рядом с файлом)"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="Рекурсивно для папок"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Перезаписывать выходные файлы"),
):
    """Конвертация файлов в заданный формат."""
    src = src.expanduser()
    files = iter_files(src, recursive=recursive)
    if not files:
        raise typer.BadParameter("Нет файлов для конвертации.")

    if out:
        out = out.expanduser()
        out.mkdir(parents=True, exist_ok=True)

    ok, fail = 0, 0
    rows: list[tuple[str, str, str]] = []

    to_ext = to.lower().lstrip(".")

    for f in files:
        frm = f.suffix.lower().lstrip(".")
        fn = reg.get(frm, to_ext)
        if not fn:
            rows.append((str(f), "skip", f"no converter {frm}->{to_ext}"))
            continue

        dst = build_dst(f, out, to_ext)
        if dst.exists() and not overwrite:
            rows.append((str(f), "skip", "exists (use --overwrite)"))
            continue

        try:
            job = ConvertJob(src=f, dst=dst, fmt_from=frm, fmt_to=to_ext)
            fn(job)
            ok += 1
            rows.append((str(f), "ok", str(dst)))
        except Exception as e:
            fail += 1
            rows.append((str(f), "fail", repr(e)))

    t = Table(title=f"Done: ok={ok}, fail={fail}")
    t.add_column("src", overflow="fold")
    t.add_column("status")
    t.add_column("info", overflow="fold")
    for r in rows[:200]:
        t.add_row(*r)
    if len(rows) > 200:
        t.add_row("...", "...", f"+{len(rows)-200} more")
    console.print(t)

def main():
    app()

if __name__ == "__main__":
    main()
