from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from ..core import ConvertJob, ensure_parent

FONT_SIZE = 11.0
LINE_HEIGHT = 15.5
MARGIN = 46.0

_font_cache: str | None = None


def _font_candidates() -> list[tuple[str, str]]:
    candidates = [
        ("SegoeUI", r"C:\Windows\Fonts\segoeui.ttf"),
        ("Arial", r"C:\Windows\Fonts\arial.ttf"),
    ]
    try:
        import matplotlib

        dejavu = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"
        candidates.append(("DejaVuSans", str(dejavu)))
    except Exception:
        pass
    return candidates


def _find_font() -> str:
    global _font_cache
    if _font_cache:
        return _font_cache
    for name, path in _font_candidates():
        if not os.path.exists(path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, path))
        except Exception:
            continue
        _font_cache = name
        return name
    _font_cache = "Helvetica"
    return _font_cache


def _wrap_line(c: canvas.Canvas, text: str, font: str, size: float, max_w: float) -> list[str]:
    if not text:
        return [""]
    if pdfmetrics.stringWidth(text, font, size) <= max_w:
        return [text]
    lines: list[str] = []
    words = text.split(" ")
    cur = ""
    for word in words:
        candidate = word if not cur else cur + " " + word
        if pdfmetrics.stringWidth(candidate, font, size) <= max_w:
            cur = candidate
            continue
        if cur:
            lines.append(cur)
            cur = ""
        while pdfmetrics.stringWidth(word, font, size) > max_w:
            cut = len(word)
            while cut > 1 and pdfmetrics.stringWidth(word[:cut], font, size) > max_w:
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
        cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def txt_to_pdf(job: ConvertJob) -> None:
    ensure_parent(job.dst)
    font = _find_font()
    text = job.src.read_text(encoding="utf-8", errors="ignore")
    c = canvas.Canvas(str(job.dst), pagesize=A4)
    width, height = A4
    max_w = width - 2 * MARGIN
    y = height - MARGIN
    c.setFont(font, FONT_SIZE)
    for raw in text.splitlines() or [""]:
        raw = raw.replace("\t", "    ")
        for line in _wrap_line(c, raw, font, FONT_SIZE, max_w):
            if y < MARGIN:
                c.showPage()
                c.setFont(font, FONT_SIZE)
                y = height - MARGIN
            c.drawString(MARGIN, y, line)
            y -= LINE_HEIGHT
    c.save()
