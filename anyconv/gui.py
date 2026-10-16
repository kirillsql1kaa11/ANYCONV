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


APP_TITLE = "AnyConv — конвертер файлов"
ACCENT = "#A78BFA"
BG = "#0B0620"
PANEL = "#130B2E"
TEXT = "#EDE9FE"
MUTED = "#8E7FD4"
BORDER = "rgba(167,139,250,0.22)"

def qss() -> str:
    return f"""
    QWidget {{
        background: {BG};
        color: {TEXT};
        font-family: Segoe UI;
        font-size: 12px;
    }}
    QLabel#title {{
        font-size: 20px;
        font-weight: 600;
    }}
    QLabel#subtitle {{
        color: {MUTED};
    }}
    QLabel#caption {{
        color: {MUTED};
        font-size: 11px;
    }}
    QListWidget, QPlainTextEdit {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 8px;
    }}
    QPlainTextEdit {{
        font-family: Consolas;
        font-size: 11px;
        color: {MUTED};
    }}
    QComboBox {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 7px 10px;
        min-width: 130px;
    }}
    QComboBox QAbstractItemView {{
        background: {PANEL};
        border: 1px solid {BORDER};
        selection-background-color: rgba(167,139,250,0.22);
        padding: 6px;
    }}
    QPushButton {{
        background: transparent;
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 8px 14px;
    }}
    QPushButton:hover {{
        background: rgba(167,139,250,0.14);
    }}
    QPushButton:pressed {{
        background: rgba(167,139,250,0.20);
    }}
    QPushButton#primary {{
        background: {ACCENT};
        border: none;
        color: #14092E;
        font-weight: 600;
        padding: 11px 16px;
    }}
    QPushButton#primary:hover {{
        background: #B9A2FF;
    }}
    QPushButton#primary:pressed {{
        background: #9678E8;
    }}
    QPushButton#primary:disabled {{
        background: rgba(167,139,250,0.25);
        color: {MUTED};
    }}
    QCheckBox {{
        color: {TEXT};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border-radius: 5px;
        border: 1px solid {BORDER};
        background: {PANEL};
    }}
    QCheckBox::indicator:checked {{
        background: rgba(167,139,250,0.35);
        border: 1px solid rgba(167,139,250,0.55);
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(167,139,250,0.25);
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
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
        self.log.emit(f"Найдено файлов: {total}")

        for i, f in enumerate(files, start=1):
            frm = f.suffix.lower().lstrip(".")
            fn = self.registry.get(frm, self.to_ext)
            if not fn:
                self.log.emit(f"[{i}/{total}] пропуск — {f.name}: нет конвертера {frm} → {self.to_ext}")
                continue

            dst = build_dst(f, self.out_dir, self.to_ext)
            if dst.exists() and not self.overwrite:
                self.log.emit(f"[{i}/{total}] пропуск — {f.name}: файл уже существует")
                continue

            try:
                job = ConvertJob(src=f, dst=dst, fmt_from=frm, fmt_to=self.to_ext)
                fn(job)
                ok += 1
                self.log.emit(f"[{i}/{total}] готово  — {f.name} → {dst.name}")
            except Exception as e:
                fail += 1
                self.log.emit(f"[{i}/{total}] ошибка  — {f.name}: {e}")

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
        self.setMinimumSize(820, 540)
        self.setStyleSheet(qss())

        self.registry: Registry = build_registry()
        self.items: list[Path] = []
        self.out_dir: Path | None = None
        self.worker: ConvertWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        header = QVBoxLayout()
        header.setSpacing(2)
        title = QLabel("AnyConv")
        title.setObjectName("title")
        subtitle = QLabel("Перетащите файлы или папки, выберите формат — и готово.")
        subtitle.setObjectName("subtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.combo = QComboBox()
        self.combo.addItems(sorted({to for _, to in self.registry.supported()}))
        controls.addWidget(QLabel("В формат:"))
        controls.addWidget(self.combo)

        self.btn_out = QPushButton("Папка вывода…")
        self.btn_out.clicked.connect(self.pick_out)
        controls.addWidget(self.btn_out)

        self.chk_recursive = QCheckBox("Рекурсивно")
        self.chk_recursive.setChecked(True)
        self.chk_recursive.setToolTip("Обрабатывать файлы во вложенных папках")
        self.chk_overwrite = QCheckBox("Перезаписывать")
        self.chk_overwrite.setToolTip("Заменять уже существующие выходные файлы")
        controls.addWidget(self.chk_recursive)
        controls.addWidget(self.chk_overwrite)
        controls.addStretch(1)

        self.btn_add = QPushButton("Добавить файлы…")
        self.btn_add.clicked.connect(self.add_files)
        self.btn_add_dir = QPushButton("Добавить папку…")
        self.btn_add_dir.clicked.connect(self.add_folder)
        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.clicked.connect(self.clear_list)

        controls.addWidget(self.btn_add)
        controls.addWidget(self.btn_add_dir)
        controls.addWidget(self.btn_clear)

        root.addLayout(controls)

        body = QHBoxLayout()
        body.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(8)
        lst_caption = QLabel("Файлы и папки")
        lst_caption.setObjectName("caption")
        self.listw = DropList()
        self.listw.dropped.connect(self.on_dropped)
        left.addWidget(lst_caption)
        left.addWidget(self.listw)

        self.btn_convert = QPushButton("Конвертировать")
        self.btn_convert.setObjectName("primary")
        self.btn_convert.clicked.connect(self.convert)
        left.addWidget(self.btn_convert)

        right = QVBoxLayout()
        right.setSpacing(8)
        log_caption = QLabel("Журнал")
        log_caption.setObjectName("caption")
        right.addWidget(log_caption)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        right.addWidget(self.log)

        body.addLayout(left, 1)
        body.addLayout(right, 1)
        root.addLayout(body)

        self.append_log("Готово. Добавьте файлы или перетащите их в список.")

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
        self.append_log(f"Добавлено: {len(paths)} (всего {len(self.items)})")

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите файлы")
        if files:
            self.add_items([Path(f) for f in files])

    def add_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if d:
            self.add_items([Path(d)])

    def clear_list(self):
        self.items.clear()
        self.listw.clear()
        self.append_log("Список очищен.")

    def pick_out(self):
        d = QFileDialog.getExistingDirectory(self, "Папка вывода")
        if d:
            self.out_dir = Path(d)
            self.append_log(f"Папка вывода: {self.out_dir}")

    def set_busy(self, busy: bool):
        for w in (self.btn_convert, self.btn_add, self.btn_add_dir, self.btn_clear, self.btn_out, self.combo,
                  self.chk_recursive, self.chk_overwrite):
            w.setEnabled(not busy)
        self.btn_convert.setText("Конвертация…" if busy else "Конвертировать")

    def convert(self):
        if not self.items:
            QMessageBox.warning(self, "AnyConv", "Добавьте хотя бы один файл или папку.")
            return

        to_ext = self.combo.currentText()
        recursive = self.chk_recursive.isChecked()
        overwrite = self.chk_overwrite.isChecked()

        self.append_log("—" * 40)
        self.append_log(
            f"В формат: {to_ext} · рекурсивно: {'да' if recursive else 'нет'} · "
            f"перезапись: {'да' if overwrite else 'нет'}"
        )
        self.append_log(f"Вывод: {self.out_dir if self.out_dir else 'рядом с исходными файлами'}")

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
        self.append_log(f"Готово: успешно {ok}, с ошибками {fail}")
        self.set_busy(False)

def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
