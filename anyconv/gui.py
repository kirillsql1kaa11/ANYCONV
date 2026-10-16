from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QIcon, QKeySequence, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from . import __version__, engine, update
from .converters import html_pdf
from .core import human_size
from .registry import build_registry

APP_TITLE = "AnyConv — конвертер файлов"
ACCENT = "#A78BFA"
BG = "#0B0620"
PANEL = "#130B2E"
TEXT = "#EDE9FE"
MUTED = "#8E7FD4"
BORDER = "rgba(167,139,250,0.22)"
OK_COLOR = "#7BE0A3"
ERROR_COLOR = "#F98A8A"
WARN_COLOR = "#F5C36B"

MARKS = {"ok": "✓", "error": "✗", "warn": "!", "skip": "–", "running": "…"}
MARK_COLORS = {"ok": OK_COLOR, "error": ERROR_COLOR, "warn": WARN_COLOR, "skip": MUTED, "running": ACCENT}

TARGET_NAMES = {
    "pdf": "PDF",
    "docx": "DOCX",
    "txt": "TXT",
    "html": "HTML",
    "jpg": "JPG",
    "jpeg": "JPG",
    "png": "PNG",
    "webp": "WEBP",
    "xlsx": "XLSX",
    "csv": "CSV",
    "zip": "ZIP — упаковать",
    "unpack": "Распаковать ZIP",
}
ALL_TARGET_ORDER = ["pdf", "docx", "txt", "html", "jpg", "png", "webp", "xlsx", "csv", "zip", "unpack"]

IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff", "gif"}
QUALITY_TARGETS = {"jpg", "jpeg", "webp"}

FILTERS: list[tuple[str, set[str] | None]] = [
    ("Все файлы", None),
    ("Изображения", IMAGE_EXTS),
    ("Документы", {"pdf", "docx", "txt", "md", "html"}),
    ("Таблицы", {"csv", "xlsx"}),
    ("Архивы", {"zip"}),
]

LOG_LABELS = {"ok": "готово", "skip": "пропуск", "error": "ошибка"}


def qss() -> str:
    return f"""
    QWidget {{
        background: {BG};
        color: {TEXT};
        font-family: Segoe UI;
        font-size: 12px;
    }}
    QLabel#title {{ font-size: 20px; font-weight: 600; }}
    QLabel#subtitle, QLabel#caption {{ color: {MUTED}; }}
    QLabel#caption {{ font-size: 11px; }}
    QLabel#chip {{ color: {WARN_COLOR}; }}
    QLabel#banner {{ color: {OK_COLOR}; font-weight: 600; }}
    QListWidget, QPlainTextEdit {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 8px;
    }}
    QPlainTextEdit {{ font-family: Consolas; font-size: 11px; color: {MUTED}; }}
    QComboBox {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 7px 10px;
        min-width: 110px;
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
    QPushButton:hover {{ background: rgba(167,139,250,0.14); }}
    QPushButton:pressed {{ background: rgba(167,139,250,0.20); }}
    QPushButton:disabled {{ color: {MUTED}; }}
    QPushButton#primary {{
        background: {ACCENT};
        border: none;
        color: #14092E;
        font-weight: 600;
        padding: 11px 16px;
    }}
    QPushButton#primary:hover {{ background: #B9A2FF; }}
    QPushButton#primary:pressed {{ background: #9678E8; }}
    QPushButton#primary:disabled {{ background: rgba(167,139,250,0.25); color: {MUTED}; }}
    QCheckBox {{ color: {TEXT}; spacing: 8px; }}
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
    QScrollBar:vertical {{ background: transparent; width: 10px; }}
    QScrollBar::handle:vertical {{ background: rgba(167,139,250,0.25); border-radius: 5px; min-height: 24px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QProgressBar {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 9px;
        height: 18px;
        text-align: center;
        color: {TEXT};
        font-size: 11px;
    }}
    QProgressBar::chunk {{ background: {ACCENT}; border-radius: 8px; }}
    QSlider::groove:horizontal {{ height: 6px; background: {PANEL}; border: 1px solid {BORDER}; border-radius: 3px; }}
    QSlider::handle:horizontal {{ width: 16px; margin: -6px 0; border-radius: 8px; background: {ACCENT}; }}
    QMenu {{ background: {PANEL}; border: 1px solid {BORDER}; padding: 6px; }}
    QMenu::item {{ padding: 6px 14px; border-radius: 6px; }}
    QMenu::item:selected {{ background: rgba(167,139,250,0.18); }}
    """


