from __future__ import annotations
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QComboBox, QCheckBox,
    QPlainTextEdit, QMessageBox
)

from .core import ConvertJob, Registry
from .registry import build_registry


APP_TITLE = "AnyConv — Converter"
ACCENT = "#A78BFA"
BG = "#0B0620"
PANEL = "#130B2E"
TEXT = "#EDE9FE"
MUTED = "#B8A8FF"
BORDER = "rgba(167,139,250,0.25)"

def qss() -> str:
    return f"""
    QWidget {{
        background: {BG};
        color: {TEXT};
        font-family: Segoe UI;
        font-size: 12px;
    }}
    QLabel#title {{
        font-size: 18px;
        font-weight: 600;
    }}
    QLabel#subtitle {{
        color: {MUTED};
    }}
    QListWidget, QPlainTextEdit {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 10px;
    }}
    QComboBox {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 8px 10px;
        min-width: 160px;
    }}
    QComboBox QAbstractItemView {{
        background: {PANEL};
        border: 1px solid {BORDER};
        selection-background-color: rgba(167,139,250,0.25);
        padding: 6px;
    }}
    QPushButton {{
        background: rgba(167,139,250,0.16);
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 10px 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background: rgba(167,139,250,0.24);
    }}
    QPushButton:pressed {{
        background: rgba(167,139,250,0.30);
    }}
    QCheckBox {{
        color: {TEXT};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px; height: 18px;
        border-radius: 6px;
        border: 1px solid {BORDER};
        background: {PANEL};
    }}
    QCheckBox::indicator:checked {{
        background: rgba(167,139,250,0.35);
        border: 1px solid rgba(167,139,250,0.55);
    }}
    """

def iter_files(src: Path, recursive: bool) -> list[Path]:
    if src.is_file():
        return [src]
    pat = "**/*" if recursive else "*"
    return [p for p in src.glob(pat) if p.is_file()]

def build_dst(src_file: Path, out_dir: Path | None, to_ext: str) -> Path:
    if out_dir:
        return out_dir / (src_file.stem + "." + to_ext)
    return src_file.with_suffix("." + to_ext)

class ConvertWorker(QThread):
    log = Signal(str)
    finished_ok = Signal(int, int)

    def __init__(self, items: list[Path], to_ext: str, out_dir: Path | None,
                 recursive: bool, overwrite: bool, registry: Registry):
        super().__init__()
        self.items = items
        self.to_ext = to_ext.lower().lstrip(".")
        self.out_dir = out_dir
        self.recursive = recursive
        self.overwrite = overwrite
        self.registry = registry

    def run(self) -> None:
        ok = 0
        fail = 0
        files: list[Path] = []
        for it in self.items:
            files.extend(iter_files(it, self.recursive))

        if self.out_dir:
            self.out_dir.mkdir(parents=True, exist_ok=True)

        total = len(files)
        self.log.emit(f"Found files: {total}")

        for i, f in enumerate(files, start=1):
            frm = f.suffix.lower().lstrip(".")
            fn = self.registry.get(frm, self.to_ext)
            if not fn:
                self.log.emit(f"[{i}/{total}] SKIP  {f}  (no converter {frm}->{self.to_ext})")
                continue

            dst = build_dst(f, self.out_dir, self.to_ext)
            if dst.exists() and not self.overwrite:
                self.log.emit(f"[{i}/{total}] SKIP  {f}  (exists)")
                continue

            try:
                job = ConvertJob(src=f, dst=dst, fmt_from=frm, fmt_to=self.to_ext)
                fn(job)
                ok += 1
                self.log.emit(f"[{i}/{total}] OK    {f.name}  →  {dst.name}")
            except Exception as e:
                fail += 1
                self.log.emit(f"[{i}/{total}] FAIL  {f.name}  ({e!r})")

        self.finished_ok.emit(ok, fail)

