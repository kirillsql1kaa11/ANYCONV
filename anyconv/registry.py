from __future__ import annotations
import importlib.util

from .core import Registry


def build_registry() -> Registry:
    reg = Registry()

    from .converters.images import jpg_to_png, jpg_to_webp, png_to_jpg, png_to_webp, webp_to_png

    reg.register("png", "jpg", png_to_jpg)
    reg.register("jpg", "png", jpg_to_png)
    reg.register("jpeg", "png", jpg_to_png)
    reg.register("webp", "png", webp_to_png)
    reg.register("png", "webp", png_to_webp)
    reg.register("jpg", "webp", jpg_to_webp)
    reg.register("jpeg", "webp", jpg_to_webp)

    from .converters.pdf_images import image_to_pdf, pdf_to_jpg, pdf_to_png

    for ext in ("png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff", "gif"):
        reg.register(ext, "pdf", image_to_pdf)
    reg.register("pdf", "png", pdf_to_png)
    reg.register("pdf", "jpg", pdf_to_jpg)
    reg.register("pdf", "jpeg", pdf_to_jpg)

    from .converters.pdf_text import pdf_to_docx, pdf_to_txt

    reg.register("pdf", "txt", pdf_to_txt)
    reg.register("pdf", "docx", pdf_to_docx)

    from .converters.csv_xlsx import csv_to_xlsx, xlsx_to_csv
    from .converters.html_pdf import convert_html_to_pdf
    from .converters.md_html import md_to_html
    from .converters.txt_pdf import txt_to_pdf

    reg.register("md", "html", md_to_html)
    reg.register("html", "pdf", convert_html_to_pdf)
    reg.register("csv", "xlsx", csv_to_xlsx)
    reg.register("xlsx", "csv", xlsx_to_csv)
    reg.register("txt", "pdf", txt_to_pdf)

    if importlib.util.find_spec("win32com") is not None:
        from .converters.docx_pdf_win import docx_to_pdf_win

        reg.register("docx", "pdf", docx_to_pdf_win)

    return reg
