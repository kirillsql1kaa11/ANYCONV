from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__, engine, update
from .registry import build_registry

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()
reg = build_registry()

STATUS_STYLE = {"ok": "green", "skip": "yellow", "error": "red"}
STATUS_LABEL = {"ok": "ok", "skip": "skip", "error": "fail"}


@app.command()
def list() -> None:
    """Показать поддерживаемые конвертации."""
    t = Table(title="Поддерживаемые конвертации")
    t.add_column("из")
    t.add_column("в")
    for frm, to in reg.supported():
        t.add_row(frm, to)
    t.add_row("папка или файл", "zip (упаковать)")
    t.add_row("zip", "unpack (распаковать)")
    console.print(t)


@app.command()
def convert(
    src: Path = typer.Argument(..., help="Файл или папка"),
    to: str = typer.Argument(..., help="Целевой формат: pdf, html, xlsx, docx, png, zip, unpack…"),
    out: Path | None = typer.Option(None, "--out", "-o", help="Папка вывода (по умолчанию рядом с файлом)"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="Рекурсивно для папок"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Перезаписывать выходные файлы"),
    quality: int = typer.Option(85, "--quality", "-q", min=10, max=100, help="Качество JPEG/WebP"),
) -> None:
    """Конвертация файлов в заданный формат."""
    src = src.expanduser()
    if not src.exists():
        raise typer.BadParameter(f"Не найдено: {src}")
    out_dir = out.expanduser() if out else None

    rows: list[tuple[str, str, str]] = []

    def on_result(f: Path, owner: Path, status: str, message: str, index: int) -> None:
        rows.append((f.name, status, message))

    try:
        res = engine.run_batch(
            [src],
            to,
            out_dir,
            recursive=recursive,
            overwrite=overwrite,
            options={"quality": quality},
            registry=reg,
            on_result=on_result,
        )
    except KeyboardInterrupt:
        console.print("[yellow]Прервано пользователем[/]")
        raise typer.Exit(1)

    title = f"Готово: успешно {res.ok}, пропущено {res.skip}, ошибок {res.fail}"
    if res.cancelled:
        title = "Прервано · " + title
    t = Table(title=title)
    t.add_column("файл", overflow="fold")
    t.add_column("статус")
    t.add_column("результат", overflow="fold")
    for name, status, message in rows[:200]:
        style = STATUS_STYLE.get(status, "white")
        t.add_row(name, f"[{style}]{STATUS_LABEL.get(status, status)}[/]", message)
    if len(rows) > 200:
        t.add_row("...", "...", f"+{len(rows) - 200} ещё")
    console.print(t)


@app.command(name="check-update")
def check_update() -> None:
    """Проверить свежий релиз на GitHub."""
    result = update.check_for_update(__version__)
    if result is None:
        console.print(f"Обновлений нет. Текущая версия: {__version__}")
        return
    tag, url = result
    console.print(f"Доступна версия [bold green]{tag}[/]: {url}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