def resource_path(rel: str) -> Path:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / rel
    return Path(__file__).resolve().parent.parent / rel


def format_eta(sec: float) -> str:
    sec = max(0, int(sec))
    if sec < 60:
        return f"{sec} с"
    if sec < 3600:
        return f"{sec // 60} мин {sec % 60} с"
    return f"{sec // 3600} ч {(sec % 3600) // 60} мин"


class DropList(QListWidget):
    dropped = Signal(list)
    remove_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e) -> None:
        e.acceptProposedAction()

    def dropEvent(self, e) -> None:
        paths = [Path(u.toLocalFile()) for u in e.mimeData().urls() if u.toLocalFile()]
        paths = [p for p in paths if p.exists()]
        if paths:
            self.dropped.emit(paths)
        e.acceptProposedAction()

    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key_Delete:
            self.remove_requested.emit()
            return
        if e.matches(QKeySequence.StandardKey.SelectAll):
            self.selectAll()
            return
        super().keyPressEvent(e)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.count():
            return
        p = QPainter(self.viewport())
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(167, 139, 250, 110))
        pen.setStyle(Qt.DashLine)
        pen.setWidth(2)
        p.setPen(pen)
        rect = self.viewport().rect().adjusted(12, 12, -12, -12)
        p.drawRoundedRect(rect, 16, 16)
        font = p.font()
        font.setPointSize(13)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(185, 162, 255))
        p.drawText(rect.adjusted(0, -18, 0, 0), Qt.AlignCenter, "Перетащите файлы сюда")
        font.setPointSize(9)
        font.setBold(False)
        p.setFont(font)
        p.setPen(QColor(142, 127, 212))
        p.drawText(rect.adjusted(0, 22, 0, 0), Qt.AlignCenter, "или нажмите «Добавить файлы…»")
        p.end()


class EngineWorker(QThread):
    started_run = Signal(int)
    progress = Signal(int, int, str, str)
    result = Signal(str, str, str, str, int)
    done = Signal(int, int, int, bool, str)

    def __init__(self, items, to_ext, out_dir, recursive, overwrite, options, registry) -> None:
        super().__init__()
        self.items = list(items)
        self.to_ext = to_ext
        self.out_dir = out_dir
        self.recursive = recursive
        self.overwrite = overwrite
        self.options = options
        self.registry = registry
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        try:
            res = engine.run_batch(
                self.items,
                self.to_ext,
                self.out_dir,
                recursive=self.recursive,
                overwrite=self.overwrite,
                options=self.options,
                registry=self.registry,
                on_start=lambda n: self.started_run.emit(n),
                on_progress=lambda d, t, f, o: self.progress.emit(d, t, str(f), str(o)),
                on_result=lambda f, o, s, m, i: self.result.emit(str(f), str(o), s, m, i),
                is_cancelled=lambda: self._cancel.is_set(),
            )
            self.done.emit(res.ok, res.fail, res.skip, res.cancelled, str(res.out_dir or ""))
        except Exception as e:
            self.result.emit("", "", "error", f"Сбой пакета: {e}", 0)
            self.done.emit(0, 0, 0, True, "")


