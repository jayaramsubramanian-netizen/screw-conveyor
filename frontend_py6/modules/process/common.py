"""
components/pages/process_common.py — shared shell for the six process modules
═══════════════════════════════════════════════════════════════════════════
Direct port of frontend/src/components/pages/ProcessPage.tsx, which exports
the primitives every process page imports (C, Field, Divider, KpiCard,
ResultRow, RunBtn, ErrorBanner, EmptyState, ModuleShell).

Porting notes — deviations from the .tsx, and why:

  1. Colour tokens. ProcessPage.tsx keeps a local `C` object whose hexes
     differ slightly from theme.py (border #162438 vs #1c3050, bg #07111e
     vs #0a1628, text #ddeaf6 vs #e8f0fa). theme.py's docstring is explicit
     that components must never keep a local copy, and the existing calc
     page is already built on theme.py. Using theme.py here so the process
     pages sit visually flush with the calc page inside one desktop window.
     The one token with no theme equivalent — the crimson process accent —
     was added to theme.py as PROCESS_ACCENT rather than inlined.

  2. Threading. React's `run()` is an async axios call; the event loop keeps
     the UI alive for free. Qt has no such luxury — a blocking requests call
     on the GUI thread freezes the window. Every calculation therefore goes
     through _CalcWorker on a QThread, following the exact _SweepWorker
     pattern already established in calc_basis_panel.py.

  3. AxialChart is deliberately NOT ported here. The .tsx version is a
     Recharts LineChart; the PySide6 app uses pyqtgraph (see
     calc_basis_panel.py). Only the dryer/cooler/reactor modules feed it a
     `history` array, so it belongs with those pages, not in the shared
     shell. Ported when those modules land.

No physics in this file. Rendering and transport only.
"""

from __future__ import annotations

from typing import Optional, Callable, Any, Sequence, TypeVar

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QComboBox,
    QHBoxLayout, QVBoxLayout, QGridLayout, QScrollArea,
    QDoubleSpinBox, QSizePolicy,
)
from PySide6.QtCore import Qt, QObject, QThread, Signal

from core.theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER, TEAL, PURPLE, PROCESS_ACCENT,
)
from core.api_client import fetch_process
from modules.base import ModuleWorkspace, ModuleMeta, TabSpec

#: Preserves a widget's concrete type through Card.add_row/add_widget.
_W = TypeVar("_W", bound=QWidget)


# ── Field editor input styling ────────────────────────────────────────────
_INPUT_QSS = f"""
    QDoubleSpinBox, QComboBox {{
        background-color: {BG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 4px 8px;
        color: {TEXT};
        font-family: 'JetBrains Mono', 'Consolas', monospace;
        font-size: 11px;
        min-height: 18px;
    }}
    QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1px solid {PRIMARY};
    }}
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        width: 0px; border: none;
    }}
    QComboBox::drop-down {{
        border: none; width: 16px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {PANEL2};
        color: {TEXT};
        selection-background-color: {PRIMARY};
        border: 1px solid {BORDER};
    }}
"""


def _status_color(ok: Optional[bool], fallback: str = TEAL) -> str:
    """ok=True → green, ok=False → red, ok=None → caller's colour."""
    if ok is True:
        return SUCCESS
    if ok is False:
        return DANGER
    return fallback


def fmt(val: Any, dp: int = 2, fallback: str = "—") -> str:
    """Mirror of the .tsx `?.toFixed(dp) || '—'` idiom.

    Guards None explicitly. The React optional-chain silently yields '—' for
    a missing key; doing the same here keeps a backend field-name drift from
    crashing the page the way `.toFixed()` on undefined does in JS.
    """
    if val is None:
        return fallback
    try:
        return f"{float(val):.{dp}f}"
    except (TypeError, ValueError):
        return str(val)


# ── Field ─────────────────────────────────────────────────────────────────

