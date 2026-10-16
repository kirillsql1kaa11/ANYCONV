import asyncio
from playwright.async_api import async_playwright
from ..core import ConvertJob, ensure_parent

async def _html_to_pdf_async(src_path: str, dst_path: str) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file:///{src_path}", wait_until="networkidle")
        await page.pdf(path=dst_path, format="A4", print_background=True)
        await browser.close()

def html_to_pdf(job: ConvertJob) -> None:
    ensure_parent(job.dst)
    try:
        asyncio.run(_html_to_pdf_async(str(job.src.resolve()), str(job.dst.resolve())))
    except Exception as e:
        text = str(e)
        if "Executable doesn't exist" in text or "playwright install" in text:
            raise RuntimeError(
                "Не найден браузер Chromium для конвертации в PDF. "
                "Установите его командой: playwright install chromium"
            ) from e
        raise
