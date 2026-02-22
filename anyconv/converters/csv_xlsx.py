import pandas as pd
from ..core import ConvertJob, ensure_parent

def csv_to_xlsx(job: ConvertJob) -> None:
    ensure_parent(job.dst)
    df = pd.read_csv(job.src, encoding="utf-8", sep=None, engine="python")
    df.to_excel(job.dst, index=False)

def xlsx_to_csv(job: ConvertJob) -> None:
    ensure_parent(job.dst)
    df = pd.read_excel(job.src)
    df.to_csv(job.dst, index=False, encoding="utf-8")
