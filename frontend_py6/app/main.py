"""
app/main.py — entry point
═══════════════════════════════════════════════════════════════════════════
Startup only: QApplication, font, window. All behaviour lives in
app/shell.py and the modules.

Renamed from frontend_py6/main.py deliberately. Three files named main.py
previously sat in this repo — the legacy root main.py, backend/main.py, and
this one — so `import main` resolved to whichever came first on sys.path.
That shadowing broke tooling and test harnesses in ways that looked like
missing dependencies (`ModuleNotFoundError: No module named 'pydantic'`
raised from the wrong main.py entirely).

Run from the frontend_py6 directory:   python -m app.main
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from app.shell import ShellWindow

def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    window = ShellWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()