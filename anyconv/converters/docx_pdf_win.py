from ..core import ConvertJob, ensure_parent

def docx_to_pdf_win(job: ConvertJob) -> None:
    """
    Windows-only: requires installed Microsoft Word.
    """
    ensure_parent(job.dst)
    import win32com.client  # type: ignore

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(str(job.src.resolve()))
        try:
            # 17 = wdFormatPDF
            doc.SaveAs(str(job.dst.resolve()), FileFormat=17)
        finally:
            doc.Close(False)
    finally:
        word.Quit()
