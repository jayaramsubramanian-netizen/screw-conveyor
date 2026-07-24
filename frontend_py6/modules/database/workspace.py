"""
modules/database/workspace.py — VECTRIX™ Database browser
═══════════════════════════════════════════════════════════════════════════
Port of frontend/src/components/pages/DatabasePage.tsx.

Six tabs over the reference tables: Materials, Bearings, Gearboxes, Motors,
Drives, Costs.

Canonical source — resolved
───────────────────────────
Two candidates existed: DatabasePage.jsx at the repo root (3,281 "lines")
and frontend/src/components/pages/DatabasePage.tsx (898 lines). The root
file is NOT React source — it parses as JSON and is a stray
package-lock.json saved under the wrong extension (a different lockfile
from the root package-lock.json, i.e. a duplicate-download artifact). Its
line count was npm dependency entries. The .tsx is the only real source and
is what this module is ported from. The root file should be deleted.

Scope of this pass
──────────────────
Read, search, filter, and the Applications coverage matrix — the whole
browsing surface. CRUD (add / edit / delete) is deliberately NOT in this
pass: core/api_client.py exposes only fetchers (fetch_materials,
fetch_bearings, …) with no POST/PUT/DELETE helpers, so writes need client
plumbing plus a distinct modal form per table schema. Building half of that
would leave edit buttons that silently fail, which is worse than not
showing them.

The Applications matrix (APP_DEFS below) is the feature the .tsx docstring
calls out as the point of the page: each material carries an `app` list,
and each badge is green when that module's required fields are all present,
amber when only recommended fields are missing, red when a required field
is absent. It answers "which modules will actually work with this
material", which is otherwise invisible until a calculation fails.

Derived-column note
───────────────────
The .tsx computes λ, Ks and Wc client-side for the Materials table, with
the comment "mirrors Python engine". That is the same duplicated-physics
pattern flagged for calcStructural(), on a smaller scale: engine.py already
has calc_lambda / calc_ks / calc_wc, but there is no bulk endpoint that
returns them per material, and /calculate returns them for one material at
a time. Rather than silently reimplement the formulas here, those three
columns are omitted and the stored inputs (lambda_ref, particle_class,
flowability, cohesion, abr) are shown instead — every value in this table
is read from the database, none is derived. Restoring the columns properly
means having /materials return them; noted rather than worked around.
"""

from __future__ import annotations

from typing import Optional, Sequence, Callable, Any

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QLineEdit, QComboBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QStackedWidget,
)
from PySide6.QtCore import Qt, QObject, QThread, Signal
from PySide6.QtGui import QColor

from core.theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER, TEAL, PURPLE, PROCESS_ACCENT,
)
from core.api_client import (
    fetch_materials, fetch_bearings, fetch_gearboxes,
    fetch_motors, fetch_drives, fetch_costs,
)
from modules.base import ModuleWorkspace, ModuleMeta, TabSpec


# ── Application coverage definitions — ported from APP_DEFS in the .tsx ────

APP_DEFS: dict[str, dict] = {
    "conv":    {"label": "Conveyor",   "icon": "🔩", "col": PRIMARY,
                "required": ["rho", "fill_max", "lambda_ref"],
                "recommended": ["flowability", "abr", "cls", "moist"]},
    "dry":     {"label": "Dryer",      "icon": "🌡️", "col": PROCESS_ACCENT,
                "required": ["rho", "moist", "temp_max"],
                "recommended": ["fill_max", "flowability"]},
    "cool":    {"label": "Cooler",     "icon": "❄️", "col": TEAL,
                "required": ["rho", "temp_max"],
                "recommended": ["fill_max"]},
    "mix":     {"label": "Mixer",      "icon": "🌀", "col": PURPLE,
                "required": ["rho", "fill_max"],
                "recommended": ["flowability", "particle_class"]},
    "sep":     {"label": "Separator",  "icon": "🔀", "col": SUCCESS,
                "required": ["rho", "particle_class"],
                "recommended": ["flowability"]},
    "react":   {"label": "Reactor",    "icon": "⚗️", "col": PURPLE,
                "required": ["rho", "temp_max"],
                "recommended": ["fill_max", "flowability"]},
    "compact": {"label": "Compactor",  "icon": "🗜️", "col": DANGER,
                "required": ["rho", "bridging_risk"],
                "recommended": ["fill_max", "flowability"]},
    "feed":    {"label": "Feeder",     "icon": "⚖️", "col": WARNING,
                "required": ["rho", "fill_max", "flowability"],
                "recommended": ["bridging_risk", "cohesion"]},
}

