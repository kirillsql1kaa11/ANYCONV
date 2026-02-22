from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from ..core import ConvertJob, ensure_parent

def txt_to_pdf(job: ConvertJob) -> None:
    ensure_parent(job.dst)
    lines = job.src.read_text(encoding="utf-8", errors="ignore").splitlines()
    c = canvas.Canvas(str(job.dst), pagesize=A4)
    width, height = A4
    x, y = 40, height - 40
    line_h = 14

    for line in lines:
        if y < 40:
            c.showPage()
            y = height - 40
        c.drawString(x, y, line[:240])
        y -= line_h

    c.save()
