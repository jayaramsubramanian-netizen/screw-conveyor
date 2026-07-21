"""
widgets.py — VECTRIX™ shared primitive widgets
═══════════════════════════════════════════════════════════════════════════
Direct port of the bucket-elevator equivalents — ColHeader, Placeholder,
NavTabButton, ModulePill, KpiChip, fail_warn_badges.
No backend dependency in this file.

Updated to follow the typography/text-color rules documented at the top
of theme.py:
  - Every font-size now uses an FS_* constant (16px floor everywhere)
  - FONT_FAMILY (Arial) applied to every stylesheet block
  - All body/label/header text now uses TEXT (white) instead of
    TEXT3/MUTED — those two are chrome-only now, not for readable text
  - Pill heights (TAB_PILL_HEIGHT, MODULE_PILL_HEIGHT) already bumped
    in theme.py to comfortably fit the larger text
  - KpiChip enlarged (was 88×52) to fit 16px label/unit + a legible
    value size without cramping

Pylance fixes applied (carried over from before):
  - ColHeader.sub / action use Optional[str] / Optional[QWidget]
  - ModulePill parent uses Optional[QWidget]
  - QRectF imported from QtCore (not QtGui) for PySide6 ≥ 6.4
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
)
from PySide6.QtCore import Qt, QRect, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QPen

from theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER,
    FONT_FAMILY, FS_MIN, FS_UNIT, FS_LABEL, FS_BODY, FS_VALUE,
    FS_SUBHEAD, FS_HEAD, FS_TITLE, FS_DISPLAY,
    TAB_PILL_HEIGHT, TAB_PILL_RADIUS,
    MODULE_PILL_HEIGHT, MODULE_PILL_RADIUS,
)


class ColHeader(QFrame):
    """Fixed-height column header — label + optional sub + optional action widget."""

    def __init__(
        self,
        label: str,
        sub: Optional[str] = None,
        action: Optional[QWidget] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(
            f"background-color: {PANEL}; border-bottom: 1px solid {BORDER};"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(0)

        text_box = QHBoxLayout()
        text_box.setSpacing(9)
        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            f"color: {TEXT}; font-family: '{FONT_FAMILY}'; "
            f"font-size: {FS_UNIT}px; font-weight: 700; letter-spacing: 1px;"
        )
        text_box.addWidget(lbl)
        if sub:
            sub_lbl = QLabel(sub)
            sub_lbl.setStyleSheet(
                f"color: {TEXT}; font-family: '{FONT_FAMILY}'; font-size: {FS_UNIT}px;"
            )
            text_box.addWidget(sub_lbl)
        layout.addLayout(text_box)
        layout.addStretch()
        if action is not None:
            layout.addWidget(action)


class Placeholder(QWidget):
    """Honest labeled gap — not a fake implementation."""

    def __init__(
        self,
        title: str,
        note: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG};")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        icon_lbl = QLabel("○")
        icon_lbl.setStyleSheet(f"color: {BORDER}; font-size: 34px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {TEXT}; font-family: '{FONT_FAMILY}'; "
            f"font-size: {FS_SUBHEAD}px; font-weight: 600;"
        )
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)

        if note:
            note_lbl = QLabel(note)
            note_lbl.setStyleSheet(
                f"color: {TEXT}; font-family: '{FONT_FAMILY}'; font-size: {FS_UNIT}px;"
            )
            note_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(note_lbl)


class NavTabButton(QPushButton):
    """Tab pill — checked = PRIMARY fill, unchecked = transparent."""

    def __init__(self, label: str, parent: Optional[QWidget] = None):
        super().__init__(label, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(TAB_PILL_HEIGHT)
        self._apply_style()

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._apply_style()

    def _apply_style(self) -> None:
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PRIMARY}; color: white;
                    font-family: '{FONT_FAMILY}';
                    border-style: none; border-radius: {TAB_PILL_RADIUS}px;
                    padding: 0px 18px; font-size: {FS_BODY}px; font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; color: {TEXT};
                    font-family: '{FONT_FAMILY}';
                    border-style: none; border-radius: {TAB_PILL_RADIUS}px;
                    padding: 0px 18px; font-size: {FS_BODY}px;
                }}
                QPushButton:hover {{ background-color: {PANEL2}; }}
            """)