FLAG_META = {
    "L": ("Lumpy", WARNING), "M": ("Moist", PRIMARY),
    "O": ("Oily", WARNING),  "U": ("Dusty", PURPLE),
    "X": ("Explosive", DANGER),
}

_FLOWABILITY = {1: "Very Free", 2: "Free", 3: "Average", 4: "Sluggish"}


def _coverage(mat: dict) -> tuple[str, str]:
    """
    (summary text, colour) for a material's Applications cell.

    Port of AppCoverage. The .tsx renders one badge per app; a Qt table cell
    is a single string, so this condenses to "n ok · n partial · n missing"
    with the worst status driving the colour — the same information, read at
    a glance across 531 rows rather than per-row.
    """
    apps = mat.get("app") or []
    if not apps:
        return "—", TEXT3

    ok = partial = missing = 0
    for app_id in apps:
        d = APP_DEFS.get(app_id)
        if not d:
            continue
        miss_req = [f for f in d["required"]
                    if mat.get(f) is None or mat.get(f) == ""]
        miss_rec = [f for f in d["recommended"]
                    if mat.get(f) is None or mat.get(f) == ""]
        if miss_req:
            missing += 1
        elif miss_rec:
            partial += 1
        else:
            ok += 1

    parts = []
    if ok:
        parts.append(f"{ok} ok")
    if partial:
        parts.append(f"{partial} partial")
    if missing:
        parts.append(f"{missing} missing")
    colour = DANGER if missing else WARNING if partial else SUCCESS
    return " · ".join(parts) or "—", colour


def _coverage_detail(mat: dict) -> str:
    """Per-app tooltip listing exactly which fields are absent."""
    apps = mat.get("app") or []
    lines = []
    for app_id in apps:
        d = APP_DEFS.get(app_id)
        if not d:
            continue
        miss_req = [f for f in d["required"]
                    if mat.get(f) is None or mat.get(f) == ""]
        miss_rec = [f for f in d["recommended"]
                    if mat.get(f) is None or mat.get(f) == ""]
        if miss_req:
            lines.append(f"{d['icon']} {d['label']}: REQUIRED missing — "
                         f"{', '.join(miss_req)}")
        elif miss_rec:
            lines.append(f"{d['icon']} {d['label']}: recommended missing — "
                         f"{', '.join(miss_rec)}")
        else:
            lines.append(f"{d['icon']} {d['label']}: all required present")
    return "\n".join(lines) or "No applications assigned"


def _flags_text(flags: Optional[str]) -> str:
    if not flags:
        return "—"
    return " ".join(
        f"{f}={FLAG_META[f][0]}" if f in FLAG_META else f for f in flags
    )


def _fmt(v: Any, dp: int = 2) -> str:
    if v is None or v == "":
        return "—"
    try:
        return f"{float(v):.{dp}f}"
    except (TypeError, ValueError):
        return str(v)


# ── Table specifications ──────────────────────────────────────────────────
# (header, key, dp or None for raw, right-aligned)
_Col = tuple[str, str, Optional[int], bool]

