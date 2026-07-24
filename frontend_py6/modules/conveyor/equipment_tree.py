"""
modules/conveyor/equipment_tree.py — col1 equipment / project tree
═══════════════════════════════════════════════════════════════════════════
Replaces the Placeholder that has occupied column 1 of the conveyor
workspace since the restructure.

Scope — and why it is session-scoped
────────────────────────────────────
core/api_client.py has save_project() / load_project(), but both carry an
explicit note that the backend router (api/project_meta.py) is NOT mounted
in backend/main.py — calling them today returns a 404 error dict. So there
is no persistence to build against yet.

Rather than ship a tree that appears to save and silently does not, this
holds equipment for the current session only, and says so in the UI. Each
entry is a complete input payload plus the headline results from when it
was captured, so the real value — keeping several design variants side by
side and switching between them — works now. When the projects route is
mounted, add_project()/load happens here and the item model does not change.

Interaction
───────────
    Capture      snapshot the sidebar's current inputs as a new item
    (select)     load that item's inputs back into the sidebar and recalc
    Duplicate    copy an item so a variant can be edited from it
    Rename       F2 or double-click the tag
    Delete       remove an item

The panel never touches the sidebar directly. It emits load_requested with
a payload and the workspace applies it, the same indirection the Family
Designer uses — so the tree stays testable on its own.
"""

from __future__ import annotations

from typing import Optional, Any

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QAbstractItemView, QMenu, QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QAction

from core.theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    ACCENT, PRIMARY, SUCCESS, DANGER,
)

_ROLE_PAYLOAD = Qt.ItemDataRole.UserRole
_ROLE_SUMMARY = Qt.ItemDataRole.UserRole + 1


def _tag(n: int) -> str:
    return f"SC-{n:03d}"


class EquipmentTree(QWidget):
    """Session equipment list for the conveyor workspace."""

    #: Emitted with a stored input payload when the user selects an item.
    load_requested = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._seq = 0
        self._loading = False        # guards select-during-programmatic-change

        self.setStyleSheet(f"QWidget {{ background-color: {BG}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._tree.customContextMenuRequested.connect(self._menu)
        self._tree.itemSelectionChanged.connect(self._on_select)
        self._tree.itemChanged.connect(self._on_renamed)
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {PANEL}; border: 1px solid {BORDER};
                border-radius: 7px; color: {TEXT}; font-size: 11px;
                outline: none; padding: 4px;
            }}
            QTreeWidget::item {{ padding: 4px 2px; border-radius: 4px; }}
            QTreeWidget::item:selected {{
                background-color: rgba(74,158,255,0.20); color: {TEXT};
            }}
            QTreeWidget::item:hover {{ background-color: {PANEL2}; }}
        """)

        self._root = QTreeWidgetItem(self._tree, ["📁  Project (unsaved)"])
        self._root.setForeground(0, QColor(ACCENT))
        self._root.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self._root.setExpanded(True)
        layout.addWidget(self._tree, 1)

        btns = QHBoxLayout()
        btns.setSpacing(5)
        self._capture = self._button("＋ Capture", SUCCESS)
        self._capture.clicked.connect(self.capture_requested_clicked)
        self._delete = self._button("🗑 Delete", DANGER)
        self._delete.clicked.connect(self._delete_selected)
        self._delete.setEnabled(False)
        btns.addWidget(self._capture, 1)
        btns.addWidget(self._delete, 1)
        layout.addLayout(btns)

        note = QLabel(
            "Session only — project save is not yet available on the backend."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {TEXT3}; font-size: 8.5px; border: none;")
        layout.addWidget(note)

    #: Emitted when Capture is pressed; the workspace supplies the payload.
    capture_requested = Signal()

    def capture_requested_clicked(self) -> None:
        self.capture_requested.emit()

    def _button(self, text: str, colour: str) -> QPushButton:
        b = QPushButton(text)
        b.setFixedHeight(24)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG}; color: {colour};
                border: 1px solid {colour}66; border-radius: 4px;
                font-size: 10px; font-weight: 700;
            }}
            QPushButton:hover:enabled {{ background-color: {colour}22; }}
            QPushButton:disabled {{ color: {TEXT3}; border: 1px solid {BORDER}; }}
        """)
        return b

    # ── items ─────────────────────────────────────────────────────────────

    def add_item(self, payload: dict, results: Optional[dict] = None) -> None:
        """Store a snapshot. payload is copied — later sidebar edits must
        not mutate an item already captured."""
        self._seq += 1
        item = QTreeWidgetItem(self._root, [_tag(self._seq)])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        item.setData(0, _ROLE_PAYLOAD, dict(payload))
        self._apply_summary(item, payload, results)
        self._root.setExpanded(True)
        self._loading = True
        self._tree.setCurrentItem(item)
        self._loading = False
        self._delete.setEnabled(True)

    def _apply_summary(self, item: QTreeWidgetItem, payload: dict,
                       results: Optional[dict]) -> None:
        D = payload.get("D")
        L = payload.get("L")
        N = payload.get("N")
        bits = []
        if D is not None:
            bits.append(f"⌀{float(D) * 1000:.0f}")
        if L is not None:
            bits.append(f"{float(L):g} m")
        if N is not None:
            bits.append(f"{float(N):g} rpm")
        cap = ((results or {}).get("cap") or {}).get("Qt")
        if cap is not None:
            bits.append(f"{float(cap):.1f} t/h")
        summary = " · ".join(bits)
        item.setData(0, _ROLE_SUMMARY, summary)
        item.setToolTip(0, summary or "No results captured")
        ok = ((results or {}).get("cap") or {}).get("ok")
        if ok is not None:
            item.setForeground(0, QColor(SUCCESS if ok else DANGER))

    # ── interaction ───────────────────────────────────────────────────────

    def _on_select(self) -> None:
        item = self._tree.currentItem()
        self._delete.setEnabled(item is not None and item is not self._root)
        if self._loading or item is None or item is self._root:
            return
        payload = item.data(0, _ROLE_PAYLOAD)
        if isinstance(payload, dict):
            self.load_requested.emit(dict(payload))

    def _on_renamed(self, item: QTreeWidgetItem, _col: int) -> None:
        # Empty tags make the list unreadable; restore something rather than
        # leaving a blank row.
        if item is not self._root and not item.text(0).strip():
            item.setText(0, _tag(self._tree.indexOfTopLevelItem(item) + 1))

    def _menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        if item is None or item is self._root:
            return
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: {PANEL2}; color: {TEXT}; "
            f"border: 1px solid {BORDER}; font-size: 11px; }}"
            f"QMenu::item:selected {{ background-color: {PRIMARY}; }}"
        )
        act_dup = QAction("Duplicate", self)
        act_dup.triggered.connect(lambda: self._duplicate(item))
        act_ren = QAction("Rename", self)
        act_ren.triggered.connect(lambda: self._tree.editItem(item, 0))
        act_del = QAction("Delete", self)
        act_del.triggered.connect(lambda: self._delete_item(item))
        for a in (act_dup, act_ren, act_del):
            menu.addAction(a)
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _duplicate(self, item: QTreeWidgetItem) -> None:
        payload = item.data(0, _ROLE_PAYLOAD)
        if isinstance(payload, dict):
            self.add_item(payload)

    def _delete_selected(self) -> None:
        item = self._tree.currentItem()
        if item is not None and item is not self._root:
            self._delete_item(item)

    def _delete_item(self, item: QTreeWidgetItem) -> None:
        self._root.removeChild(item)
        if self._root.childCount() == 0:
            self._delete.setEnabled(False)

    def count(self) -> int:
        return self._root.childCount()