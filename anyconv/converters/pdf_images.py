from __future__ import annotations

from PIL import Image
import pypdfium2 as pdfium

from ..core import ConvertJob, ensure_parent
from .images import flatten_rgb, job_quality

A4_WIDTH_IN = 8.27
RENDER_SCALE = 2


def image_to_pdf(job: ConvertJob) -> None:
    ensure_parent(job.dst)
    with Image.open(job.src) as im:
        im.load()
        im = flatten_rgb(im)
        resolution = max(72.0, min(300.0, im.width / A4_WIDTH_IN))
        im.save(job.dst, "PDF", resolution=resolution)


def _pdf_to_image(job: ConvertJob, fmt: str) -> str | None:
    ensure_parent(job.dst)
    try:
        doc = pdfium.PdfDocument(str(job.src))
    except Exception as e:
        raise RuntimeError("Не удалось открыть PDF (возможно, он защищён паролем или повреждён)") from e
    n = len(doc)
    if n == 0:
        raise RuntimeError("В PDF нет страниц")
    outs = [job.dst]
    if n > 1:
        outs = [
            job.dst.with_name(f"{job.dst.stem}_{i + 1:02d}{job.dst.suffix}")
            for i in range(n)
        ]
    quality = job_quality(job)
    for i, out in enumerate(outs):
        try:
            img = doc[i].render(scale=RENDER_SCALE).to_pil()
        except Exception as e:
            raise RuntimeError("Не удалось отрисовать страницу PDF") from e
        if fmt == "jpg":
            img = flatten_rgb(img)
            img.save(out, quality=quality, optimize=True)
        else:
            img.save(out)
    if n > 1:
        return f"{n} стр."
    return None


def pdf_to_png(job: ConvertJob) -> str | None:
    return _pdf_to_image(job, "png")


def pdf_to_jpg(job: ConvertJob) -> str | None:
    return _pdf_to_image(job, "jpg")
