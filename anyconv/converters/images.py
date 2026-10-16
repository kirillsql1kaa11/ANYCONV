from __future__ import annotations

from PIL import Image

from ..core import ConvertJob, ensure_parent

DEFAULT_QUALITY = 85


def flatten_rgb(im: Image.Image) -> Image.Image:
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.getchannel("A"))
        return bg
    if im.mode != "RGB":
        return im.convert("RGB")
    return im


def job_quality(job: ConvertJob, default: int = DEFAULT_QUALITY) -> int:
    try:
        q = int(job.options.get("quality", default))
    except (TypeError, ValueError):
        q = default
    return max(10, min(100, q))


def _convert_image(job: ConvertJob) -> None:
    ensure_parent(job.dst)
    ext = job.dst.suffix.lower().lstrip(".")
    with Image.open(job.src) as im:
        im.load()
        if ext in ("jpg", "jpeg"):
            im = flatten_rgb(im)
        save_kwargs = {}
        if ext in ("jpg", "jpeg", "webp"):
            save_kwargs["quality"] = job_quality(job)
            save_kwargs["optimize"] = True
        im.save(job.dst, **save_kwargs)


def png_to_jpg(job: ConvertJob) -> None:
    _convert_image(job)


def jpg_to_png(job: ConvertJob) -> None:
    _convert_image(job)


def webp_to_png(job: ConvertJob) -> None:
    _convert_image(job)


def png_to_webp(job: ConvertJob) -> None:
    _convert_image(job)


def jpg_to_webp(job: ConvertJob) -> None:
    _convert_image(job)
