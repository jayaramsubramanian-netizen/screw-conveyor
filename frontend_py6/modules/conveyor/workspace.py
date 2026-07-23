"""
modules/conveyor/workspace.py — Screw Conveyor calculator workspace
═══════════════════════════════════════════════════════════════════════════
The conveyor calculator as a ModuleWorkspace, owning its own four-column
body rather than being the shape the application shell is built around.

What moved here, and why it matters
───────────────────────────────────
Until step 4 these four columns lived directly in ShellWindow:

    col1  200 px  equipment / project tree
    col2  280 px  InputSidebarPanel — all EngineInput fields
    col3  flex    calc tab stack (Results / Optimizer / Axial / …)
    col4  260 px  StatusPanel — design health

Only col3 swapped when the user changed module. Columns 1, 2 and 4 stayed
mounted no matter what, so every other module rendered inside the
conveyor's frame — the Screw Mixer displayed the conveyor's CEMA input
sidebar and design-health column alongside its own input rail. Two input
sidebars, one of them belonging to a different machine.

Moving them here fixes that by construction: they are conveyor widgets in
the conveyor package, mounted only while the conveyor is the active
workspace. The shell no longer has a column layout at all.

Also moved off the shell, for the same reason — they are conveyor
behaviour, not application behaviour:

    run_calculation()      fetch_design + fetch_calculate_multi routing
    _maybe_fetch_axial()   lazy axial-profile fetch with payload-signature cache
    _fetch_axial()         axial fetch + error surface
    _on_sidebar_calculate  sidebar → recalc
    _on_optimizer_apply    optimizer candidate → sidebar → recalc
    _swap_col3_header()    col3 header + fail/warn badges

The `if self._current_page == "calc"` guards that wrapped most of
run_calculation() are all gone. They existed only because the conveyor's
result distribution ran inside a shell shared with every other module.
Here there is nothing else to guard against.

Physics note: nothing in this file computes engineering values. It routes
payloads to the backend and distributes results to panels.
"""

from __future__ import annotations

from typing import Optional, Sequence

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QStackedWidget,
)
from PySide6.QtCore import Qt

from core.theme import BG, BORDER, PRIMARY, CALC_TABS, DEFAULT_PAYLOAD
from core.widgets import ColHeader, Placeholder, fail_warn_badges
from core.api_client import (
    fetch_design, fetch_calculate_multi, fetch_axial_profile,
)
from modules.base import ModuleWorkspace, ModuleMeta, TabSpec

from .sidebar import InputSidebarPanel
from .results_panel import ResultsPanel
from .axial_panel import AxialProfilePanel
from .status_panel import StatusPanel
from .optimizer_panel import AutoOptimizerPanel
from .detail_panels import (
    ChecksPanel, WearPanel, StructuralPanel, MaterialsPanel,
)


_CALC_TAB_INDEX = {t["id"]: i for i, t in enumerate(CALC_TABS)}
_CALC_TAB_LABELS = {t["id"]: t["label"] for t in CALC_TABS}


