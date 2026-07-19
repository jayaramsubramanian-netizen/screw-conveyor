"""
components/pages/standards_widgets.py — VECTRIX™ Standards Comparison
═══════════════════════════════════════════════════════════════════════════
Faithful port of StdTabs + StdCompTable from CalcPage.tsx.

Key behavioral fidelity point: in the original, selecting a standard
tab does not just change a table — it swaps `activeR = multiR[activeStd]`
as the data source for EVERY card on the results page. StdTabsWidget
below reproduces that by emitting std_changed(str); ResultsPanel (in
results_panel.py) listens and re-renders all its cards from the newly
selected standard's result, using the multi-standard dict it already
has cached — no new network call on tab switch, exactly like the React
version's pure client-side `activeR` selection.

Effective λ display (matLam × lamMult = λ_eff) is fully data-driven
from the backend response rather than duplicating constants client-side:
    matLam  = multiR["CEMA"]["cap"]["lam_used"]   (material λ — same
              across all 3 standards, since it doesn't depend on lam_factor)
    lamMult = multiR[std]["_lam_factor"]          (injected by
              calculate_multi() in routes.py for every standard)

Not duplicated: TSX's dedicated "Custom λ Multiplier" slider inside
StdTabs. That value is the same thing as the sidebar's existing
"λ factor" field (Advanced section, calc_page.py) — payload.lam_factor
is what the backend uses for the Custom column. Rather than two
editable controls for one value (which could drift out of sync),
StdTabsWidget shows it read-only with a pointer to where to change it.
"""

from __future__ import annotations

from typing import Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

from core.theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER, ACCENT, PURPLE, TEAL,
)


def _f(val: Any, dp: int = 2, fallback: str = "—") -> str:
    try:
        return f"{float(val):.{dp}f}"
    except (TypeError, ValueError):
        return fallback


def _fi(val: Any, fallback: str = "—") -> str:
    try:
        return f"{int(round(float(val))):,}"
    except (TypeError, ValueError):
        return fallback


_STD_DEFS = {
    "CEMA":   {"flag": "🇺🇸", "label": "CEMA 7th Ed.",
               "desc": "CEMA resistance-factor method. λ multiplier = 1.00 (baseline)."},
    "DIN":    {"flag": "🇩🇪", "label": "DIN 15262",
               "desc": "German DIN λ-coefficient method. +1% on material λ."},
    "Custom": {"flag": "⚙️", "label": "Custom",
               "desc": "User-defined λ-multiplier — set via Advanced section (λ factor) in Parameters."},
}
_STD_ORDER = ["CEMA", "DIN", "Custom"]


# ══════════════════════════════════════════════════════════════════════════
# StdTabsWidget
# ══════════════════════════════════════════════════════════════════════════

