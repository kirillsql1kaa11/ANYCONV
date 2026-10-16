from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core import ConvertJob, ensure_parent

MISSING_MESSAGE = (
    "Chromium для HTML→PDF не установлен. Нажмите «Установить Chromium» в окне AnyConv "
    "или выполните в терминале: playwright install chromium"
)


class ChromiumMissing(RuntimeError):
    pass


def _is_missing(e: Exception) -> bool:
    text = str(e)
    return "Executable doesn't exist" in text or "playwright install" in text


def _render(browser: Any, job: ConvertJob) -> None:
    ensure_parent(job.dst)
    page = browser.new_page()
    try:
        page.goto(job.src.resolve().as_uri(), wait_until="load", timeout=60000)
        page.pdf(path=str(job.dst.resolve()), format="A4", print_background=True)
    finally:
        page.close()


def convert_html_to_pdf(job: ConvertJob) -> None:
    ctx = job.ctx
    if ctx.get("chromium_missing"):
        raise ChromiumMissing(MISSING_MESSAGE)
    browser = ctx.get("browser")
    if browser is None:
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        try:
            browser = pw.chromium.launch()
        except Exception as e:
            pw.stop()
            if _is_missing(e):
                ctx["chromium_missing"] = True
                raise ChromiumMissing(MISSING_MESSAGE) from e
            raise
        ctx["playwright"] = pw
        ctx["browser"] = browser
    try:
        _render(browser, job)
    except Exception as e:
        if _is_missing(e):
            ctx["chromium_missing"] = True
            raise ChromiumMissing(MISSING_MESSAGE) from e
        raise


def close_batch_ctx(ctx: dict) -> None:
    browser = ctx.pop("browser", None)
    pw = ctx.pop("playwright", None)
    if browser is not None:
        try:
            browser.close()
        except Exception:
            pass
    if pw is not None:
        try:
            pw.stop()
        except Exception:
            pass


def chromium_installed() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False
    try:
        with sync_playwright() as p:
            path = p.chromium.executable_path
        return bool(path) and Path(path).exists()
    except Exception:
        return False


def install_command() -> list[str] | None:
    try:
        from playwright._impl._driver import compute_driver_executable

        node, cli = compute_driver_executable()
        return [str(node), str(cli), "install", "chromium"]
    except Exception:
        pass
    import sys

    exe = getattr(sys, "executable", "")
    if exe:
        return [exe, "-m", "playwright", "install", "chromium"]
    return None
