from __future__ import annotations

from ..core import ConvertJob, ensure_parent


def docx_to_pdf_win(job: ConvertJob) -> None:
    ensure_parent(job.dst)
    try:
        import pythoncom
        import win32com.client
    except ImportError as e:
        raise RuntimeError(
            "Для DOCX→PDF нужен пакет pywin32 (pip install pywin32) и установленный Microsoft Word."
        ) from e

    pythoncom.CoInitialize()
    word = None
    try:
        try:
            word = win32com.client.Dispatch("Word.Application")
        except Exception as e:
            raise RuntimeError(
                "Не удалось запустить Microsoft Word — DOCX→PDF работает только на машинах с установленным Word."
            ) from e
        word.Visible = False
        doc = word.Documents.Open(str(job.src.resolve()))
        try:
            doc.SaveAs(str(job.dst.resolve()), FileFormat=17)
        finally:
            doc.Close(False)
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()
