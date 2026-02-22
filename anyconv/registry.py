from __future__ import annotations
from .core import Registry

def build_registry() -> Registry:
    reg = Registry()

    # images
    from .converters.images import (
        png_to_jpg, jpg_to_png, webp_to_png,
        png_to_webp, jpg_to_webp
    )
    reg.register("png", "jpg", png_to_jpg)
    reg.register("jpg", "png", jpg_to_png)
    reg.register("jpeg", "png", jpg_to_png)
    reg.register("webp", "png", webp_to_png)
    reg.register("png", "webp", png_to_webp)
    reg.register("jpg", "webp", jpg_to_webp)
    reg.register("jpeg", "webp", jpg_to_webp)

    # md/html/pdf
    from .converters.md_html import md_to_html
    from .converters.html_pdf import html_to_pdf
    reg.register("md", "html", md_to_html)
    reg.register("html", "pdf", html_to_pdf)

    # csv/xlsx
    from .converters.csv_xlsx import csv_to_xlsx, xlsx_to_csv
    reg.register("csv", "xlsx", csv_to_xlsx)
    reg.register("xlsx", "csv", xlsx_to_csv)

    # txt/pdf
    from .converters.txt_pdf import txt_to_pdf
    reg.register("txt", "pdf", txt_to_pdf)

    # docx/pdf (optional)
    try:
        from .converters.docx_pdf_win import docx_to_pdf_win
        reg.register("docx", "pdf", docx_to_pdf_win)
    except Exception:
        pass

    return reg
