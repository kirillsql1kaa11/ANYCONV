from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Tuple
import shutil


@dataclass(frozen=True)
class ConvertJob:
    src: Path
    dst: Path
    fmt_from: str
    fmt_to: str
    options: Dict[str, Any] = field(default_factory=dict)
    ctx: Dict[str, Any] = field(default_factory=dict)


ConverterFn = Callable[[ConvertJob], Optional[str]]


class Registry:
    def __init__(self) -> None:
        self._map: Dict[Tuple[str, str], ConverterFn] = {}

    def register(self, frm: str, to: str, fn: ConverterFn) -> None:
        self._map[(frm.lower(), to.lower())] = fn

    def get(self, frm: str, to: str) -> Optional[ConverterFn]:
        return self._map.get((frm.lower(), to.lower()))

    def supported(self) -> Iterable[Tuple[str, str]]:
        return sorted(self._map.keys())

    def targets(self) -> Iterable[str]:
        return sorted({to for _, to in self._map})


def ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def safe_copy(src: Path, dst: Path) -> None:
    ensure_parent(dst)
    shutil.copy2(src, dst)


def human_size(n: int) -> str:
    units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]
    val = float(n)
    i = 0
    while val >= 1024.0 and i < len(units) - 1:
        val /= 1024.0
        i += 1
    if i == 0:
        return f"{int(val)} {units[i]}"
    return f"{val:.1f}".replace(".", ",") + f" {units[i]}"
