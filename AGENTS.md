# AGENTS.md

- Стек: Python ≥3.10. GUI — PySide6 (`anyconv/gui.py`), CLI — Typer+Rich (`anyconv/cli.py`). Версия 0.3.0 — держать синхронно в `anyconv/__init__.py` и `pyproject.toml`.
- Общая логика пакетной конвертации — `anyconv/engine.py` (используют и GUI, и CLI): сохранение структуры подпапок, дедупликация имён, спец-цели `zip` / `unpack`. Конвертеры — `anyconv/converters/*`, регистрация в `anyconv/registry.py`.
- Запуск GUI: `python -m anyconv.gui`. CLI: `python -m anyconv.cli list|convert|check-update`. Тестов и CI в репозитории нет.
- Сборка exe: команда из README (PyInstaller; обязательны `--collect-all pypdfium2 pypdfium2_raw`). `AnyConv.spec` в корне не отслеживается (`*.spec` в .gitignore). Иконка — `anyconv/assets/icon.ico`, для frozen-сборки ищется через `_MEIPASS`.
- Нюансы:
  - `docx→pdf` регистрируется только если импортируется `win32com`; в рантайме требует установленный Microsoft Word, иначе кидает понятный RuntimeError.
  - HTML→PDF: один Chromium на всю пачку через `ctx`; без браузера — `ChromiumMissing`, GUI предлагает установку (`install_command()`), CLI просит `playwright install chromium`.
  - `pdf→txt/docx` — только текстовый слой, без OCR.
  - `options={"quality": N}` действует для jpg/jpeg/webp (слайдер в GUI, `--quality` в CLI).
  - Прозрачные изображения при сохранении в JPG/PDF накладываются на белый фон (`flatten_rgb`).
  - TXT→PDF: шрифт с кириллицей ищется в системе (Segoe UI / Arial / DejaVu), длинные строки переносятся.
