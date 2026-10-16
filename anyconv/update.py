from __future__ import annotations

import json
import re
import urllib.request

REPO = "kirillsql1kaa11/ANYCONV"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"


def _parse(v: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", v or "")
    return tuple(int(x) for x in nums[:3]) if nums else ()


def _padded(v: tuple[int, ...]) -> tuple[int, int, int]:
    v = (v + (0, 0, 0))[:3]
    return (v[0], v[1], v[2])


def latest_release(timeout: float = 6.0) -> tuple[str, str]:
    req = urllib.request.Request(
        API_URL,
        headers={"User-Agent": "AnyConv", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    tag = (data.get("tag_name") or "").lstrip("v")
    url = data.get("html_url") or ""
    return tag, url


def check_for_update(current: str) -> tuple[str, str] | None:
    try:
        tag, url = latest_release()
    except Exception:
        return None
    if tag and _padded(_parse(tag)) > _padded(_parse(current)):
        return tag, url
    return None