TABLES: dict[str, dict] = {
    "materials": {
        "label": "Materials", "fetch": fetch_materials, "key": "MATS",
        "search": ["name", "cema_code", "note"],
        "cols": [
            ("Material Name", "name", None, False),
            ("Category", "category", None, False),
            ("ρ t/m³", "rho", 2, True),
            ("λ ref", "lambda_ref", 2, True),
            ("Fill max", "fill_max", 2, True),
            ("Particle", "particle_class", None, False),
            ("Flow", "flowability", None, False),
            ("Abrasiveness", "abr", None, False),
            ("AoR °", "aor", 1, True),
            ("Cohesion", "cohesion", 1, True),
            ("Cls", "cls", None, False),
            ("Moist %", "moist", 1, True),
            ("Temp max", "temp_max", 0, True),
            ("Flags", "flags", None, False),
            ("Applications", "_coverage", None, False),
            ("CEMA", "cema_code", None, False),
        ],
    },
    "bearings": {
        "label": "Bearings", "fetch": fetch_bearings, "key": "BEARINGS",
        "search": ["name", "mfr", "type"],
        "cols": [
            ("Name", "name", None, False), ("Mfr", "mfr", None, False),
            ("Type", "type", None, False), ("Bore", "bore", 0, True),
            ("OD", "od", 0, True), ("B", "B", 0, True),
            ("C kN", "C", 1, True), ("C0 kN", "C0", 1, True),
        ],
    },
    "gearboxes": {
        "label": "Gearboxes", "fetch": fetch_gearboxes, "key": "GBXS",
        "search": ["model", "type"],
        "cols": [
            ("Model", "model", None, False), ("Type", "type", None, False),
            ("Stages", "stages", 0, True), ("Tn Nm", "Tn", 0, True),
            ("P kW", "Pkw", 2, True),
            ("Ratio min", "ratio_min", 1, True),
            ("Ratio max", "ratio_max", 1, True),
        ],
    },
    "motors": {
        "label": "Motors", "fetch": fetch_motors, "key": "MOTORS",
        "search": ["model", "frame"],
        "cols": [
            ("Model", "model", None, False), ("Frame", "frame", None, False),
            ("kW", "kW", 2, True), ("Poles", "poles", 0, True),
            ("RPM", "rpm", 0, True), ("Eff %", "eff", 1, True),
        ],
    },
    "drives": {
        "label": "Drives", "fetch": fetch_drives, "key": "DRIVES",
        "search": ["name", "type"],
        "cols": [
            ("Name", "name", None, False), ("Type", "type", None, False),
            ("Eff", "eff", 3, True), ("Cost factor", "cost_factor", 2, True),
        ],
    },
    "costs": {
        "label": "Costs", "fetch": fetch_costs, "key": "COSTS_DB",
        "search": ["item", "category"],
        "cols": [
            ("Item", "item", None, False),
            ("Category", "category", None, False),
            ("Unit", "unit", None, False),
            ("Cost USD", "cost", 2, True),
        ],
    },
}


class _LoadWorker(QObject):
    """Fetches one table off the GUI thread."""

    finished = Signal(str, list)
    failed = Signal(str, str)

    def __init__(self, table_id: str, fetcher: Callable, key: str):
        super().__init__()
        self._id = table_id
        self._fetch = fetcher
        self._key = key

    def run(self) -> None:
        try:
            r = self._fetch()
        except Exception as exc:
            self.failed.emit(self._id, str(exc))
            return
        rows: list = []
        if isinstance(r, list):
            rows = r
        elif isinstance(r, dict):
            if r.get("error"):
                self.failed.emit(
                    self._id, str(r.get("message") or "Request failed")
                )
                return
            # Accept several envelope shapes rather than assuming one.
            for candidate in (self._key, self._key.lower(), "items", "rows",
                              "data", "materials"):
                v = r.get(candidate)
                if isinstance(v, list):
                    rows = v
                    break
        self.finished.emit(self._id, rows)


