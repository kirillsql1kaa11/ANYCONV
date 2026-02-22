from PIL import Image
from ..core import ConvertJob, ensure_parent

def _convert_image(job: ConvertJob, quality: int = 85) -> None:
    ensure_parent(job.dst)
    with Image.open(job.src) as im:
        ext = job.dst.suffix.lower().lstrip(".")
        if ext in ("jpg", "jpeg") and im.mode in ("RGBA", "P"):
            im = im.convert("RGB")

        save_kwargs = {}
        if ext in ("jpg", "jpeg", "webp"):
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True

        im.save(job.dst, **save_kwargs)

def png_to_jpg(job: ConvertJob) -> None:
    _convert_image(job, quality=85)

def jpg_to_png(job: ConvertJob) -> None:
    _convert_image(job)

def webp_to_png(job: ConvertJob) -> None:
    _convert_image(job)

def png_to_webp(job: ConvertJob) -> None:
    _convert_image(job, quality=80)

def jpg_to_webp(job: ConvertJob) -> None:
    _convert_image(job, quality=80)