class DropList(QListWidget):
    dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        e.acceptProposedAction()

    def dropEvent(self, e):
        paths = []
        for url in e.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.exists():
                paths.append(p)
        if paths:
            self.dropped.emit(paths)
        e.acceptProposedAction()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(860, 560)
        self.setStyleSheet(qss())

        self.registry: Registry = build_registry()
        self.items: list[Path] = []
        self.out_dir: Path | None = None
        self.worker: ConvertWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        header = QVBoxLayout()
        title = QLabel("AnyConv")
        title.setObjectName("title")
        subtitle = QLabel("Drag & drop файлы/папки → выбери формат → Convert")
        subtitle.setObjectName("subtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        controls = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.addItems(sorted({to for _, to in self.registry.supported()}))
        controls.addWidget(QLabel("Convert to:"))
        controls.addWidget(self.combo)

        self.btn_out = QPushButton("Output folder…")
        self.btn_out.clicked.connect(self.pick_out)
        controls.addWidget(self.btn_out)

        self.chk_recursive = QCheckBox("Recursive")
        self.chk_recursive.setChecked(True)
        self.chk_overwrite = QCheckBox("Overwrite")
        controls.addWidget(self.chk_recursive)
        controls.addWidget(self.chk_overwrite)
        controls.addStretch(1)

        self.btn_add = QPushButton("Add files…")
        self.btn_add.clicked.connect(self.add_files)
        self.btn_add_dir = QPushButton("Add folder…")
        self.btn_add_dir.clicked.connect(self.add_folder)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_list)

        controls.addWidget(self.btn_add)
        controls.addWidget(self.btn_add_dir)
        controls.addWidget(self.btn_clear)

        root.addLayout(controls)

        body = QHBoxLayout()
        body.setSpacing(12)

        left = QVBoxLayout()
        self.listw = DropList()
        self.listw.dropped.connect(self.on_dropped)
        left.addWidget(QLabel("Files / folders (drop here):"))
        left.addWidget(self.listw)

        self.btn_convert = QPushButton("Convert")
        self.btn_convert.clicked.connect(self.convert)
        left.addWidget(self.btn_convert)

        right = QVBoxLayout()
        right.addWidget(QLabel("Log:"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        right.addWidget(self.log)

        body.addLayout(left, 1)
        body.addLayout(right, 1)
        root.addLayout(body)

        self.append_log("Ready. Drop files/folders or use Add buttons.")

    def append_log(self, s: str) -> None:
        self.log.appendPlainText(s)

    def on_dropped(self, paths: list[Path]) -> None:
        self.add_items(paths)

    def add_items(self, paths: list[Path]) -> None:
        for p in paths:
            if p in self.items:
                continue
            self.items.append(p)
            self.listw.addItem(QListWidgetItem(str(p)))
        self.append_log(f"Added: {len(paths)} item(s). Total: {len(self.items)}")

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select files")
        if files:
            self.add_items([Path(f) for f in files])

    def add_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select folder")
        if d:
            self.add_items([Path(d)])

    def clear_list(self):
        self.items.clear()
        self.listw.clear()
        self.append_log("Cleared list.")

    def pick_out(self):
        d = QFileDialog.getExistingDirectory(self, "Select output folder")
        if d:
            self.out_dir = Path(d)
            self.append_log(f"Output folder: {self.out_dir}")

    def set_busy(self, busy: bool):
        for w in (self.btn_convert, self.btn_add, self.btn_add_dir, self.btn_clear, self.btn_out, self.combo,
                  self.chk_recursive, self.chk_overwrite):
            w.setEnabled(not busy)
        self.btn_convert.setText("Converting…" if busy else "Convert")

    def convert(self):
        if not self.items:
            QMessageBox.warning(self, "AnyConv", "Добавь хотя бы один файл или папку.")
            return

        to_ext = self.combo.currentText()
        recursive = self.chk_recursive.isChecked()
        overwrite = self.chk_overwrite.isChecked()

        self.append_log("—" * 40)
        self.append_log(f"Convert to: {to_ext} | recursive={recursive} | overwrite={overwrite}")
        self.append_log(f"Output: {self.out_dir if self.out_dir else 'рядом с исходником'}")

        self.set_busy(True)
        self.worker = ConvertWorker(
            items=self.items,
            to_ext=to_ext,
            out_dir=self.out_dir,
            recursive=recursive,
            overwrite=overwrite,
            registry=self.registry,
        )
        self.worker.log.connect(self.append_log)
        self.worker.finished_ok.connect(self.on_done)
        self.worker.start()

    def on_done(self, ok: int, fail: int):
        self.append_log(f"Done. OK={ok} FAIL={fail}")
        self.set_busy(False)

def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