class StdTabsWidget(QWidget):
    """
    3-way standard selector + λ explanation banner. Sits at the very
    top of the Results tab (above the model number badge / warnings).

    Signal:
        std_changed(str) — "CEMA" | "DIN" | "Custom". Pure client-side
        selection — ResultsPanel already has all 3 results cached and
        just re-renders from the newly selected one.
    """

    std_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._active = "CEMA"
        self._multi: dict = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 8)
        outer.setSpacing(0)

        # Tab row
        tab_row = QHBoxLayout()
        tab_row.setSpacing(0)
        self._tab_btns: dict[str, QPushButton] = {}
        for std in _STD_ORDER:
            d = _STD_DEFS[std]
            btn = QPushButton(f"{d['flag']} {std}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda checked, s=std: self._select(s))
            tab_row.addWidget(btn)
            self._tab_btns[std] = btn
        tab_row.addStretch()
        outer.addLayout(tab_row)
        self._style_tabs()

        # λ explanation banner (static text, always visible)
        explain = QLabel(
            "<b style='color:#4a9eff'>λ (Lambda) — how it works:</b> "
            "the material λ is the CEMA flight resistance factor. "
            "The standards multiplier is a method correction factor applied "
            "on top. Effective λ used in Pm = material λ × multiplier. "
            "Pm = Q_design × L × λ_eff × Ks / 367."
        )
        explain.setStyleSheet(
            f"background-color: rgba(74,158,255,.05); "
            f"border: 1px solid rgba(74,158,255,.15); border-radius: 7px; "
            f"padding: 8px 12px; color: rgba(221,234,246,.75); font-size: 9.5px;"
        )
        explain.setWordWrap(True)
        outer.addWidget(explain)

        # Active standard info box
        self._info_box = QFrame()
        self._info_box.setStyleSheet(
            f"background-color: rgba(232,160,0,.06); "
            f"border: 1px solid rgba(232,160,0,.2); border-radius: 7px;"
        )
        info_lay = QVBoxLayout(self._info_box)
        info_lay.setContentsMargins(10, 8, 10, 8)
        info_lay.setSpacing(4)

        top_row = QHBoxLayout()
        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        self._std_label_lbl = QLabel("")
        self._std_label_lbl.setStyleSheet(
            f"color: {ACCENT}; font-size: 11px; font-weight: 700;"
        )
        text_box.addWidget(self._std_label_lbl)
        self._std_desc_lbl = QLabel("")
        self._std_desc_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 9.5px;")
        self._std_desc_lbl.setWordWrap(True)
        text_box.addWidget(self._std_desc_lbl)
        top_row.addLayout(text_box, 1)

        self._lambda_calc_lbl = QLabel("")
        self._lambda_calc_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 10px; font-family: 'Consolas', monospace;"
        )
        self._lambda_calc_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        top_row.addWidget(self._lambda_calc_lbl)
        info_lay.addLayout(top_row)

        outer.addWidget(self._info_box)

    def _style_tabs(self) -> None:
        for std, btn in self._tab_btns.items():
            active = (std == self._active)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {ACCENT if active else TEXT3};
                    border: none; border-bottom: 2px solid {ACCENT if active else 'transparent'};
                    padding: 0px 16px; font-size: 12px; font-weight: 700;
                }}
            """)

    def _select(self, std: str) -> None:
        self._active = std
        self._style_tabs()
        self._update_info_box()
        self.std_changed.emit(std)

    def set_multi(self, multi: dict) -> None:
        """Called whenever a fresh /calculate-multi response arrives."""
        self._multi = multi or {}
        self._update_info_box()

    def active_standard(self) -> str:
        return self._active

    def _update_info_box(self) -> None:
        d = _STD_DEFS.get(self._active, _STD_DEFS["CEMA"])
        self._std_label_lbl.setText(f"{d['flag']} {d['label']}")
        self._std_desc_lbl.setText(d["desc"])

        active_result = self._multi.get(self._active, {}) or {}
        cema_result = self._multi.get("CEMA", {}) or {}
        mat_lam = (cema_result.get("cap", {}) or {}).get("lam_used", 1.0)
        lam_mult = active_result.get("_lam_factor", 1.0)
        eff_lam = mat_lam * lam_mult

        self._lambda_calc_lbl.setText(
            f"mat.λ {_f(mat_lam, 2)}  ×  SF {_f(lam_mult, 3)}  =  "
            f"<span style='color:#1fb86e;font-weight:700'>λ_eff {_f(eff_lam, 3)}</span>"
        )


# ══════════════════════════════════════════════════════════════════════════
# StdCompTable
# ══════════════════════════════════════════════════════════════════════════

# (label, extractor(r)->str, ok_extractor(r)->Optional[bool])
_ROW_DEFS: list[tuple[str, Any, Any]] = [
    ("Capacity (t/h)",
     lambda r: _f((r.get("cap", {}) or {}).get("Qt"), 2),
     lambda r: (r.get("cap", {}) or {}).get("ok")),
    ("Power (kW)",
     lambda r: _f((r.get("pwr", {}) or {}).get("Pt"), 3),
     lambda r: None),
    ("Motor (kW)",
     lambda r: str((r.get("pwr", {}) or {}).get("motor", "—")),
     lambda r: None),
    ("Running Torque (Nm)",
     lambda r: _fi((r.get("tor", {}) or {}).get("Tr")),
     lambda r: None),
    ("Shaft OD (mm)",
     lambda r: _f((r.get("tor", {}) or {}).get("od")
                  or (r.get("shaft_auto", {}) or {}).get("sel_mm"), 0) + " std",
     lambda r: (r.get("tor", {}) or {}).get("shOk")),
    ("Shear Stress (MPa)",
     lambda r: _f((r.get("tor", {}) or {}).get("tau"), 2),
     lambda r: (r.get("tor", {}) or {}).get("shOk")),
    ("Safety Factor",
     lambda r: _f((r.get("shaft_auto", {}) or {}).get("sf"), 2) + " ×",
     lambda r: ((r.get("shaft_auto", {}) or {}).get("sf") or 0) >= 1.5),
    ("Bearing L10 (h)",
     lambda r: _fi((r.get("brg_r", {}) or {}).get("L10")),
     lambda r: (r.get("brg_r", {}) or {}).get("ok")),
    ("Shaft Defl. (mm)",
     lambda r: _f((r.get("deflection") or 0) * 1000, 3) + " / "
               + _f((r.get("defl_limit") or 0.01) * 1000, 3) + " lim",
     lambda r: r.get("deflection_ok")),
    ("Hangers",
     lambda r: f"{(r.get('hgr', {}) or {}).get('count', 0)} @ "
               f"{_f((r.get('hgr', {}) or {}).get('span'), 1)}m",
     lambda r: None),
    ("kWh/t",
     lambda r: _f((r.get("eff", {}) or {}).get("kWh_t"), 3),
     lambda r: None),
    ("Design Score",
     lambda r: f"{(r.get('eff', {}) or {}).get('score', 0)}/100",
     lambda r: ((r.get("eff", {}) or {}).get("score") or 0) > 70),
    ("Est. Cost (USD)",
     lambda r: "$" + _fi((r.get("cost", {}) or {}).get("total")),
     lambda r: None),
]


class StdCompTable(QFrame):
    """
    Standards Comparison table — all 13 metrics, CEMA/DIN/Custom
    side by side. Independent of which standard is "active" for the
    cards above; shows all three regardless, with the active column
    highlighted in accent colour (matches the React version).
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px;"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 10)
        outer.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(34)
        hdr.setStyleSheet(
            f"background-color: {PANEL2}; "
            f"border-top-left-radius: 8px; border-top-right-radius: 8px; "
            f"border-bottom: 1px solid {BORDER};"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(12, 0, 12, 0)
        hdr_lay.setSpacing(7)
        icon = QLabel("📊")
        icon.setStyleSheet("font-size: 13px;")
        title = QLabel("STANDARDS COMPARISON")
        title.setStyleSheet(
            f"color: {ACCENT}; font-size: 9.5px; font-weight: 700; letter-spacing: 1px;"
        )
        hdr_lay.addWidget(icon)
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()
        outer.addWidget(hdr)

        self._grid = QGridLayout()
        self._grid.setContentsMargins(12, 8, 12, 8)
        self._grid.setSpacing(0)
        self._grid.setColumnStretch(0, 2)
        for c in range(1, 4):
            self._grid.setColumnStretch(c, 1)
        outer.addLayout(self._grid)

        # Column headers
        col_headers = ["Metric", "CEMA", "DIN", "Custom"]
        for c, h in enumerate(col_headers):
            lbl = QLabel(h.upper())
            lbl.setStyleSheet(
                f"color: {TEXT3}; font-size: 9px; font-weight: 700; "
                f"letter-spacing: .5px; padding: 4px 8px;"
            )
            self._grid.addWidget(lbl, 0, c)

        # Value cells — built once, updated in place
        self._cells: list[list[QLabel]] = []
        for row_idx, (label, _extract, _ok) in enumerate(_ROW_DEFS, start=1):
            label_lbl = QLabel(label)
            label_lbl.setStyleSheet(
                f"color: {TEXT3}; font-size: 9.5px; padding: 3px 8px; "
                f"border-bottom: 1px solid rgba(28,48,72,.4);"
            )
            self._grid.addWidget(label_lbl, row_idx, 0)

            row_cells = []
            for c in range(1, 4):
                cell = QLabel("—")
                cell.setStyleSheet(
                    f"color: {TEXT}; font-size: 10.5px; font-weight: 700; "
                    f"font-family: 'Consolas', monospace; padding: 3px 8px; "
                    f"border-bottom: 1px solid rgba(28,48,72,.4);"
                )
                self._grid.addWidget(cell, row_idx, c)
                row_cells.append(cell)
            self._cells.append(row_cells)

    def set_data(self, multi: dict, active_std: str) -> None:
        if not multi:
            self.setVisible(False)
            return
        self.setVisible(True)

        for row_idx, (label, extract, ok_fn) in enumerate(_ROW_DEFS):
            for c, std in enumerate(_STD_ORDER):
                r = multi.get(std)
                cell = self._cells[row_idx][c]
                if not r or r.get("error"):
                    cell.setText("—")
                    continue
                value = extract(r)
                ok = ok_fn(r) if ok_fn else None
                cell.setText(value)

                if ok is True:
                    color = SUCCESS
                elif ok is False:
                    color = DANGER
                elif std == active_std:
                    color = ACCENT
                else:
                    color = TEXT
                cell.setStyleSheet(
                    f"color: {color}; font-size: 10.5px; font-weight: 700; "
                    f"font-family: 'Consolas', monospace; padding: 3px 8px; "
                    f"border-bottom: 1px solid rgba(28,48,72,.4);"
                )