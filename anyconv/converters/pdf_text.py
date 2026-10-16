from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from ..core import ConvertJob, ensure_parent


def _reader(src: Path) -> PdfReader:
    try:
        reader = PdfReader(str(src))
        if reader.is_encrypted:
            raise RuntimeError("PDF защищён паролем")
        return reader
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError("Не удалось открыть PDF (повреждён или защищён паролем)") from e


def _pages_text(src: Path) -> list[str]:
    reader = _reader(src)
    out: list[str] = []
    for page in reader.pages:
        try:
            out.append(page.extract_text() or "")
        except Exception:
            out.append("")
    return out


def pdf_to_txt(job: ConvertJob) -> str:
    ensure_parent(job.dst)
    pages = _pages_text(job.src)
    text = "\n\n".join(p.strip("\n") for p in pages).strip()
    job.dst.write_text(text + "\n", encoding="utf-8")
    return f"{len(pages)} стр."


def pdf_to_docx(job: ConvertJob) -> str:
    from docx import Document

    ensure_parent(job.dst)
    pages = _pages_text(job.src)
    doc = Document()
    for i, text in enumerate(pages):
        if i:
            doc.add_page_break()
        for line in text.splitlines():
            doc.add_paragraph(line.rstrip())
    doc.save(str(job.dst))
    return f"{len(pages)} стр."