class EstimateWorker(QThread):
    ready = Signal(int, str)

    def __init__(self, seq: int, path: Path, to_ext: str, quality: int) -> None:
        super().__init__()
        self.seq = seq
        self.path = path
        self.to_ext = to_ext
        self.quality = quality

    def run(self) -> None:
        text = ""
        try:
            import io

            from PIL import Image

            from .converters.images import flatten_rgb

            with Image.open(self.path) as im:
                im.load()
                if self.to_ext in ("jpg", "jpeg"):
                    im = flatten_rgb(im)
                fmt = "JPEG" if self.to_ext in ("jpg", "jpeg") else "WEBP"
                buf = io.BytesIO()
                im.save(buf, fmt, quality=self.quality, optimize=True)
                text = human_size(buf.tell())
        except Exception:
            text = ""
        self.ready.emit(self.seq, text)


class ChromiumCheckWorker(QThread):
    checked = Signal(bool)

    def run(self) -> None:
        self.checked.emit(html_pdf.chromium_installed())


class ChromiumInstallWorker(QThread):
    line = Signal(str)
    done = Signal(bool, str)

    def run(self) -> None:
        cmd = html_pdf.install_command()
        if not cmd:
            self.done.emit(False, "Не удалось найти установщик Playwright")
            return
        flags = 0
        if os.name == "nt":
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=flags,
            )
        except Exception as e:
            self.done.emit(False, str(e))
            return
        try:
            for raw in proc.stdout:
                line = raw.strip()
                if line:
                    self.line.emit(line[:300])
            rc = proc.wait()
        except Exception as e:
            self.done.emit(False, str(e))
            return
        self.done.emit(rc == 0, "" if rc == 0 else f"код выхода {rc}")