class _TablePane(QWidget):
    """Search bar + filter + table for one reference table."""

    def __init__(self, spec: dict, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._spec = spec
        self._rows: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self._search = QLineEdit()
        self._search.setPlaceholderText(
            "Search " + " / ".join(spec["search"]) + " …"
        )
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG}; border: 1px solid {BORDER};
                border-radius: 4px; padding: 6px 10px;
                color: {TEXT}; font-size: 11px;
            }}
            QLineEdit:focus {{ border: 1px solid {PRIMARY}; }}
        """)
        self._search.textChanged.connect(self._apply_filter)
        bar.addWidget(self._search, 1)

        self._cat = QComboBox()
        self._cat.addItem("All Categories", "")
        self._cat.setStyleSheet(f"""
            QComboBox {{
                background-color: {BG}; border: 1px solid {BORDER};
                border-radius: 4px; padding: 6px 10px;
                color: {TEXT}; font-size: 11px; min-width: 150px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {PANEL2}; color: {TEXT};
                selection-background-color: {PRIMARY};
            }}
        """)
        self._cat.currentIndexChanged.connect(lambda _i: self._apply_filter())
        self._has_cat = any(c[1] == "category" for c in spec["cols"])
        self._cat.setVisible(self._has_cat)
        bar.addWidget(self._cat)

        self._count = QLabel("—")
        self._count.setStyleSheet(
            f"color: {MUTED}; font-size: 10px; padding: 0 4px;"
        )
        bar.addWidget(self._count)
        layout.addLayout(bar)

        self._table = QTableWidget()
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.setAlternatingRowColors(False)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {PANEL}; border: 1px solid {BORDER};
                border-radius: 8px; gridline-color: {BORDER};
                color: {TEXT}; font-size: 10px;
            }}
            QHeaderView::section {{
                background-color: {BG}; color: #93c5fd; border: none;
                border-bottom: 2px solid {BORDER}; padding: 5px 8px;
                font-size: 9px; font-weight: 700;
            }}
            QTableWidget::item:selected {{
                background-color: rgba(74,158,255,0.18); color: {TEXT};
            }}
        """)
        layout.addWidget(self._table, 1)

    # ── data ──────────────────────────────────────────────────────────────

    def set_rows(self, rows: list) -> None:
        self._rows = [r for r in rows if isinstance(r, dict)]
        if self._has_cat:
            cats = sorted({
                str(r.get("category")) for r in self._rows
                if r.get("category")
            })
            current = self._cat.currentData()
            self._cat.blockSignals(True)
            self._cat.clear()
            self._cat.addItem("All Categories", "")
            for c in cats:
                self._cat.addItem(c, c)
            idx = self._cat.findData(current)
            self._cat.setCurrentIndex(idx if idx >= 0 else 0)
            self._cat.blockSignals(False)
        self._apply_filter()

    def set_error(self, msg: str) -> None:
        self._rows = []
        self._table.setRowCount(0)
        self._count.setText(f"⚠ {msg}")
        self._count.setStyleSheet(f"color: {DANGER}; font-size: 10px;")

    def _apply_filter(self) -> None:
        q = self._search.text().strip().lower()
        cat = self._cat.currentData() if self._has_cat else ""
        rows = self._rows
        if cat:
            rows = [r for r in rows if str(r.get("category") or "") == cat]
        if q:
            keys = self._spec["search"]
            rows = [
                r for r in rows
                if any(q in str(r.get(k) or "").lower() for k in keys)
            ]
        self._render(rows)
        self._count.setText(f"{len(rows)} / {len(self._rows)}")
        self._count.setStyleSheet(f"color: {MUTED}; font-size: 10px;")

    def _render(self, rows: Sequence[dict]) -> None:
        cols = self._spec["cols"]
        # Sorting must be off while populating or Qt re-sorts mid-fill and
        # scrambles row/item alignment.
        self._table.setSortingEnabled(False)
        self._table.clear()
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels([c[0] for c in cols])
        self._table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            for c, (_hdr, key, dp, right) in enumerate(cols):
                tip = ""
                colour: Optional[str] = None
                if key == "_coverage":
                    text, colour = _coverage(row)
                    tip = _coverage_detail(row)
                elif key == "flags":
                    text = _flags_text(row.get("flags"))
                elif key == "flowability":
                    v = row.get("flowability")
                    text = ("—" if v is None
                            else f"{v} — {_FLOWABILITY.get(int(v), '')}")
                elif dp is not None:
                    text = _fmt(row.get(key), dp)
                else:
                    v = row.get(key)
                    text = "—" if v is None or v == "" else str(v)

                item = QTableWidgetItem(text)
                if right:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                if colour:
                    item.setForeground(QColor(colour))
                elif key == "name" or key == "model" or key == "item":
                    item.setForeground(QColor(TEXT))
                if tip:
                    item.setToolTip(tip)
                self._table.setItem(r, c, item)

        self._table.resizeColumnsToContents()
        self._table.setSortingEnabled(True)