class Field(QWidget):
    """
    Label + unit caption above a numeric spinbox or a combo.

    Port of ProcessPage.tsx <Field/>. Exposes .value() so pages assemble
    payloads by reading fields directly, replacing React's setter closures.
    """

    changed = Signal()

    def __init__(
        self,
        label: str,
        value: Any,
        minimum: float = 0.0,
        maximum: float = 1e9,
        step: float = 0.01,
        unit: str = "",
        options: Optional[Sequence[tuple[str, str]]] = None,
        decimals: Optional[int] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._is_combo = options is not None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(2)

        cap = QLabel(
            f"{label.upper()}"
            + (f"  <span style='color:{TEXT3};font-weight:400;'>{unit}</span>"
               if unit else "")
        )
        cap.setTextFormat(Qt.TextFormat.RichText)
        cap.setStyleSheet(
            f"color: {MUTED}; font-size: 8.5px; font-weight: 700; "
            f"letter-spacing: 0.08em;"
        )
        layout.addWidget(cap)

        if self._is_combo:
            self._editor: QWidget = QComboBox()
            assert isinstance(self._editor, QComboBox)
            for val, lbl in options:            # type: ignore[union-attr]
                self._editor.addItem(lbl, val)
            idx = self._editor.findData(value)
            if idx >= 0:
                self._editor.setCurrentIndex(idx)
            # Relay through a lambda: currentIndexChanged carries an int and
            # `changed` takes none, so a direct connect raises TypeError on
            # every edit rather than at wire-up time.
            self._editor.currentIndexChanged.connect(
                lambda _idx: self.changed.emit()
            )
        else:
            spin = QDoubleSpinBox()
            # Derive decimals from step so 0.05 shows 2dp and 1 shows 0dp,
            # matching how the HTML number input renders each field.
            if decimals is None:
                decimals = 0 if float(step).is_integer() else (
                    2 if step >= 0.01 else 4
                )
            spin.setDecimals(decimals)
            spin.setRange(minimum, maximum)
            spin.setSingleStep(step)
            spin.setValue(float(value))
            spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            spin.valueChanged.connect(lambda _v: self.changed.emit())  # see above
            self._editor = spin

        self._editor.setStyleSheet(_INPUT_QSS)
        self._editor.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self._editor)

    def value(self) -> Any:
        if self._is_combo:
            return self._editor.currentData()      # type: ignore[union-attr]
        return self._editor.value()                # type: ignore[union-attr]

    def set_options(self, options: Sequence[tuple[str, str]]) -> None:
        """
        Replace a combo Field's options, preserving the current selection
        where possible.

        Exists so callers populating a combo from the backend (the Family
        Designer's material list) do not reach into Field._editor. That
        attribute is typed QWidget, so every combo call through it is a
        static-analysis error, and it couples callers to this widget's
        internals.

        No-op on a numeric Field.
        """
        if not self._is_combo:
            return
        combo = self._editor
        assert isinstance(combo, QComboBox)
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for val, label in options:
            combo.addItem(label, val)
        idx = combo.findData(current)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

    def set_value(self, value: Any) -> None:
        if self._is_combo:
            idx = self._editor.findData(value)     # type: ignore[union-attr]
            if idx >= 0:
                self._editor.setCurrentIndex(idx)  # type: ignore[union-attr]
        else:
            self._editor.setValue(float(value))    # type: ignore[union-attr]


# ── Divider ───────────────────────────────────────────────────────────────

class Divider(QWidget):
    """Crimson tick + section label + hairline rule. Port of <Divider/>."""

    def __init__(self, label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 6)
        layout.setSpacing(8)

        tick = QFrame()
        tick.setFixedSize(12, 2)
        tick.setStyleSheet(
            f"QWidget {{" f"background-color: {PROCESS_ACCENT}; border-radius: 1px;" f"}}"
        )
        layout.addWidget(tick, 0, Qt.AlignmentFlag.AlignVCenter)

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            f"color: {PROCESS_ACCENT}; font-size: 8px; font-weight: 700; "
            f"letter-spacing: 0.12em; font-family: 'Barlow Condensed', sans-serif;"
        )
        layout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(f"background-color: {BORDER};")
        layout.addWidget(rule, 1, Qt.AlignmentFlag.AlignVCenter)


# ── KpiCard ───────────────────────────────────────────────────────────────

