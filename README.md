# AnyConv (MVP)
GUI + CLI конвертер файлов (Windows 10/11).

## 📦 Скачать

➡ **[Скачать AnyConv для Windows](https://github.com/kirillsql1kaa11/anyconv/releases/latest)**

> Просто распакуйте архив и запустите `AnyConv.exe`

## Быстрый старт
```powershell
py -m venv .venv
.\.venv\Scripts\activate
pip install -U pip
pip install typer rich pillow markdown pandas openpyxl reportlab playwright pyside6
python -m playwright install chromium
# (опционально для DOCX->PDF через Word)
pip install pywin32

python -m anyconv.gui
```

## Сборка exe

```powershell
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --noupx ^
  --name AnyConv --collect-submodules anyconv --collect-all playwright ^
  --hidden-import win32com.client run_gui.py
```

Готовый файл появится в `dist\AnyConv.exe`.

> Для конвертации HTML → PDF на целевой машине нужен Chromium: `python -m playwright install chromium`.

## CLI
```powershell
python -m anyconv.cli list
python -m anyconv.cli convert "C:\files" pdf --out "C:\files\out" --recursive
```