class DatabaseWorkspace(ModuleWorkspace):

    page_id = "db"
    meta = ModuleMeta(
        label="Material Database",
        icon="🗄️",
        subtitle="Materials · Bearings · Gearboxes · Motors · Drives · Costs",
        group="reference",
    )

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._threads: dict[str, QThread] = {}
        self._workers: dict[str, _LoadWorker] = {}
        self._loaded: set[str] = set()

        self.setStyleSheet(f"background-color: {BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._panes: dict[str, _TablePane] = {}
        for tid, spec in TABLES.items():
            pane = _TablePane(spec)
            self._panes[tid] = pane
            self._stack.addWidget(pane)
        layout.addWidget(self._stack, 1)

        self._current = next(iter(TABLES))

    # ── contract ──────────────────────────────────────────────────────────

    def tabs(self) -> Sequence[TabSpec]:
        return tuple(
            TabSpec(tab_id=tid, label=spec["label"])
            for tid, spec in TABLES.items()
        )

    def on_tab_changed(self, tab_id: str) -> None:
        pane = self._panes.get(tab_id)
        if pane is None:
            return
        self._current = tab_id
        self._stack.setCurrentWidget(pane)
        self._load(tab_id)

    def on_activate(self) -> None:
        self._load(self._current)

    # ── loading ───────────────────────────────────────────────────────────

    def _load(self, table_id: str) -> None:
        """
        Fetch a table once, on first view.

        Six tables × 531 materials is a lot to pull at startup for a page the
        user may not open; each tab fetches when first shown and is cached
        thereafter.
        """
        if table_id in self._loaded or table_id in self._threads:
            return
        spec = TABLES.get(table_id)
        if spec is None:
            return
        self._loaded.add(table_id)

        thread = QThread()
        worker = _LoadWorker(table_id, spec["fetch"], spec["key"])
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_rows)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(lambda tid=table_id: self._cleanup(tid))
        self._threads[table_id] = thread
        self._workers[table_id] = worker
        thread.start()

    def _on_rows(self, table_id: str, rows: list) -> None:
        pane = self._panes.get(table_id)
        if pane is not None:
            pane.set_rows(rows)

    def _on_failed(self, table_id: str, msg: str) -> None:
        pane = self._panes.get(table_id)
        if pane is not None:
            pane.set_error(msg)
        # Allow a retry on the next visit rather than caching the failure.
        self._loaded.discard(table_id)

    def _cleanup(self, table_id: str) -> None:
        thread = self._threads.pop(table_id, None)
        if thread is not None:
            thread.deleteLater()
        self._workers.pop(table_id, None)

    def closeEvent(self, event) -> None:
        for thread in list(self._threads.values()):
            if thread.isRunning():
                thread.quit()
                thread.wait(2000)
        super().closeEvent(event)