"""
modules/family/workspace.py — VECTRIX™ Family Designer
═══════════════════════════════════════════════════════════════════════════
Port of frontend/src/components/pages/FamilyPage.tsx.

D × L × N matrix generator with five view modes (All Designs, Meets Target,
Capacity Matrix, Energy Matrix, Best per D), CSV export, and
Apply-to-Designer.

Own package rather than modules/process/: this module posts to /api/v1/family
via api_client.fetch_family(), not to /process/<module>, and it builds a
sortable table rather than the input-rail + result-column shape, so it
subclasses ModuleWorkspace directly instead of ModuleShell.

Cross-module state — the part that does not translate directly
──────────────────────────────────────────────────────────────
FamilyPage.tsx and CalcPage.tsx share a global useCalcStore(). Family reads
mat/ang/surge/cap out of it on mount (a useEffect that resyncs whenever
those change), and applyDesign() writes D/N/P/L back into it.

There is no shared store here, and a module may not import another module.
Both directions go through the shell instead:

    reading   self.peer_payload("calc")  → shell → ConveyorWorkspace
                                            .export_payload()
    writing   self.apply_requested.emit("calc", {...}) → shell →
                                ConveyorWorkspace.receive_payload()

One behavioural difference worth knowing: the .tsx resyncs continuously
through useEffect, so editing material on CalcPage updates Family while it
sits in the background. Here the sync happens in on_activate(), i.e. each
time the user opens the page. Continuous sync would mean the shell pushing
change notifications between modules, which is a store by another name.
Re-syncing on open covers the actual workflow — set up the conveyor, then
go look at the family — without that machinery.

Ds are held and sent in millimetres; the backend divides by 1000.
"""

from __future__ import annotations

import csv
from typing import Optional, Sequence

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFileDialog,
)
from PySide6.QtCore import Qt, QObject, QThread, Signal
from PySide6.QtGui import QColor

from core.theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER, TEAL, PURPLE, PROCESS_ACCENT,
)
from core.api_client import fetch_family, fetch_materials
from modules.base import ModuleWorkspace, ModuleMeta, TabSpec
from modules.process.common import Field, Divider, RunBtn, ErrorBanner, fmt


# Diameter / length option sets — DA and LA in the .tsx
_DA = [100, 150, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800]
_LA = [3, 5, 8, 10, 12, 15, 18, 20, 25, 30, 35, 40, 45, 50]

_DEFAULT_DS = [150, 200, 250, 300, 400, 500]
_DEFAULT_LS = [5, 10, 15, 20, 25, 30]

_COLUMNS = [
    ("D(mm)",      "Dmm",      0, False),
    ("L(m)",       "L",        0, False),
    ("N(RPM)",     "N",        0, False),
    ("Cap(t/h)",   "cap",      1, True),
    ("Feasible",   "cap_ok",   0, False),
    ("Power(kW)",  "pwr",      2, True),
    ("Motor(kW)",  "motor",    0, True),
    ("Torque(Nm)", "tor",      0, True),
    ("Shaft(mm)",  "shaft_mm", 0, True),
    ("Hangers",    "hgr",      0, True),
    ("L10(h)",     "L10",      0, True),
    ("kWh/t",      "kWh",      3, True),
    ("Cost(USD)",  "cost",     0, True),
    ("Score",      "score",    1, True),
]


class _FamilyWorker(QObject):
    """Runs the sweep off the GUI thread — it is a D × L × N grid and can
    take seconds."""

    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, payload: dict):
        super().__init__()
        self._payload = payload

    def run(self) -> None:
        try:
            r = fetch_family(self._payload)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        if not isinstance(r, dict):
            self.failed.emit("Backend returned an unexpected response type.")
        elif r.get("error"):
            self.failed.emit(str(r.get("message") or r.get("detail") or "Error"))
        else:
            self.finished.emit(r)