class KpiCard(QFrame):
    """Large monospace KPI tile. Port of <KpiCard/>."""

    def __init__(
        self,
        label: str,
        value: str = "—",
        unit: str = "",
        ok: Optional[bool] = None,
        sub: str = "",
        col: str = TEAL,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{" f"background-color: {PANEL}; border: 1px solid {BORDER}; "
            f"border-radius: 8px;" f"}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        self._label = QLabel(label.upper())
        self._label.setStyleSheet(
            f"QFrame {{" f"color: {MUTED}; font-size: 8.5px; font-weight: 700; "
            f"letter-spacing: 0.10em; border: none;" f"}}"
        )
        layout.addWidget(self._label)

        self._value = QLabel()
        self._value.setStyleSheet(
            f"QFrame {{" "border: none;" f"}}"
        )
        layout.addWidget(self._value)

        self._sub = QLabel()
        self._sub.setStyleSheet(
            f"QFrame {{" f"color: {TEXT3}; font-size: 9px; border: none;" f"}}"
        )
        self._sub.setVisible(False)
        layout.addWidget(self._sub)

        self._unit = unit
        self.set_value(value, unit, ok, sub, col)

    def set_value(
        self,
        value: str,
        unit: Optional[str] = None,
        ok: Optional[bool] = None,
        sub: str = "",
        col: str = TEAL,
    ) -> None:
        unit = self._unit if unit is None else unit
        colour = _status_color(ok, col)
        unit_html = (
            f"<span style='font-size:12px;font-weight:400;color:{MUTED};'>"
            f" {unit}</span>" if unit else ""
        )
        self._value.setTextFormat(Qt.TextFormat.RichText)
        self._value.setText(
            f"<span style='font-size:18px;font-weight:800;color:{colour};"
            f"font-family:\"JetBrains Mono\",monospace;'>{value}</span>{unit_html}"
        )
        self._sub.setText(sub)
        self._sub.setVisible(bool(sub))


# ── ResultRow ─────────────────────────────────────────────────────────────

class ResultRow(QWidget):
    """key ····· value unit, hairline underline. Port of <ResultRow/>."""

    def __init__(
        self,
        label: str,
        value: Any = None,
        unit: str = "",
        ok: Optional[bool] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setStyleSheet(
            f"QWidget {{" f"border-bottom: 1px solid {BORDER};" f"}}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(8)

        self._key = QLabel(label)
        self._key.setStyleSheet(
            f"QWidget {{" f"color: {MUTED}; font-size: 11px; border: none;" f"}}"
        )
        layout.addWidget(self._key)
        layout.addStretch()

        self._val = QLabel()
        self._val.setTextFormat(Qt.TextFormat.RichText)
        self._val.setStyleSheet(
            f"QWidget {{" "border: none;" f"}}"
        )
        self._val.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._val)

        self._unit = unit
        self.set_value(value, ok)

    def set_value(self, value: Any, ok: Optional[bool] = None) -> None:
        colour = _status_color(ok, TEXT)
        shown = "—" if value is None else str(value)
        unit_html = (
            f"<span style='color:{MUTED};font-weight:400;'> {self._unit}</span>"
            if self._unit else ""
        )
        self._val.setText(
            f"<span style='font-family:\"JetBrains Mono\",monospace;"
            f"font-weight:700;font-size:11px;color:{colour};'>{shown}</span>"
            f"{unit_html}"
        )


# ── Card — container for ResultRows ───────────────────────────────────────

class Card(QFrame):
    """
    Titled panel holding ResultRows. The .tsx builds these inline as styled
    <div>s; factoring it out here keeps the six pages from each repeating
    the same twelve style properties.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{" f"background-color: {PANEL}; border: 1px solid {BORDER}; "
            f"border-radius: 8px;" f"}}"
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(0)

        head = QLabel(title.upper())
        head.setStyleSheet(
            f"QFrame {{" f"color: {PROCESS_ACCENT}; font-size: 9px; font-weight: 700; "
            f"letter-spacing: 0.10em; border: none; "
            f"font-family: 'Barlow Condensed', sans-serif;" f"}}"
        )
        self._layout.addWidget(head)
        self._layout.addSpacing(8)

    def add_row(self, row: _W) -> _W:
        """
        Add a row and return it with its concrete type preserved.

        Annotated with a TypeVar rather than QWidget: pages assign the
        result straight to an attribute (`self._r_pe = card.add_row(
        ResultRow(...))`) and then call `.set_value()` on it. A plain
        `-> QWidget` return widens the type and every one of those calls
        becomes reportAttributeAccessIssue — 19 of them in the Mixer page
        alone, and the same again for each remaining process module.
        """
        self._layout.addWidget(row)
        return row

    def add_widget(self, w: _W) -> _W:
        self._layout.addWidget(w)
        return w


# ── WarningsPanel ─────────────────────────────────────────────────────────

class WarningsPanel(QWidget):
    """
    Stacked critical / advisory / optimisation notices.

    Port of the warns block in FeederPage.tsx. Lives here rather than in the
    feeder package because `warns: {crit, adv, opt}` is the conveyor
    engine's standard warning shape — ConveyorWorkspace already reads it for
    the nav fail badge — so any module surfacing warnings should render them
    identically.

    Hides itself when every bucket is empty, matching the .tsx guard
    `(r.warns?.crit?.length > 0 || r.warns?.adv?.length > 0)`.
    """

    _STYLES = (
        ("crit", DANGER,  "rgba(224,82,82,0.08)",  "✗ [CRITICAL] "),
        ("adv",  WARNING, "rgba(217,142,0,0.07)",  "▲ [ADVISORY] "),
        ("opt",  TEAL,    "rgba(45,212,191,0.07)", "💡 "),
    )

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self.setVisible(False)

    def set_warnings(self, warns: Optional[dict]) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w is not None:
                w.deleteLater()

        warns = warns or {}
        any_shown = False
        for key, colour, bg, prefix in self._STYLES:
            for msg in (warns.get(key) or []):
                lbl = QLabel(f"{prefix}{msg}")
                lbl.setWordWrap(True)
                lbl.setStyleSheet(
            f"QWidget {{" f"background-color: {bg}; border: 1px solid {colour}; "
                    f"border-radius: 6px; padding: 6px 10px; "
                    f"font-size: 10px; color: {colour};" f"}}"
        )
                self._layout.addWidget(lbl)
                any_shown = True

        self.setVisible(any_shown)


# ── RunBtn ────────────────────────────────────────────────────────────────

class RunBtn(QPushButton):
    """Full-width crimson run button with a loading state. Port of <RunBtn/>."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("▶  RUN CALCULATION", parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(30)
        self._loading = False
        self._apply_style()

    def set_loading(self, loading: bool) -> None:
        self._loading = loading
        self.setEnabled(not loading)
        self.setText("⏳  CALCULATING…" if loading else "▶  RUN CALCULATION")
        self.setCursor(
            Qt.CursorShape.ForbiddenCursor if loading
            else Qt.CursorShape.PointingHandCursor
        )
        self._apply_style()

    def _apply_style(self) -> None:
        bg = TEXT3 if self._loading else PROCESS_ACCENT
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg}; color: #ffffff;
                border: none; border-radius: 5px;
                font-size: 11px; font-weight: 800; letter-spacing: 0.08em;
                font-family: 'Barlow Condensed', sans-serif;
            }}
            QPushButton:hover:enabled {{ background-color: #d9203a; }}
            QPushButton:disabled     {{ color: {TEXT2}; }}
        """)


# ── ErrorBanner ───────────────────────────────────────────────────────────

class ErrorBanner(QFrame):
    """Red inline banner. Port of <ErrorBanner/>. Hidden until set_message."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{" f"background-color: rgba(224,82,82,0.08); "
            f"border: 1px solid {DANGER}; border-radius: 6px;" f"}}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        self._lbl = QLabel()
        self._lbl.setWordWrap(True)
        self._lbl.setStyleSheet(
            f"QFrame {{" f"color: {DANGER}; font-size: 11px; border: none;" f"}}"
        )
        layout.addWidget(self._lbl)
        self.setVisible(False)

    def set_message(self, msg: Optional[str]) -> None:
        if msg:
            self._lbl.setText(f"⚠️  {msg}")
            self.setVisible(True)
        else:
            self.setVisible(False)


# ── EmptyState ────────────────────────────────────────────────────────────

class EmptyState(QWidget):
    """Pre-calculation placeholder. Port of <EmptyState/>."""

    def __init__(
        self,
        icon: str,
        name: str,
        desc: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(8)

        for text, qss in (
            (icon, "font-size: 36px;"),
            (name, f"color: {PROCESS_ACCENT}; font-size: 12px; font-weight: 700;"),
            (desc, f"color: {MUTED}; font-size: 10px;"),
            ("Configure inputs → click Run Calculation",
             f"color: {TEXT3}; font-size: 10px; margin-top: 4px;"),
        ):
            lbl = QLabel(text)
            lbl.setStyleSheet(qss)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setWordWrap(True)
            lbl.setMaximumWidth(340)
            layout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignHCenter)


# ── Background calculation worker ─────────────────────────────────────────

class _CalcWorker(QObject):
    """
    Runs fetch_process off the GUI thread.

    Emits exactly one of finished/failed. api_client returns an error dict
    rather than raising, so both paths are checked — a bare try/except would
    let {"error": True} through as a success and blank the page.
    """

    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, module: str, payload: dict):
        super().__init__()
        self._module = module
        self._payload = payload

    def run(self) -> None:
        try:
            r = fetch_process(self._module, self._payload)
        except Exception as exc:                      # transport-level failure
            self.failed.emit(str(exc))
            return
        if not isinstance(r, dict):
            self.failed.emit("Backend returned an unexpected response type.")
        elif r.get("error"):
            self.failed.emit(str(r.get("message") or r.get("detail") or "Error"))
        else:
            self.finished.emit(r)


# ── ModuleShell ───────────────────────────────────────────────────────────

class ModuleShell(ModuleWorkspace):
    """
    260 px scrolling input rail + scrolling result column.
    Port of <ModuleShell/>, implementing the ModuleWorkspace contract.

    Subclasses implement build_inputs / build_results / collect_payload /
    apply_result, and get run()/threading for free.

    Identity now comes from class attributes rather than constructor
    arguments — `page_id` and `meta` are declared on the subclass, so the
    registry can read a module's label and icon to build the menus without
    instantiating (and therefore laying out) every workspace at startup.

    Subclasses additionally set:
        endpoint    backend key passed to fetch_process; defaults to page_id
        empty_desc  body text for the pre-calculation EmptyState
    """

    abstract = True          # intermediate base — see ModuleWorkspace.abstract
    endpoint: str = ""
    empty_desc: str = ""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Falls back to page_id: for all six process modules the menu key and
        # the backend key are the same string, so requiring both would just
        # be two places to drift.
        self._module = self.endpoint or self.page_id
        icon = self.meta.icon
        title = self.meta.label
        subtitle = self.meta.subtitle
        empty_desc = self.empty_desc
        self._thread: Optional[QThread] = None
        self._worker: Optional[_CalcWorker] = None
        self._result: Optional[dict] = None

        self.setStyleSheet(f"background-color: {BG};")

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # ── input rail ────────────────────────────────────────────────────
        rail = QWidget()
        rail.setStyleSheet(
            f"QFrame {{" f"background-color: {PANEL}; border: 1px solid {BORDER}; "
            f"border-radius: 8px;" f"}}"
        )
        self._rail_layout = QVBoxLayout(rail)
        self._rail_layout.setContentsMargins(12, 12, 12, 12)
        self._rail_layout.setSpacing(0)

        head = QVBoxLayout()
        head.setSpacing(3)
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            f"QFrame {{" "font-size: 20px; border: none;" f"}}"
        )
        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(
            f"QFrame {{" f"color: {PROCESS_ACCENT}; font-size: 12px; font-weight: 800; "
            f"letter-spacing: 0.08em; border: none; "
            f"font-family: 'Barlow Condensed', sans-serif;" f"}}"
        )
        sub_lbl = QLabel(subtitle)
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet(
            f"QFrame {{" f"color: {MUTED}; font-size: 9px; border: none;" f"}}"
        )
        head.addWidget(icon_lbl)
        head.addWidget(title_lbl)
        head.addWidget(sub_lbl)
        self._rail_layout.addLayout(head)
        self._rail_layout.addSpacing(10)

        self.build_inputs(self._rail_layout)

        self._run_btn = RunBtn()
        self._run_btn.clicked.connect(self.run)
        self._rail_layout.addSpacing(10)
        self._rail_layout.addWidget(self._run_btn)
        self._rail_layout.addStretch()

        rail_scroll = QScrollArea()
        rail_scroll.setWidget(rail)
        rail_scroll.setWidgetResizable(True)
        rail_scroll.setFixedWidth(260)
        rail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        rail_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        root.addWidget(rail_scroll)

        # ── result column ─────────────────────────────────────────────────
        body = QWidget()
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(10)

        self._error = ErrorBanner()
        self._body_layout.addWidget(self._error)

        self._empty = EmptyState(icon, title, empty_desc)
        self._body_layout.addWidget(self._empty)

        self._results_host = QWidget()
        self._results_layout = QVBoxLayout(self._results_host)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(10)
        self.build_results(self._results_layout)
        self._results_host.setVisible(False)
        self._body_layout.addWidget(self._results_host)
        self._body_layout.addStretch()

        body_scroll = QScrollArea()
        body_scroll.setWidget(body)
        body_scroll.setWidgetResizable(True)
        body_scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(body_scroll, 1)

    # ── hooks for subclasses ──────────────────────────────────────────────

    def build_inputs(self, layout: QVBoxLayout) -> None:
        raise NotImplementedError

    def build_results(self, layout: QVBoxLayout) -> None:
        raise NotImplementedError

    def collect_payload(self) -> dict:
        raise NotImplementedError

    def apply_result(self, r: dict) -> None:
        raise NotImplementedError

    # ── run cycle ─────────────────────────────────────────────────────────

    def run(self) -> None:
        if self._thread is not None:
            return
        self._error.set_message(None)
        self._run_btn.set_loading(True)

        self._thread = QThread()
        self._worker = _CalcWorker(self._module, self.collect_payload())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _on_finished(self, r: dict) -> None:
        self._result = r
        self._empty.setVisible(False)
        self._results_host.setVisible(True)
        self.apply_result(r)

    def _on_failed(self, msg: str) -> None:
        self._error.set_message(msg)

    def _cleanup_thread(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self._run_btn.set_loading(False)

    def result(self) -> Optional[dict]:
        return self._result