"""
modules/manual/workspace.py — VECTRIX™ Engineering Manual
═══════════════════════════════════════════════════════════════════════════
Port of frontend/src/components/pages/ManualPage.tsx, which is an <iframe>
onto frontend/public/manual.html (≈570 KB).

Rendering choice
────────────────
Qt has no iframe. Three options were considered:

  QTextBrowser      rejected. It renders Qt rich text — a subset of HTML 4
                    with no flexbox, CSS grid, or custom properties. The
                    manual uses 794 such constructs, so it would render as
                    a scrambled wall of text rather than a document.
  external browser  rejected as the primary path. It works, but the manual
                    stops being part of the application.
  QWebEngineView    used. Full Chromium rendering, so the manual looks
                    exactly as it does in the web app.

QWebEngineView ships in PySide6-Addons, which `pip install PySide6` pulls in
by default — but a PySide6-Essentials-only environment will not have it.
Rather than crash the whole app on import (the registry imports every module
at startup, so one bad import takes down all eleven), the import is guarded
and the module degrades to an "open in your browser" panel.

Locating the manual
───────────────────
manual.html lives in frontend/public/, outside frontend_py6/, because the
web app serves it from there. Rather than hardcode one relative path — which
breaks the moment the app is launched from a different working directory or
bundled — _find_manual() walks a list of candidates relative to this file
and reports honestly when none exists.
"""

from __future__ import annotations

import os
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from core.theme import BG, PANEL, BORDER, TEXT, TEXT2, TEXT3, MUTED, ACCENT
from modules.base import ModuleWorkspace, ModuleMeta

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    _WEBENGINE = True
except ImportError:                              # PySide6-Essentials only
    QWebEngineView = None                        # type: ignore[assignment]
    _WEBENGINE = False


def _find_manual() -> Optional[str]:
    """
    Absolute path to manual.html, or None.

    Candidates are tried in order from this file's location: the repo layout
    first, then a couple of bundled layouts so a packaged build can ship the
    manual beside the app without this module changing.
    """
    here = os.path.dirname(os.path.abspath(__file__))          # modules/manual
    root = os.path.abspath(os.path.join(here, "..", ".."))     # frontend_py6
    candidates = [
        os.path.join(root, "..", "frontend", "public", "manual.html"),
        os.path.join(root, "resources", "manual.html"),
        os.path.join(root, "manual.html"),
        os.path.join(root, "..", "manual.html"),
    ]
    for c in candidates:
        p = os.path.abspath(c)
        if os.path.isfile(p):
            return p
    return None


class ManualWorkspace(ModuleWorkspace):

    page_id = "help"
    meta = ModuleMeta(
        label="User Manual",
        icon="📘",
        subtitle="VECTRIX™ engineering reference",
        group="reference",
    )

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._path = _find_manual()
        self._loaded = False
        self._view: Optional[QWidget] = None

        self.setStyleSheet(f"background-color: {BG};")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._status = QLabel()
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setWordWrap(True)
        self._status.setStyleSheet(
            f"color: {MUTED}; font-size: 12px; padding: 40px;"
        )
        self._layout.addWidget(self._status)

        if self._path is None:
            self._show_missing()
        elif not _WEBENGINE:
            self._show_fallback()
        else:
            self._status.setText("Loading VECTRIX™ Manual…")

    # ── states ────────────────────────────────────────────────────────────

    def _show_missing(self) -> None:
        self._status.setText(
            "manual.html could not be found.\n\n"
            "Expected at frontend/public/manual.html relative to the "
            "project root, or beside the application as resources/manual.html."
        )

    def _show_fallback(self) -> None:
        """No WebEngine — offer the system browser instead of rendering
        badly. Better an honest external link than a mangled document."""
        self._status.setText(
            "Qt WebEngine is not installed, so the manual cannot be "
            "displayed inside the application.\n\n"
            "Install it with:   pip install PySide6-Addons\n"
            "…or open the manual in your browser:"
        )
        btn = QPushButton("📘  OPEN MANUAL IN BROWSER")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(30)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT}; color: #10233a;
                border: none; border-radius: 5px; padding: 0 18px;
                font-size: 11px; font-weight: 800; letter-spacing: 0.06em;
            }}
        """)
        btn.clicked.connect(self._open_external)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn)
        row.addStretch()
        self._layout.addLayout(row)
        self._layout.addStretch()

    def _open_external(self) -> None:
        if self._path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._path))

    # ── lifecycle ─────────────────────────────────────────────────────────

    def on_activate(self) -> None:
        """
        Build the web view on first open, not at startup.

        QWebEngineView spins up a Chromium render process — several hundred
        milliseconds and a large memory allocation. Eleven workspaces are
        constructed when the shell starts; paying that cost for a manual the
        user may never open would slow every launch. Deferring it here is
        why ModuleWorkspace has on_activate() at all.
        """
        if self._loaded or self._path is None or not _WEBENGINE:
            return
        self._loaded = True

        assert QWebEngineView is not None
        view = QWebEngineView()
        view.setUrl(QUrl.fromLocalFile(self._path))
        view.loadFinished.connect(self._on_load_finished)
        self._view = view
        self._layout.addWidget(view, 1)

    def _on_load_finished(self, ok: bool) -> None:
        if ok:
            self._status.setVisible(False)
        else:
            self._status.setText(
                "The manual failed to render. You can still open it in "
                "your browser."
            )