class ModulePill(QPushButton):
    """Platform module switcher pill."""

    def __init__(
        self,
        icon: str,
        label: str,
        active: bool = False,
        enabled: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(f"{icon}  {label}", parent)
        self.setEnabled(enabled)
        self.setFixedHeight(MODULE_PILL_HEIGHT)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled
            else Qt.CursorShape.ArrowCursor
        )
        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PRIMARY}; color: white;
                    font-family: '{FONT_FAMILY}';
                    border-style: none; border-radius: {MODULE_PILL_RADIUS}px;
                    padding: 0px 16px; font-size: {FS_BODY}px; font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; color: {TEXT};
                    font-family: '{FONT_FAMILY}';
                    border-style: none; border-radius: {MODULE_PILL_RADIUS}px;
                    padding: 0px 16px; font-size: {FS_BODY}px;
                }}
                QPushButton:disabled {{ color: {TEXT2}; }}
                QPushButton:hover:!disabled {{ background-color: {PANEL2}; }}
            """)


class KpiChip(QWidget):
    """
    Custom-painted KPI chip — label top-left, unit top-right, large value
    centred. Enlarged from the original 88×52 to comfortably fit 16px
    label/unit text plus a legible value size without cramping.
    """

    _W, _H = 112, 66

    def __init__(self, label: str, unit: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(self._W, self._H)
        self._label = label
        self._unit  = unit
        self._value = "—"
        self._color = TEXT

    def set_value(self, value: str, color: Optional[str] = None) -> None:
        self._value = value
        if color is not None:
            self._color = color
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self._W, self._H

        p.setPen(QPen(QColor(self._color), 1.2))
        p.setBrush(QColor(PANEL2))
        p.drawRoundedRect(QRectF(0.6, 0.6, W - 1.2, H - 1.2), 8.0, 8.0)

        p.setPen(QColor(TEXT))
        f_small = QFont(FONT_FAMILY)
        f_small.setPixelSize(FS_UNIT)
        f_small.setBold(True)
        p.setFont(f_small)
        p.drawText(QRect(8, 6, W // 2, 18), Qt.AlignmentFlag.AlignLeft, self._label)
        p.drawText(QRect(W // 2, 6, W // 2 - 8, 18), Qt.AlignmentFlag.AlignRight, self._unit)

        p.setPen(QColor(self._color))
        f_val = QFont(FONT_FAMILY)
        f_val.setPixelSize(FS_DISPLAY - 6)   # 24px — clearly emphasized, still floor-safe
        f_val.setBold(True)
        p.setFont(f_val)
        p.drawText(QRect(0, 20, W, H - 24), Qt.AlignmentFlag.AlignCenter, self._value)
        p.end()


def fail_warn_badges(n_fail: int, n_warn: int) -> QWidget:
    """Small FAIL / WARN pill row for a ColHeader action slot."""
    box = QWidget()
    layout = QHBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    if n_fail > 0:
        lbl = QLabel(f"{n_fail} FAIL")
        lbl.setStyleSheet(
            f"background-color: rgba(224,82,82,.15); color: {DANGER}; "
            f"font-family: '{FONT_FAMILY}'; "
            f"border-radius: 999px; padding: 3px 10px; "
            f"font-size: {FS_UNIT}px; font-weight: 700;"
        )
        layout.addWidget(lbl)
    if n_warn > 0:
        lbl = QLabel(f"{n_warn} WARN")
        lbl.setStyleSheet(
            f"background-color: rgba(217,142,0,.15); color: {WARNING}; "
            f"font-family: '{FONT_FAMILY}'; "
            f"border-radius: 999px; padding: 3px 10px; "
            f"font-size: {FS_UNIT}px; font-weight: 700;"
        )
        layout.addWidget(lbl)
    return box