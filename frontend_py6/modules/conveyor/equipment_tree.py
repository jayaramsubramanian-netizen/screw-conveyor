"""
modules/conveyor/equipment_tree.py — critical-components design tree
═══════════════════════════════════════════════════════════════════════════
A hierarchical breakdown of the current design's critical components and
their status, modelled on the bucket-elevator equipment tree:

    PROCESS
      ├─ Material          Clinker  rho=1500 kg/m3
      ├─ Capacity          36.5 t/h  req 30 t/h
      ├─ Speed             75 rpm
      └─ Fill              22.5%
    MECHANICAL DESIGN
      ├─ Screw Assembly (Diameter / Pitch / Flight / Shaft stress+defl)
      ├─ Trough (plate / cover / weld from structural)
      ├─ Drive (gearbox torque / motor)
      ├─ Bearings (L10)
      └─ Hangers

Each leaf shows a computed value and is coloured by status: green pass, red
fail, amber advisory, neutral for informational rows. A section header goes
red if any child fails.

This is a DISPLAY of the /calculate result, not a store, and computes no
engineering — capacity/torque/bearing come from the checks fields, geometry
from the payload, trough sizing from the structural block. It replaces the
earlier session-snapshot version; design capture/compare belongs with the
separate save/load feature.
"""

from __future__ import annotations

from typing import Optional, Any

from PySide6.QtWidgets import (
    QWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QHeaderView,
    QAbstractItemView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush

from core.theme import (
    BG, PANEL, BORDER, TEXT, TEXT3, MUTED,
    SUCCESS, WARNING, DANGER, ACCENT, PROCESS_ACCENT,
)

_PASS, _FAIL, _WARN, _INFO = "pass", "fail", "warn", "info"
_STATUS_COLOUR = {_PASS: SUCCESS, _FAIL: DANGER, _WARN: WARNING, _INFO: TEXT}


def _f(v: Any, dp: int = 1) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.{dp}f}"
    except (TypeError, ValueError):
        return str(v)