class ConveyorWorkspace(ModuleWorkspace):

    page_id = "calc"
    meta = ModuleMeta(
        label="Screw Conveyor",
        icon="🔩",
        subtitle="CEMA 7th Ed. · slip-corrected capacity · axial power decomposition",
        group="conveyor",
    )

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_tab = "design"
        self._last_results: dict = {}
        self._last_payload = dict(DEFAULT_PAYLOAD)
        self._axial_loaded_for: Optional[str] = None
        self._combos_loaded = False

        self.setStyleSheet(f"background-color: {BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._build_columns()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{ background-color: {BORDER}; }}
            QSplitter::handle:hover {{ background-color: {PRIMARY}; }}
        """)
        splitter.setHandleWidth(2)
        for col in (self._col1, self._col2, self._col3, self._col4):
            splitter.addWidget(col)
        splitter.setSizes([200, 280, 720, 260])
        for i, stretch in enumerate((0, 0, 1, 0)):
            splitter.setStretchFactor(i, stretch)
        self._splitter = splitter
        root.addWidget(splitter)

    # ── column construction ───────────────────────────────────────────────

    def _build_columns(self) -> None:
        # col1 — equipment tree (still a placeholder; unchanged by this step)
        self._col1 = QWidget()
        c1 = QVBoxLayout(self._col1)
        c1.setContentsMargins(0, 0, 0, 0)
        c1.setSpacing(0)
        c1.addWidget(ColHeader("Equipment", "SC-001"))
        c1.addWidget(Placeholder(
            "Equipment Tree", "Conveyor list + project tree — next session",
        ))

        # col2 — input sidebar
        self._col2 = QWidget()
        c2 = QVBoxLayout(self._col2)
        c2.setContentsMargins(0, 0, 0, 0)
        c2.setSpacing(0)
        c2.addWidget(ColHeader("Parameters", "CEMA 7th Ed."))
        self._sidebar = InputSidebarPanel()
        self._sidebar.calculate.connect(self._on_sidebar_calculate)
        c2.addWidget(self._sidebar)

        # col3 — tab stack
        self._col3 = QWidget()
        self._c3l = QVBoxLayout(self._col3)
        self._c3l.setContentsMargins(0, 0, 0, 0)
        self._c3l.setSpacing(0)
        self._col3_header = ColHeader("Results")
        self._c3l.addWidget(self._col3_header)

        self._tab_stack = QStackedWidget()
        self._results_panel: Optional[ResultsPanel] = None
        self._axial_panel: Optional[AxialProfilePanel] = None
        self._optimizer_panel: Optional[AutoOptimizerPanel] = None
        self._checks_panel: Optional[ChecksPanel] = None
        self._wear_panel: Optional[WearPanel] = None
        self._structural_panel: Optional[StructuralPanel] = None
        self._materials_panel: Optional[MaterialsPanel] = None

        for t in CALC_TABS:
            if t["id"] == "design":
                self._results_panel = ResultsPanel(
                    get_base_payload=self._sidebar.get_payload,
                )
                self._tab_stack.addWidget(self._results_panel)
            elif t["id"] == "axial":
                self._axial_panel = AxialProfilePanel()
                self._axial_panel.refresh_requested.connect(self._on_axial_refresh)
                self._tab_stack.addWidget(self._axial_panel)
            elif t["id"] == "optimizer":
                self._optimizer_panel = AutoOptimizerPanel(
                    get_base_payload=self._sidebar.get_payload,
                    apply_overrides=self._on_optimizer_apply,
                )
                self._tab_stack.addWidget(self._optimizer_panel)
            elif t["id"] == "checks":
                checks = ChecksPanel()
                self._checks_panel = checks
                self._tab_stack.addWidget(checks)
            elif t["id"] == "wear":
                wear = WearPanel()
                self._wear_panel = wear
                self._tab_stack.addWidget(wear)
            elif t["id"] == "structural":
                structural = StructuralPanel()
                self._structural_panel = structural
                self._tab_stack.addWidget(structural)
            elif t["id"] == "materials":
                materials = MaterialsPanel()
                self._materials_panel = materials
                self._tab_stack.addWidget(materials)
            else:
                self._tab_stack.addWidget(Placeholder(
                    t["label"], f"CalcPage › {t['label']} — next session",
                ))
        self._c3l.addWidget(self._tab_stack)

        # col4 — design health
        self._col4 = QWidget()
        c4 = QVBoxLayout(self._col4)
        c4.setContentsMargins(0, 0, 0, 0)
        c4.setSpacing(0)
        self._status_panel = StatusPanel()
        c4.addWidget(self._status_panel)

    # ── ModuleWorkspace contract ──────────────────────────────────────────

    def tabs(self) -> Sequence[TabSpec]:
        return tuple(
            TabSpec(
                tab_id=t["id"],
                label=(f"{t['label']}  ·{t['badge']}" if t.get("badge")
                       else t["label"]),
            )
            for t in CALC_TABS
        )

    def on_tab_changed(self, tab_id: str) -> None:
        self._current_tab = tab_id
        self._tab_stack.setCurrentIndex(_CALC_TAB_INDEX.get(tab_id, 0))
        if tab_id == "axial":
            self._maybe_fetch_axial()
        self._update_header(tab_id)

    def on_activate(self) -> None:
        """
        Populate combos and fire the first calculation the first time this
        workspace is shown, not at application start. Previously this ran
        from the shell's backend health check, which meant the conveyor
        always paid that cost even if the user went straight to the Mixer.
        """
        if not self._combos_loaded:
            self._sidebar.load_combos()
            self._combos_loaded = True
            self.run_calculation(self._last_payload)
        else:
            # Re-publish cached headline numbers so the chips repopulate
            # after the shell blanked them on page change.
            self._publish_kpis(self._last_results)

    # ── slots ─────────────────────────────────────────────────────────────

    def _on_sidebar_calculate(self, payload: dict) -> None:
        self._last_payload = payload
        self.run_calculation(payload)

    def _on_optimizer_apply(self, overrides: dict) -> None:
        """
        Apply a swept candidate. set_payload is a partial update — it only
        touches keys present in the dict — then the recalculation runs on
        the full merged sidebar state, not on the overrides alone.
        """
        self._sidebar.set_payload(overrides)
        self.run_calculation(self._sidebar.get_payload())

    # ── calculation ───────────────────────────────────────────────────────

    def run_calculation(self, payload: Optional[dict] = None) -> None:
        if payload is None:
            payload = self._last_payload
        self._last_payload = payload

        results = fetch_design(payload)
        if results.get("error"):
            print(f"[Backend error] {results.get('message')}")
            return

        self._last_results = results
        self._publish_kpis(results)

        # Standards Comparison — eager fetch on every calculate, matching
        # CalcPage.tsx useQuery(enabled:!!R, staleTime:0). One extra call,
        # but the backend computes all three standards in a single request
        # and the 400 ms sidebar debounce limits how often it fires.
        if self._results_panel is not None:
            multi = fetch_calculate_multi(payload)
            if multi.get("error"):
                # Non-fatal: the Standards tab keeps its previous cache.
                self._results_panel.set_data(results)
            else:
                self._results_panel.set_data(results, multi)

        self._status_panel.set_data(results, payload)

        # Detail tabs read the same design result. Stash D so the structural
        # panel can compute the .tsx's recommended-bearing string, which is a
        # function of the input diameter rather than any engine output.
        results["_D_display"] = payload.get("D")
        results["_sallow_display"] = payload.get("sallow", 40)
        if self._checks_panel is not None:
            self._checks_panel.set_data(results)
        if self._wear_panel is not None:
            self._wear_panel.set_data(results)
        if self._structural_panel is not None:
            self._structural_panel.set_data(results)
        if self._materials_panel is not None:
            self._materials_panel.set_data(results)

        # Shaft deflection profile needs the main design result; cheap to
        # feed every calculate whether or not that tab is visible.
        if self._axial_panel is not None:
            self._axial_panel.set_main_result(results)

        if self._current_tab == "design":
            self._update_header("design")

        # New payload invalidates any loaded axial profile. Don't refetch
        # here — that would fire a network call on every debounced
        # keystroke. The next visit to the Axial tab fetches fresh.
        self._axial_loaded_for = None

    def _publish_kpis(self, results: dict) -> None:
        if not results:
            return
        self.kpis_changed.emit({
            "Qt":        results.get("cap", {}).get("Qt"),
            "cap_ok":    results.get("cap", {}).get("ok"),
            "Pt":        results.get("pwr", {}).get("Pt"),
            "eff_score": results.get("eff", {}).get("score"),
        })
        self.fail_count_changed.emit(
            len(results.get("warns", {}).get("crit", []))
        )

    # ── axial profile (lazy) ──────────────────────────────────────────────

    def _maybe_fetch_axial(self) -> None:
        if str(self._last_payload) == self._axial_loaded_for:
            return
        self._fetch_axial(
            self._axial_panel.segments_value() if self._axial_panel else 60
        )

    def _on_axial_refresh(self, segments: int) -> None:
        self._fetch_axial(segments)

    def _fetch_axial(self, segments: int) -> None:
        if self._axial_panel is None:
            return
        self._axial_panel.set_loading()
        response = fetch_axial_profile({
            "inp": self._last_payload,
            "segments": segments,
        })
        if response.get("error"):
            self._axial_panel.set_error(response.get("message", "Unknown error"))
            return
        self._axial_panel.set_data(response)
        self._axial_loaded_for = str(self._last_payload)

    # ── col3 header ───────────────────────────────────────────────────────

    def _update_header(self, tab_id: Optional[str]) -> None:
        if tab_id is None:
            return
        label = _CALC_TAB_LABELS.get(tab_id, "Results")
        action = None
        if tab_id == "design":
            warns = (self._last_results or {}).get("warns", {})
            action = fail_warn_badges(
                len(warns.get("crit", [])), len(warns.get("adv", [])),
            )
        new_header = ColHeader(label, action=action)
        self._c3l.replaceWidget(self._col3_header, new_header)
        self._col3_header.deleteLater()
        self._col3_header = new_header

    # ── cross-module exchange ─────────────────────────────────────────────

    def export_payload(self) -> dict:
        """Current sidebar inputs, for a peer module to read.

        Reads the sidebar live rather than returning _last_payload, so a
        peer sees what is on screen now, not what was last calculated.
        """
        return self._sidebar.get_payload()

    def receive_payload(self, payload: dict) -> None:
        """Load a design handed over by another module and recalculate.

        set_payload is a partial update — only keys present are touched —
        so the Family Designer sending D/N/P/L/mat/ang/surge leaves every
        other conveyor input (bearing, gearbox, wear allowance) intact.
        Matches applyDesign() in FamilyPage.tsx, which spreads into the
        shared store rather than replacing it.
        """
        self._sidebar.set_payload(payload)
        self.run_calculation(self._sidebar.get_payload())

    # ── accessors used by the shell ───────────────────────────────────────

    def current_payload(self) -> dict:
        return self._last_payload

    def current_results(self) -> dict:
        return self._last_results