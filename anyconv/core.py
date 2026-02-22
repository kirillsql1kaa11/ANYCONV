from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Tuple
import shutil

@dataclass(frozen=True)
class ConvertJob:
    src: Path
    dst: Path
    fmt_from: str
    fmt_to: str

ConverterFn = Callable[[ConvertJob], None]

class Registry:
    def __init__(self) -> None:
        self._map: Dict[Tuple[str, str], ConverterFn] = {}

    def register(self, frm: str, to: str, fn: ConverterFn) -> None:
        self._map[(frm.lower(), to.lower())] = fn

    def get(self, frm: str, to: str) -> Optional[ConverterFn]:
        return self._map.get((frm.lower(), to.lower()))

    def supported(self) -> Iterable[Tuple[str, str]]:
        return sorted(self._map.keys())

def ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def safe_copy(src: Path, dst: Path) -> None:
    ensure_parent(dst)
    shutil.copy2(src, dst)