class UpdateWorker(QThread):
    found = Signal(str, str)

    def run(self) -> None:
        result = update.check_for_update(__version__)
        if result:
            self.found.emit(result[0], result[1])


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(880, 560)
        self.setStyleSheet(qss())
        icon_path = resource_path("anyconv/assets/icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.settings = QSettings("anyconv", "anyconv")
        self.registry = build_registry()
        self.items: list[Path] = []
        self.status: dict[str, str] = {}
        self.details: dict[str, list[str]] = {}
        self.counts: dict[str, dict[str, int]] = {}
        self.out_dir: Path | None = None
        self.last_out: Path | None = None
        self.worker: EngineWorker | None = None
        self.busy = False
        self.sort_mode = 0
        self.run_started = 0.0
        self.est_seq = 0
        self.est_worker: EstimateWorker | None = None
        self.chromium_ok: bool | None = None
        self.update_shown = False
        self.update_tag = ""
        self.update_url = ""
        self._chromium_install: ChromiumInstallWorker | None = None
        self._chromium_check: ChromiumCheckWorker | None = None
        self._update_worker: UpdateWorker | None = None

        self.est_timer = QTimer(self)
        self.est_timer.setSingleShot(True)
        self.est_timer.setInterval(350)
        self.est_timer.timeout.connect(self._estimate_now)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(10)

        header = QVBoxLayout()
        header.setSpacing(2)
        title = QLabel("AnyConv")
        title.setObjectName("title")
        subtitle = QLabel("Перетащите файлы или папки, выберите формат — и готово.")
        subtitle.setObjectName("subtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        self.update_bar = QWidget()
        ub = QHBoxLayout(self.update_bar)
        ub.setContentsMargins(0, 0, 0, 0)
        ub.setSpacing(8)
        self.update_label = QLabel("")
        self.update_label.setObjectName("banner")
        self.btn_update = QPushButton("Скачать обновление")
        self.btn_update.clicked.connect(self.open_update)
        self.btn_update_skip = QPushButton("Скрыть")
        self.btn_update_skip.clicked.connect(self.skip_update)
        ub.addWidget(self.update_label)
        ub.addWidget(self.btn_update)
        ub.addWidget(self.btn_update_skip)
        ub.addStretch(1)
        self.update_bar.hide()
        root.addWidget(self.update_bar)

        self.chromium_bar = QWidget()
        cb = QHBoxLayout(self.chromium_bar)
        cb.setContentsMargins(0, 0, 0, 0)
        cb.setSpacing(8)
        self.chromium_label = QLabel("Для HTML → PDF нужен Chromium (~150 МБ)")
        self.chromium_label.setObjectName("chip")
        self.btn_chromium = QPushButton("Установить Chromium")
        self.btn_chromium.clicked.connect(self.install_chromium)
        cb.addWidget(self.chromium_label)
        cb.addWidget(self.btn_chromium)
        cb.addStretch(1)
        self.chromium_bar.hide()
        root.addWidget(self.chromium_bar)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(QLabel("В формат:"))
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.on_target_changed)
        controls.addWidget(self.combo)
        self.btn_out = QPushButton("Папка вывода…")
        self.btn_out.clicked.connect(self.pick_out)
        controls.addWidget(self.btn_out)
        self.chk_recursive = QCheckBox("Рекурсивно")
        self.chk_recursive.setChecked(True)
        self.chk_recursive.setToolTip("Обрабатывать файлы во вложенных папках")
        self.chk_recursive.toggled.connect(lambda _: self.refresh_targets())
        self.chk_overwrite = QCheckBox("Перезаписывать")
        self.chk_overwrite.setToolTip("Заменять уже существующие выходные файлы")
        controls.addWidget(self.chk_recursive)
        controls.addWidget(self.chk_overwrite)
        controls.addStretch(1)
        self.recent_menu = QMenu(self)
        self.recent_menu.aboutToShow.connect(self.rebuild_recent_menu)
        self.btn_recent = QPushButton("Недавние")
        self.btn_recent.setMenu(self.recent_menu)
        controls.addWidget(self.btn_recent)
        root.addLayout(controls)

        body = QHBoxLayout()
        body.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(8)
        cap_row = QHBoxLayout()
        cap_row.setSpacing(8)
        cap = QLabel("Файлы и папки")
        cap.setObjectName("caption")
        cap_row.addWidget(cap)
        cap_row.addStretch(1)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([name for name, _ in FILTERS])
        self.filter_combo.setToolTip("Фильтр по типу файлов")
        self.filter_combo.currentIndexChanged.connect(lambda _: self.rebuild_list())
        cap_row.addWidget(self.filter_combo)
        self.btn_sort = QPushButton("А-Я")
        self.btn_sort.setToolTip("Сортировка: имя / имя в обратном порядке / по типу")
        self.btn_sort.clicked.connect(self.cycle_sort)
        cap_row.addWidget(self.btn_sort)
        left.addLayout(cap_row)

        self.listw = DropList()
        self.listw.dropped.connect(self.on_dropped)
        self.listw.remove_requested.connect(self.remove_selected)
        self.listw.itemDoubleClicked.connect(self.show_details)
        left.addWidget(self.listw, 1)

        q_row = QHBoxLayout()
        q_row.setSpacing(8)
        self.quality_label = QLabel("Качество: 85")
        self.quality_label.setObjectName("caption")
        q_row.addWidget(self.quality_label)
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(40, 95)
        self.quality_slider.setValue(85)
        self.quality_slider.valueChanged.connect(self.on_quality_changed)
        q_row.addWidget(self.quality_slider, 1)
        self.quality_est = QLabel("")
        self.quality_est.setObjectName("caption")
        q_row.addWidget(self.quality_est)
        left.addLayout(q_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_add = QPushButton("Добавить файлы…")
        self.btn_add.clicked.connect(self.add_files)
        self.btn_add_dir = QPushButton("Добавить папку…")
        self.btn_add_dir.clicked.connect(self.add_folder)
        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.clicked.connect(self.clear_list)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_add_dir)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch(1)
        left.addLayout(btn_row)

        self.btn_convert = QPushButton("Конвертировать")
        self.btn_convert.setObjectName("primary")
        self.btn_convert.clicked.connect(self.convert)
        left.addWidget(self.btn_convert)

        right = QVBoxLayout()
        right.setSpacing(8)
        log_cap = QLabel("Журнал")
        log_cap.setObjectName("caption")
        right.addWidget(log_cap)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        right.addWidget(self.log, 1)

        prog_row = QHBoxLayout()
        prog_row.setSpacing(8)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        prog_row.addWidget(self.progress, 1)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.cancel_run)
        self.btn_cancel.hide()
        prog_row.addWidget(self.btn_cancel)
        right.addLayout(prog_row)

        self.btn_open = QPushButton("Открыть папку вывода")
        self.btn_open.clicked.connect(self.open_out)
        self.btn_open.setEnabled(False)
        right.addWidget(self.btn_open)

        body.addLayout(left, 3)
        body.addLayout(right, 2)
        root.addLayout(body, 1)

        self.append_log(f"AnyConv {__version__}. Добавьте файлы или перетащите их в список.")
        self.refresh_targets()
        self.start_checks()

    def append_log(self, s: str) -> None:
        self.log.appendPlainText(s)

    def start_checks(self) -> None:
        self._chromium_check = ChromiumCheckWorker()
        self._chromium_check.checked.connect(self.on_chromium_checked)
        self._chromium_check.start()
        if self.settings.value("check_updates", True, bool):
            self._update_worker = UpdateWorker()
            self._update_worker.found.connect(self.on_update_found)
            self._update_worker.start()

    def on_chromium_checked(self, ok: bool) -> None:
        self.chromium_ok = ok
        self.chromium_bar.setVisible(not ok)

    def install_chromium(self) -> None:
        if self._chromium_install is not None and self._chromium_install.isRunning():
            return
        self.btn_chromium.setEnabled(False)
        self.append_log("Скачивание Chromium для HTML → PDF…")
        self._chromium_install = ChromiumInstallWorker()
        self._chromium_install.line.connect(self.append_log)
        self._chromium_install.done.connect(self.on_chromium_install_done)
        self._chromium_install.start()

    def on_chromium_install_done(self, ok: bool, message: str) -> None:
        self.btn_chromium.setEnabled(True)
        if ok:
            self.chromium_bar.hide()
            self.append_log("Chromium установлен — HTML → PDF готов к работе.")
        else:
            self.append_log(f"Не удалось установить Chromium: {message or 'неизвестная ошибка'}")
            QMessageBox.warning(
                self,
                "AnyConv",
                "Не удалось установить Chromium автоматически.\n"
                "Попробуйте вручную: playwright install chromium",
            )

    def on_update_found(self, tag: str, url: str) -> None:
        if not tag or self.update_shown:
            return
        if str(self.settings.value("skip_version", "")) == tag:
            return
        self.update_tag = tag
        self.update_url = url
        self.update_label.setText(f"Доступно обновление {tag} — у вас {__version__}")
        self.update_bar.show()
        self.update_shown = True

    def open_update(self) -> None:
        if self.update_url:
            webbrowser.open(self.update_url)

    def skip_update(self) -> None:
        if self.update_tag:
            self.settings.setValue("skip_version", self.update_tag)
        self.update_bar.hide()

    def on_dropped(self, paths: list[Path]) -> None:
        self.add_items(paths)

    def add_items(self, paths: list[Path]) -> None:
        if self.busy:
            return
        existing = {os.path.normcase(str(p)) for p in self.items}
        added = 0
        for p in paths:
            key = os.path.normcase(str(p))
            if key in existing:
                continue
            existing.add(key)
            self.items.append(p)
            added += 1
            if p.is_dir():
                self.remember_recent(p)
        self.rebuild_list()
        self.refresh_targets()
        if added:
            self.append_log(f"Добавлено: {added} (всего {len(self.items)})")

    def remember_recent(self, d: Path) -> None:
        val = self.settings.value("recent", [])
        if isinstance(val, str):
            val = [val] if val else []
        recent = [str(x) for x in val]
        s = str(d)
        recent = [x for x in recent if x != s]
        recent.insert(0, s)
        self.settings.setValue("recent", recent[:6])

    def recent_list(self) -> list[str]:
        val = self.settings.value("recent", [])
        if isinstance(val, str):
            val = [val] if val else []
        return [x for x in val if Path(x).exists()]

    def rebuild_recent_menu(self) -> None:
        self.recent_menu.clear()
        recent = self.recent_list()
        if not recent:
            act = self.recent_menu.addAction("Пусто")
            act.setEnabled(False)
            return
        for s in recent:
            act = self.recent_menu.addAction(s)
            act.triggered.connect(lambda _checked=False, path=s: self.add_items([Path(path)]))

    def add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите файлы")
        if files:
            self.add_items([Path(f) for f in files])

    def add_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if d:
            self.add_items([Path(d)])

    def pick_out(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Папка вывода")
        if d:
            self.out_dir = Path(d)
            self.append_log(f"Папка вывода: {self.out_dir}")

    def clear_list(self) -> None:
        if self.busy:
            return
        self.items.clear()
        self.status.clear()
        self.details.clear()
        self.counts.clear()
        self.rebuild_list()
        self.refresh_targets()
        self.append_log("Список очищен.")

    def remove_selected(self) -> None:
        if self.busy:
            return
        keys = {it.data(Qt.UserRole) for it in self.listw.selectedItems()}
        if not keys:
            return
        self.items = [p for p in self.items if str(p) not in keys]
        for k in keys:
            self.status.pop(k, None)
            self.details.pop(k, None)
            self.counts.pop(k, None)
        self.rebuild_list()
        self.refresh_targets()
        self.append_log(f"Убрано: {len(keys)}")

    def current_filter(self) -> set[str] | None:
        idx = max(0, self.filter_combo.currentIndex())
        return FILTERS[idx][1]

    def visible_item(self, p: Path) -> bool:
        if p.is_dir():
            return True
        group = self.current_filter()
        if group is None:
            return True
        return p.suffix.lower().lstrip(".") in group

    def sort_key(self):
        if self.sort_mode == 2:
            return lambda p: (p.suffix.lower(), p.name.lower())
        return lambda p: p.name.lower()

    def cycle_sort(self) -> None:
        self.sort_mode = (self.sort_mode + 1) % 3
        self.btn_sort.setText(["А-Я", "Я-А", "по типу"][self.sort_mode])
        self.rebuild_list()

    def rebuild_list(self) -> None:
        self.listw.clear()
        order = sorted(self.items, key=self.sort_key(), reverse=(self.sort_mode == 1))
        for p in order:
            key = str(p)
            st = self.status.get(key, "")
            mark = MARKS.get(st)
            item = QListWidgetItem(f"{mark}  {key}" if mark else key)
            item.setData(Qt.UserRole, key)
            color = MARK_COLORS.get(st)
            if color:
                item.setForeground(QBrush(QColor(color)))
            det = self.details.get(key)
            if det:
                item.setToolTip("\n".join(det[-8:]))
            self.listw.addItem(item)
            if not self.visible_item(p):
                item.setHidden(True)
        self.listw.update()

    def item_by_key(self, key: str) -> QListWidgetItem | None:
        for i in range(self.listw.count()):
            it = self.listw.item(i)
            if it.data(Qt.UserRole) == key:
                return it
        return None

    def update_item_visual(self, key: str) -> None:
        it = self.item_by_key(key)
        if it is None:
            return
        st = self.status.get(key, "")
        mark = MARKS.get(st)
        it.setText(f"{mark}  {key}" if mark else key)
        color = MARK_COLORS.get(st)
        if color:
            it.setForeground(QBrush(QColor(color)))

    def show_details(self, item: QListWidgetItem) -> None:
        key = item.data(Qt.UserRole)
        det = self.details.get(key)
        box = QMessageBox(self)
        box.setWindowTitle("AnyConv — результаты")
        box.setText(Path(key).name)
        if det:
            box.setDetailedText("\n".join(det))
        else:
            box.setInformativeText("Пока нет результатов по этому элементу.")
        box.exec()

    def refresh_targets(self) -> None:
        if self.busy:
            return
        current = self.combo.currentData()
        if self.items:
            exts = engine.detect_exts(self.items, self.chk_recursive.isChecked())
            targets = {t for frm, t in self.registry.supported() if frm in exts}
            targets.add("zip")
            if "zip" in exts:
                targets.add("unpack")
        else:
            targets = set(self.registry.targets())
            targets.add("zip")
        targets.discard("jpeg")
        ordered = [t for t in ALL_TARGET_ORDER if t in targets]
        ordered += sorted(t for t in targets if t not in ALL_TARGET_ORDER)
        self.combo.blockSignals(True)
        self.combo.clear()
        for t in ordered:
            self.combo.addItem(TARGET_NAMES.get(t, t.upper()), t)
        self.combo.blockSignals(False)
        idx = self.combo.findData(current)
        self.combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.on_target_changed()

    def on_target_changed(self) -> None:
        target = self.combo.currentData() or ""
        is_quality = target in QUALITY_TARGETS
        self.quality_slider.setEnabled(is_quality and not self.busy)
        self.quality_label.setEnabled(is_quality)
        self.quality_est.setText("")
        if is_quality and not self.busy:
            self.est_timer.start()

    def on_quality_changed(self, value: int) -> None:
        self.quality_label.setText(f"Качество: {value}")
        if not self.busy:
            self.est_timer.start()

    def _estimate_now(self) -> None:
        target = self.combo.currentData() or ""
        if target not in QUALITY_TARGETS:
            self.quality_est.setText("")
            return
        src = None
        for p in self.items:
            if p.is_file() and p.suffix.lower().lstrip(".") in IMAGE_EXTS:
                src = p
                break
        if src is None:
            self.quality_est.setText("")
            return
        self.est_seq += 1
        worker = EstimateWorker(self.est_seq, src, target, self.quality_slider.value())
        worker.ready.connect(self.on_estimate)
        self.est_worker = worker
        worker.start()

    def on_estimate(self, seq: int, text: str) -> None:
        if seq != self.est_seq:
            return
        self.quality_est.setText(f"≈ {text}" if text else "")

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        for w in (
            self.btn_convert,
            self.btn_add,
            self.btn_add_dir,
            self.btn_clear,
            self.btn_out,
            self.combo,
            self.chk_recursive,
            self.chk_overwrite,
            self.filter_combo,
            self.btn_sort,
            self.btn_recent,
            self.quality_slider,
        ):
            w.setEnabled(not busy)
        self.btn_cancel.setVisible(busy)
        self.btn_convert.setText("Конвертация…" if busy else "Конвертировать")
        self.listw.setAcceptDrops(not busy)
        if busy:
            self.progress.setValue(0)
            self.progress.setFormat("0%")
        else:
            self.on_target_changed()

    def convert(self) -> None:
        if self.busy:
            return
        if not self.items:
            QMessageBox.warning(self, "AnyConv", "Добавьте хотя бы один файл или папку.")
            return
        to_ext = self.combo.currentData()
        if not to_ext:
            QMessageBox.warning(self, "AnyConv", "Нет доступных форматов для этих файлов.")
            return

        self.status.clear()
        self.details.clear()
        self.counts.clear()
        self.rebuild_list()

        self.append_log("—" * 40)
        self.append_log(
            f"В формат: {TARGET_NAMES.get(to_ext, to_ext)} · рекурсивно: "
            f"{'да' if self.chk_recursive.isChecked() else 'нет'} · "
            f"перезапись: {'да' if self.chk_overwrite.isChecked() else 'нет'}"
        )
        self.append_log(f"Вывод: {self.out_dir if self.out_dir else 'рядом с исходными файлами'}")

        self.run_started = time.monotonic()
        self.btn_open.setEnabled(False)
        self.set_busy(True)
        self.worker = EngineWorker(
            items=list(self.items),
            to_ext=to_ext,
            out_dir=self.out_dir,
            recursive=self.chk_recursive.isChecked(),
            overwrite=self.chk_overwrite.isChecked(),
            options={"quality": self.quality_slider.value()},
            registry=self.registry,
        )
        self.worker.started_run.connect(self.on_run_started)
        self.worker.progress.connect(self.on_progress)
        self.worker.result.connect(self.on_result)
        self.worker.done.connect(self.on_done)
        self.worker.start()

    def on_run_started(self, total: int) -> None:
        self.progress.setRange(0, max(1, total))
        self.progress.setValue(0)
        self.progress.setFormat(f"0/{total}")
        self.append_log(f"Найдено файлов: {total}")

    def on_progress(self, done: int, total: int, f: str, owner: str) -> None:
        self.progress.setMaximum(max(1, total))
        self.progress.setValue(done)
        pct = int(done * 100 / total) if total else 0
        text = f"{done}/{total} · {pct}%"
        if 0 < done < total and done >= 2:
            elapsed = time.monotonic() - self.run_started
            eta = elapsed / done * (total - done)
            text += f" · осталось ≈ {format_eta(eta)}"
        self.progress.setFormat(text)
        if owner and not self.status.get(owner):
            self.status[owner] = "running"
            self.update_item_visual(owner)

    def on_result(self, f: str, owner: str, status: str, message: str, index: int) -> None:
        if owner:
            c = self.counts.setdefault(owner, {"ok": 0, "skip": 0, "error": 0})
            c[status] = c.get(status, 0) + 1
            if c["error"]:
                st = "error"
            elif c["ok"] and c["skip"]:
                st = "warn"
            elif c["ok"]:
                st = "ok"
            elif c["skip"]:
                st = "skip"
            else:
                st = ""
            self.status[owner] = st
            entries = self.details.setdefault(owner, [])
            entries.append(f"{MARKS.get(status, '')} {message}")
            if len(entries) > 200:
                del entries[:50]
            self.update_item_visual(owner)
        label = LOG_LABELS.get(status, status)
        prefix = f"[{index}/{self.progress.maximum()}] " if index else ""
        self.append_log(f"{prefix}{label} — {message}")

    def on_done(self, ok: int, fail: int, skip: int, cancelled: bool, out_str: str) -> None:
        self.set_busy(False)
        parts = [f"успешно {ok}"]
        if skip:
            parts.append(f"пропущено {skip}")
        if fail:
            parts.append(f"ошибок {fail}")
        prefix = "Прервано: " if cancelled else "Готово: "
        self.append_log(prefix + ", ".join(parts))
        if out_str:
            self.last_out = Path(out_str)
        elif ok and self.items:
            first = self.items[0]
            self.last_out = first if first.is_dir() else first.parent
        else:
            self.last_out = None
        self.btn_open.setEnabled(bool(self.last_out and self.last_out.exists()))
        self.worker = None

    def cancel_run(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)
            self.append_log("Остановка после текущего файла…")

    def open_out(self) -> None:
        if not self.last_out:
            return
        try:
            os.startfile(str(self.last_out))
        except Exception as e:
            QMessageBox.warning(self, "AnyConv", f"Не удалось открыть папку: {e}")


def main() -> None:
    app = QApplication(sys.argv)
    icon_path = resource_path("anyconv/assets/icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
