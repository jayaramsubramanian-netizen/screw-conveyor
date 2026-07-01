"""
widgets.py — VECTRIX™ shared primitive widgets
═══════════════════════════════════════════════════════════════════════════
Direct port of the bucket-elevator equivalents. Every class here is a
1-for-1 match to its bucket-elevator counterpart so the two applications
look identical when docked side by side.

ColHeader      → identical to bucket elevator ColHeader
Placeholder    → identical — honest labeled gap
NavTabButton   → identical pill geometry, same fixed-height trick
ModulePill     → identical
KpiChip        → identical custom-painted chip
FailWarnBadges → inline factory, same badge style
"""

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QRect, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QPen

from theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER,
    TAB_PILL_HEIGHT, TAB_PILL_RADIUS,
    MODULE_PILL_HEIGHT, MODULE_PILL_RADIUS,
)


# ── ColHeader ────────────────────────────────────────────────────────────
class ColHeader(QFrame):
    """Fixed-height column header with optional sub-label and right-side
    action widget.  Identical to the bucket-elevator version."""

    def __init__(self, label: str, sub: str = None, action: QWidget = None,
                 parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setStyleSheet(
            f"background-color: {PANEL}; border-bottom: 1px solid {BORDER};"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)

        text_box = QHBoxLayout()
        text_box.setSpacing(7)
        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            f"color: {TEXT3}; font-size: 9.5px; font-weight: 700; letter-spacing: 1px;"
        )
        text_box.addWidget(lbl)
        if sub:
            sub_lbl = QLabel(sub)
            sub_lbl.setStyleSheet(f"color: {MUTED}; font-size: 8.5px;")
            text_box.addWidget(sub_lbl)
        layout.addLayout(text_box)
        layout.addStretch()
        if action:
            layout.addWidget(action)


# ── Placeholder ──────────────────────────────────────────────────────────
class Placeholder(QWidget):
    """Honest labeled gap — not a fake implementation."""

    def __init__(self, title: str, note: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG};")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        icon_lbl = QLabel("○")
        icon_lbl.setStyleSheet(f"color: {BORDER}; font-size: 32px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {TEXT3}; font-size: 13px; font-weight: 600;"
        )
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if note:
            note_lbl = QLabel(note)
            note_lbl.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
            note_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        if note:
            layout.addWidget(note_lbl)


# ── NavTabButton ─────────────────────────────────────────────────────────
class NavTabButton(QPushButton):
    """Tab pill button.  Uses setFixedHeight + exact-half border-radius
    for a guaranteed stadium shape — same fix as bucket elevator."""

    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(TAB_PILL_HEIGHT)
        self._apply_style()

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._apply_style()

    def _apply_style(self):
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PRIMARY}; color: white;
                    border-style: none; border-width: 0px;
                    border-radius: {TAB_PILL_RADIUS}px;
                    padding: 0px 16px; font-size: 12.5px; font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; color: {TEXT3};
                    border-style: none; border-width: 0px;
                    border-radius: {TAB_PILL_RADIUS}px;
                    padding: 0px 16px; font-size: 12.5px;
                }}
                QPushButton:hover {{ background-color: {PANEL2}; color: {TEXT2}; }}
            """)


# ── ModulePill ───────────────────────────────────────────────────────────
class ModulePill(QPushButton):
    """Platform-level module switcher pill.  Active = solid PRIMARY fill;
    inactive = transparent with hover.  Disabled = muted, non-clickable."""

    def __init__(self, icon: str, label: str, active: bool = False,
                 enabled: bool = True, parent=None):
        super().__init__(f"{icon}  {label}", parent)
        self.setEnabled(enabled)
        self.setFixedHeight(MODULE_PILL_HEIGHT)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled
            else Qt.CursorShape.ArrowCursor
        )
        if not enabled:
            self.setToolTip(f"{label} — switch to that application window")

        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PRIMARY}; color: white;
                    border-style: none; border-width: 0px;
                    border-radius: {MODULE_PILL_RADIUS}px;
                    padding: 0px 14px; font-size: 12px; font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; color: {TEXT3};
                    border-style: none; border-width: 0px;
                    border-radius: {MODULE_PILL_RADIUS}px;
                    padding: 0px 14px; font-size: 12px;
                }}
                QPushButton:disabled {{ color: {MUTED}; }}
                QPushButton:hover:!disabled {{ color: {TEXT2}; }}
            """)


# ── KpiChip ──────────────────────────────────────────────────────────────
class KpiChip(QWidget):
    """Custom-painted KPI chip — label top-left, unit top-right, large
    value centred.  Identical to bucket elevator KPIChip."""

    _W, _H = 88, 52

    def __init__(self, label: str, unit: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(self._W, self._H)
        self._label = label
        self._unit  = unit
        self._value = "—"
        self._color = TEXT3

    def set_value(self, value: str, color: str = None):
        self._value = value
        if color:
            self._color = color
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self._W, self._H

        # background + border
        p.setPen(QPen(QColor(self._color), 1.2))
        p.setBrush(QColor(PANEL2))
        p.drawRoundedRect(QRectF(0.6, 0.6, W - 1.2, H - 1.2), 8, 8)

        # label (top-left)
        p.setPen(QColor(TEXT3))
        f_small = QFont(); f_small.setPixelSize(9); f_small.setBold(True)
        p.setFont(f_small)
        p.drawText(QRect(7, 5, W // 2, 14), Qt.AlignmentFlag.AlignLeft, self._label)

        # unit (top-right)
        p.drawText(QRect(W // 2, 5, W // 2 - 7, 14), Qt.AlignmentFlag.AlignRight, self._unit)

        # value (centred)
        p.setPen(QColor(self._color))
        f_val = QFont(); f_val.setPixelSize(20); f_val.setBold(True)
        p.setFont(f_val)
        p.drawText(QRect(0, 12, W, H - 8), Qt.AlignmentFlag.AlignCenter, self._value)
        p.end()


# ── FailWarnBadges ────────────────────────────────────────────────────────
def fail_warn_badges(n_fail: int, n_warn: int) -> QWidget:
    """Small FAIL / WARN pill row for a ColHeader action slot."""
    box = QWidget()
    layout = QHBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(5)
    if n_fail > 0:
        lbl = QLabel(f"{n_fail} FAIL")
        lbl.setStyleSheet(
            f"background-color: rgba(224,82,82,.12); color: {DANGER}; "
            f"border: 1px solid rgba(224,82,82,.3); border-radius: 999px; "
            f"padding: 2px 7px; font-size: 8.5px; font-weight: 700;"
        )
        layout.addWidget(lbl)
    if n_warn > 0:
        lbl = QLabel(f"{n_warn} WARN")
        lbl.setStyleSheet(
            f"background-color: rgba(217,142,0,.12); color: {WARNING}; "
            f"border: 1px solid rgba(217,142,0,.3); border-radius: 999px; "
            f"padding: 2px 7px; font-size: 8.5px; font-weight: 700;"
        )
        layout.addWidget(lbl)
    return box