def _fi(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return f"{int(round(float(v))):,}"
    except (TypeError, ValueError):
        return str(v)


def _status_from_ok(ok: Optional[bool]) -> str:
    return _INFO if ok is None else (_PASS if ok else _FAIL)


class EquipmentTree(QWidget):
    """Component-status tree for the current conveyor design."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(f"QWidget {{ background-color: {BG}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(2)
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setIndentation(14)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {PANEL}; border: 1px solid {BORDER};
                border-radius: 7px; color: {TEXT}; font-size: 16px;
                outline: none; padding: 4px;
            }}
            QTreeWidget::item {{ padding: 2px 0; }}
        """)
        header = self._tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(True)
        self._tree.setColumnWidth(0, 130)
        layout.addWidget(self._tree)
        self._empty()

    def _empty(self) -> None:
        self._tree.clear()
        root = QTreeWidgetItem(self._tree, ["Run a calculation to populate", ""])
        root.setForeground(0, QBrush(QColor(MUTED)))
        root.setFlags(Qt.ItemFlag.ItemIsEnabled)

    def _section(self, title: str, accent: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem(self._tree, [title, ""])
        item.setForeground(0, QBrush(QColor(accent)))
        f = item.font(0); f.setBold(True); item.setFont(0, f)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setExpanded(True)
        return item

    def _group(self, parent: QTreeWidgetItem, title: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent, [title, ""])
        f = item.font(0); f.setBold(True); item.setFont(0, f)
        item.setForeground(0, QBrush(QColor(TEXT)))
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setExpanded(True)
        return item

    def _leaf(self, parent: QTreeWidgetItem, label: str, value: str,
              status: str = _INFO) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent, [label, value])
        item.setForeground(0, QBrush(QColor(TEXT)))
        item.setForeground(1, QBrush(QColor(_STATUS_COLOUR.get(status, TEXT))))
        f = item.font(1); f.setBold(True); item.setFont(1, f)
        item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        if status == _FAIL:
            parent.setForeground(0, QBrush(QColor(DANGER)))
        return item

    def set_data(self, result: dict, payload: Optional[dict] = None) -> None:
        if not result or result.get("error"):
            self._empty()
            return
        payload = payload or {}
        self._tree.clear()

        cap = result.get("cap", {}) or {}
        tor = result.get("tor", {}) or {}
        gbx = result.get("gbx_r", {}) or {}
        brg = result.get("brg_r", {}) or {}
        pwr = result.get("pwr", {}) or {}
        mat = result.get("mat", {}) or {}
        struct = result.get("structural", {}) or {}
        hgr = result.get("hgr", {}) or {}

        # PROCESS
        proc = self._section("PROCESS", PROCESS_ACCENT)
        rho = mat.get("rho")
        self._leaf(proc, "Material",
                   f"{mat.get('name', payload.get('mat', '—'))}  ρ={_fi((rho or 0) * 1000)} kg/m³")
        self._leaf(proc, "Capacity",
                   f"{_f(cap.get('Qt'), 1)} t/h  req {cap.get('req', payload.get('cap', '—'))}",
                   _status_from_ok(cap.get("ok")))
        self._leaf(proc, "Speed", f"{_f(payload.get('N'), 0)} rpm")
        fill = cap.get("fill_actual") or cap.get("fill") or 0
        self._leaf(proc, "Fill fraction", f"{_f(fill * 100, 1)}%",
                   _PASS if 0.15 <= fill <= 0.45 else _WARN)
        self._leaf(proc, "Inclination", f"{_f(payload.get('ang'), 0)}°")

        # MECHANICAL DESIGN
        mech = self._section("MECHANICAL DESIGN", ACCENT)

        screw = self._group(mech, "Screw Assembly")
        D = payload.get("D", 0) or 0
        P = payload.get("P", D) or D
        self._leaf(screw, "Diameter", f"Ø{_fi(D * 1000)} mm")
        self._leaf(screw, "Pitch", f"{_fi(P * 1000)} mm  ({_f(P / D if D else 0, 2)}×D)")
        self._leaf(screw, "Flight thickness", f"{_fi((payload.get('ft', 0) or 0) * 1000)} mm")
        self._leaf(screw, "Shaft stress",
                   f"{_f(tor.get('tau'), 1)} MPa  ≤{payload.get('sallow', 40)}",
                   _status_from_ok(tor.get("shOk")))
        defl = (result.get("deflection") or 0) * 1000
        defl_lim = (result.get("defl_limit") or 0.01) * 1000
        self._leaf(screw, "Shaft deflection",
                   f"{_f(defl, 2)} mm  ≤{_f(defl_lim, 2)}",
                   _status_from_ok(result.get("deflection_ok")))

        trough = self._group(mech, "Trough")
        self._leaf(trough, "Plate thickness", f"{_fi(struct.get('t_plate'))} mm" if struct else "—")
        self._leaf(trough, "Cover thickness", f"{_fi(struct.get('t_cover'))} mm" if struct else "—")
        self._leaf(trough, "Weld size", f"{_fi(struct.get('weld_size'))} mm" if struct else "—")

        drive = self._group(mech, "Drive")
        self._leaf(drive, "Gearbox", f"{payload.get('gbx', '—')}")
        tn = gbx.get("Tn_derated") or gbx.get("Tn")
        self._leaf(drive, "Gearbox torque",
                   f"{_fi(tor.get('Ts'))} ≤ {_fi(tn)} Nm",
                   _status_from_ok(gbx.get("tOk")))
        motor = pwr.get("motor"); motor_rated = pwr.get("motor_rated")
        self._leaf(drive, "Motor", f"{motor} kW  (req {_f(motor_rated, 1)})",
                   _PASS if (motor or 0) >= (motor_rated or 0) else _FAIL)

        bearings = self._group(mech, "Bearings")
        self._leaf(bearings, payload.get("brg", "Bearing"),
                   f"L10 {_fi(brg.get('L10'))} h", _status_from_ok(brg.get("ok")))

        hang = self._group(mech, "Hangers")
        h_count = hgr.get("count") or struct.get("n_supports") or "—"
        self._leaf(hang, "Count", f"{h_count}")
        if struct.get("R_kN") is not None:
            self._leaf(hang, "Reaction", f"{_f(struct.get('R_kN'), 1)} kN")

        for i in range(self._tree.topLevelItemCount()):
            top = self._tree.topLevelItem(i)
            if top is not None:
                top.setExpanded(True)