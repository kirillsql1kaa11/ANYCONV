from markdown import markdown
from ..core import ConvertJob, ensure_parent

HTML_WRAP = """<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>{title}</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:32px auto;padding:0 16px;line-height:1.55}}
pre,code{{font-family:Consolas,monospace}}
pre{{padding:12px;border-radius:10px;overflow:auto;background:#111;color:#eee}}
table{{border-collapse:collapse}}
td,th{{border:1px solid #ccc;padding:6px 10px}}
</style>
</head>
<body>
{body}
</body>
</html>
"""

def md_to_html(job: ConvertJob) -> None:
    ensure_parent(job.dst)
    text = job.src.read_text(encoding="utf-8", errors="ignore")
    body = markdown(text, extensions=["fenced_code", "tables"])
    title = job.src.stem
    job.dst.write_text(HTML_WRAP.format(title=title, body=body), encoding="utf-8")