class _ChipRow(QWidget):
    """Toggleable value chips — the D and L selectors in the .tsx."""

    changed = Signal()

    def __init__(
        self,
        values: Sequence[int],
        selected: Sequence[int],
        suffix: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._selected = set(selected)
        self._buttons: dict[int, QPushButton] = {}

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(3)
        for i, v in enumerate(values):
            btn = QPushButton(f"{v}{suffix}")
            btn.setCheckable(True)
            btn.setChecked(v in self._selected)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(20)
            btn.clicked.connect(lambda _c, val=v: self._toggle(val))
            self._style(btn)
            grid.addWidget(btn, i // 4, i % 4)
            self._buttons[v] = btn

    def _style(self, btn: QPushButton) -> None:
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG}; color: {MUTED};
                border: 1px solid {BORDER}; border-radius: 3px;
                font-size: 9px; font-family: 'JetBrains Mono', monospace;
            }}
            QPushButton:checked {{
                background-color: {PROCESS_ACCENT}; color: #ffffff;
                border: 1px solid {PROCESS_ACCENT}; font-weight: 700;
            }}
        """)

    def _toggle(self, value: int) -> None:
        if value in self._selected:
            self._selected.discard(value)
        else:
            self._selected.add(value)
        self.changed.emit()

    def values(self) -> list[int]:
        return sorted(self._selected)


class FamilyWorkspace(ModuleWorkspace):

    page_id = "family"
    meta = ModuleMeta(
        label="Family Designer",
        icon="📊",
        subtitle="D × L × N matrix generator · capacity and energy maps",
        group="conveyor",
    )

    _TABS = (
        TabSpec("list",     "All Designs"),
        TabSpec("feasible", "Meets Target"),
        TabSpec("matrix",   "Capacity Matrix"),
        TabSpec("energy",   "Energy Matrix"),
        TabSpec("best",     "Best per D"),
    )

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pts: list[dict] = []
        self._view = "list"
        self._thread: Optional[QThread] = None
        self._worker: Optional[_FamilyWorker] = None
        self._materials_loaded = False

        self.setStyleSheet(f"background-color: {BG};")
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        root.addWidget(self._build_rail())
        root.addWidget(self._build_body(), 1)

    # ── input rail ────────────────────────────────────────────────────────

    def _build_rail(self) -> QWidget:
        rail = QWidget()
        rail.setStyleSheet(
            f"background-color: {PANEL}; border: 1px solid {BORDER}; "
            f"border-radius: 8px;"
        )
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)

        icon = QLabel("📊")
        icon.setStyleSheet("font-size: 20px; border: none;")
        title = QLabel("FAMILY DESIGNER")
        title.setStyleSheet(
            f"color: {PROCESS_ACCENT}; font-size: 12px; font-weight: 800; "
            f"letter-spacing: 0.08em; border: none; "
            f"font-family: 'Barlow Condensed', sans-serif;"
        )
        sub = QLabel("D × L × N sweep · capacity, energy, cost, life")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {MUTED}; font-size: 9px; border: none;")
        for w in (icon, title, sub):
            layout.addWidget(w)
        layout.addSpacing(10)

        layout.addWidget(Divider("Duty"))
        self._mat = Field("Material", "Portland cement dry",
                          options=[("Portland cement dry", "Portland cement dry")])
        self._cap = Field("Target capacity", 30.0, 0.1, 5000.0, 1.0, "t/h")
        self._ang = Field("Inclination", 0.0, 0.0, 45.0, 1.0, "°")
        self._surge = Field("Surge factor", 1.2, 1.0, 3.0, 0.05)
        self._L = Field("Reference length", 10.0, 1.0, 100.0, 1.0, "m")
        for f in (self._mat, self._cap, self._ang, self._surge, self._L):
            layout.addWidget(f)

        layout.addWidget(Divider("Diameters (mm)"))
        self._ds = _ChipRow(_DA, _DEFAULT_DS)
        layout.addWidget(self._ds)

        layout.addWidget(Divider("Lengths (m)"))
        self._ls = _ChipRow(_LA, _DEFAULT_LS)
        layout.addWidget(self._ls)

        layout.addSpacing(10)
        self._run_btn = RunBtn()
        self._run_btn.setText("▶  GENERATE FAMILY")
        self._run_btn.clicked.connect(self.generate)
        layout.addWidget(self._run_btn)

        self._export_btn = QPushButton("⬇  EXPORT CSV")
        self._export_btn.setFixedHeight(26)
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self.export_csv)
        self._export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG}; color: {TEXT2};
                border: 1px solid {BORDER}; border-radius: 5px;
                font-size: 10px; font-weight: 700; letter-spacing: 0.06em;
            }}
            QPushButton:hover:enabled {{ border: 1px solid {PRIMARY}; color: {TEXT}; }}
            QPushButton:disabled {{ color: {TEXT3}; }}
        """)
        layout.addWidget(self._export_btn)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(rail)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(260)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        return scroll

    # ── body ──────────────────────────────────────────────────────────────

    def _build_body(self) -> QWidget:
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._error = ErrorBanner()
        layout.addWidget(self._error)

        self._summary = QLabel("No family generated yet.")
        self._summary.setStyleSheet(
            f"color: {MUTED}; font-size: 10px; border: none;"
        )
        layout.addWidget(self._summary)

        self._table = QTableWidget()
        self._table.setAlternatingRowColors(False)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {PANEL}; border: 1px solid {BORDER};
                border-radius: 8px; gridline-color: {BORDER};
                color: {TEXT}; font-size: 10px;
            }}
            QHeaderView::section {{
                background-color: {BG}; color: #93c5fd;
                border: none; border-bottom: 2px solid {BORDER};
                padding: 5px 8px; font-size: 9px; font-weight: 700;
            }}
            QTableWidget::item:selected {{
                background-color: rgba(74,158,255,0.18); color: {TEXT};
            }}
        """)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        layout.addWidget(self._table, 1)

        self._apply_btn = QPushButton("↧  APPLY SELECTED DESIGN TO CALCULATOR")
        self._apply_btn.setFixedHeight(28)
        self._apply_btn.setEnabled(False)
        self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn.clicked.connect(self._apply_selected)
        self._apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PROCESS_ACCENT}; color: #ffffff;
                border: none; border-radius: 5px;
                font-size: 11px; font-weight: 800; letter-spacing: 0.06em;
            }}
            QPushButton:disabled {{ background-color: {BORDER}; color: {TEXT3}; }}
        """)
        layout.addWidget(self._apply_btn)
        return body

    # ── ModuleWorkspace contract ──────────────────────────────────────────

    def tabs(self) -> Sequence[TabSpec]:
        return self._TABS

    def on_tab_changed(self, tab_id: str) -> None:
        self._view = tab_id
        self._render()

    def on_activate(self) -> None:
        """Populate materials once, then resync duty from the conveyor.

        The .tsx keeps these in step continuously via useEffect on the
        shared store; here the resync happens on open. See module docstring.
        """
        if not self._materials_loaded:
            self._load_materials()
            self._materials_loaded = True
        self._sync_from_conveyor()

    def _load_materials(self) -> None:
        mats = fetch_materials()
        if isinstance(mats, dict):
            if mats.get("error"):
                return
            rows = mats.get("materials") or mats.get("items") or []
        elif isinstance(mats, list):
            rows = mats
        else:
            return

        names: list[str] = []
        for m in rows:
            if isinstance(m, dict):
                name = m.get("name")
                if isinstance(name, str) and name:
                    names.append(name)
        if not names:
            return
        self._mat.set_options([(n, n) for n in names])

    def _sync_from_conveyor(self) -> None:
        peer = self.peer_payload("calc")
        if not peer:
            return
        if peer.get("mat"):
            self._mat.set_value(peer["mat"])
        for key, field in (("ang", self._ang), ("surge", self._surge),
                           ("cap", self._cap), ("L", self._L)):
            v = peer.get(key)
            if v is not None:
                field.set_value(v)

    # ── generate ──────────────────────────────────────────────────────────

    def generate(self) -> None:
        if self._thread is not None:
            return
        ds, ls = self._ds.values(), self._ls.values()
        if not ds or not ls:
            self._error.set_message(
                "Select at least one diameter and one length."
            )
            return
        self._error.set_message(None)
        self._run_btn.set_loading(True)
        self._summary.setText("Sweeping D × L × N …")

        payload = {
            "mat":   self._mat.value(),
            "ang":   self._ang.value(),
            "surge": self._surge.value(),
            "cap":   self._cap.value(),
            "L":     self._L.value(),
            "Ds":    ds,          # millimetres — backend divides by 1000
            "Ls":    ls,
        }
        self._thread = QThread()
        self._worker = _FamilyWorker(payload)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)
        self._thread.start()

    def _on_finished(self, r: dict) -> None:
        self._pts = list(r.get("pts") or [])
        self._export_btn.setEnabled(bool(self._pts))
        self._render()

    def _on_failed(self, msg: str) -> None:
        self._error.set_message(msg)
        self._summary.setText("Generation failed.")

    def _cleanup(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self._run_btn.set_loading(False)
        self._run_btn.setText("▶  GENERATE FAMILY")

    # ── views ─────────────────────────────────────────────────────────────

    def _feasible(self) -> list[dict]:
        return [p for p in self._pts if p.get("cap_ok")]

    def _best_per_d(self) -> list[dict]:
        """Lowest kWh/t among feasible designs at each diameter."""
        by_d: dict[float, dict] = {}
        for p in self._feasible():
            d = p.get("Dmm")
            if d is None:
                continue
            d = float(d)
            cur = by_d.get(d)
            if cur is None or (p.get("kWh") or 0) < (cur.get("kWh") or 0):
                by_d[d] = p
        return sorted(by_d.values(), key=lambda p: float(p.get("Dmm") or 0))

    def _render(self) -> None:
        if not self._pts:
            self._summary.setText("No family generated yet.")
            self._table.clear()
            self._table.setRowCount(0)
            self._table.setColumnCount(0)
            return

        if self._view in ("matrix", "energy"):
            self._render_matrix(
                "cap" if self._view == "matrix" else "kWh",
                maximise=self._view == "matrix",
            )
        else:
            rows = {
                "list": self._pts,
                "feasible": self._feasible(),
                "best": self._best_per_d(),
            }[self._view]
            self._render_table(rows)

        feas = len(self._feasible())
        self._summary.setText(
            f"{len(self._pts)} designs · {feas} meet target · "
            f"{len(self._pts) - feas} infeasible"
        )

    def _render_table(self, rows: Sequence[dict]) -> None:
        self._table.clear()
        self._table.setColumnCount(len(_COLUMNS))
        self._table.setHorizontalHeaderLabels([c[0] for c in _COLUMNS])
        self._table.setRowCount(len(rows))

        for r, pt in enumerate(rows):
            for c, (_label, key, dp, right) in enumerate(_COLUMNS):
                v = pt.get(key)
                if key == "cap_ok":
                    text = "Yes" if v else "No"
                else:
                    text = fmt(v, dp)
                item = QTableWidgetItem(text)
                if right:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                if key == "cap_ok":
                    item.setForeground(QColor(SUCCESS if v else DANGER))
                elif key == "cap":
                    item.setForeground(
                        QColor(SUCCESS if pt.get("cap_ok") else DANGER)
                    )
                elif key == "kWh":
                    item.setForeground(QColor(TEAL))
                elif key == "score":
                    item.setForeground(QColor(PURPLE))
                item.setData(Qt.ItemDataRole.UserRole, r)
                self._table.setItem(r, c, item)

        self._rows_shown = list(rows)
        self._table.resizeColumnsToContents()
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def _render_matrix(self, key: str, maximise: bool) -> None:
        """
        Rows = D, cols = L, cell = the best point in that D/L group.

        `maximise` picks the highest value (capacity) versus the lowest
        (kWh/t) — the .tsx sorts descending for capacity, and Best-per-D
        picks minimum energy.
        """
        ds: list[float] = sorted({
            float(v) for p in self._pts
            if (v := p.get("Dmm")) is not None
        })
        ls: list[float] = sorted({
            float(v) for p in self._pts
            if (v := p.get("L")) is not None
        })

        self._table.clear()
        self._table.setColumnCount(len(ls))
        self._table.setRowCount(len(ds))
        self._table.setHorizontalHeaderLabels([f"L={l:g} m" for l in ls])
        self._table.verticalHeader().setVisible(True)
        self._table.setVerticalHeaderLabels([f"D={d:g}" for d in ds])

        dp = 1 if key == "cap" else 3
        for r, d in enumerate(ds):
            for c, l in enumerate(ls):
                group = [p for p in self._pts
                         if p.get("Dmm") == d and p.get("L") == l
                         and p.get(key) is not None]
                if not group:
                    item = QTableWidgetItem("—")
                    item.setForeground(QColor(TEXT3))
                else:
                    # key= must return a comparable, not Optional. group is
                    # already filtered on `is not None`, but the type checker
                    # cannot see that through dict.get, so coerce explicitly.
                    best = (max if maximise else min)(
                        group, key=lambda p: float(p.get(key) or 0.0)
                    )
                    item = QTableWidgetItem(fmt(best.get(key), dp))
                    item.setForeground(
                        QColor(SUCCESS if best.get("cap_ok") else DANGER)
                        if key == "cap" else QColor(TEAL)
                    )
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self._table.setItem(r, c, item)

        self._rows_shown = []
        self._apply_btn.setEnabled(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    # ── selection / apply ─────────────────────────────────────────────────

    def _on_row_selected(self) -> None:
        rows = self._table.selectionModel().selectedRows() \
            if self._table.selectionModel() else []
        self._apply_btn.setEnabled(
            bool(rows) and bool(getattr(self, "_rows_shown", []))
        )

    def _selected_point(self) -> Optional[dict]:
        shown = getattr(self, "_rows_shown", [])
        model = self._table.selectionModel()
        if not shown or model is None:
            return None
        rows = model.selectedRows()
        if not rows:
            return None
        idx = rows[0].row()
        return shown[idx] if 0 <= idx < len(shown) else None

    def _apply_selected(self) -> None:
        pt = self._selected_point()
        if pt is None:
            return
        d_mm = pt.get("Dmm")
        if d_mm is None:
            return
        # Mirrors applyDesign() in the .tsx: P is set equal to D, i.e. a
        # standard full-pitch screw, because the sweep only varies D/L/N.
        self.apply_requested.emit("calc", {
            "D":     d_mm / 1000,
            "P":     d_mm / 1000,
            "N":     pt.get("N"),
            "L":     pt.get("L"),
            "mat":   self._mat.value(),
            "ang":   self._ang.value(),
            "surge": self._surge.value(),
        })

    def export_payload(self) -> dict:
        return {
            "mat":   self._mat.value(),
            "ang":   self._ang.value(),
            "surge": self._surge.value(),
            "cap":   self._cap.value(),
            "L":     self._L.value(),
        }

    # ── CSV ───────────────────────────────────────────────────────────────

    def export_csv(self) -> None:
        if not self._pts:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export family", "screw_family.csv", "CSV files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow([c[0] for c in _COLUMNS])
                for p in self._pts:
                    w.writerow([
                        ("Yes" if p.get("cap_ok") else "No")
                        if key == "cap_ok" else fmt(p.get(key), dp)
                        for _lbl, key, dp, _r in _COLUMNS
                    ])
        except OSError as exc:
            self._error.set_message(f"Could not write CSV: {exc}")
            return
        self._summary.setText(f"Exported {len(self._pts)} designs → {path}")