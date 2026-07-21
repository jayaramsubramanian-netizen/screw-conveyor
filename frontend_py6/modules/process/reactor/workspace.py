"""
modules/process/reactor/workspace.py — Screw Reactor module
═══════════════════════════════════════════════════════════════════════════
Port of frontend/src/components/pages/ReactorPage.tsx.

Field names verified against backend/api/routes.py :: run_reactor
(lines 683-720) rather than process_engine.py, for the reason given in the
Dryer module.

Two contract quirks carried over deliberately:

  1. `len` is sent in ADDITION to `Lr`, both holding the same value. The
     .tsx posts {...inp, len: inp.Lr} and run_reactor reads
     payload.get("len", payload.get("Lr", 4)) — so `Lr` alone would work
     via the fallback, but solve_system() upstream reads `len` directly for
     the segment march. Sending only `Lr` silently gives the solver its
     default length while the summary reports the length you typed.

  2. `tProc` is in the .tsx input state and therefore posted, but has no
     form control — the page never renders a Field for it. Kept at the same
     default so the desktop and web apps post identical bodies.

Set Ea=0 to use k₀ directly as the rate constant (no Arrhenius); that is
the backend's documented behaviour, not a UI convention.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout

from core.theme import SUCCESS, WARNING, DANGER, PURPLE, TEAL
from modules.base import ModuleMeta
from modules.process.common import (
    ModuleShell, Field, Divider, KpiCard, ResultRow, Card, fmt,
)
from modules.process.axial_chart import AxialChart


def _conversion_color(conv: Optional[float]) -> str:
    """Mirrors conv>80 ? green : conv>50 ? amber : red in the .tsx."""
    if conv is None:
        return DANGER
    if conv > 80:
        return SUCCESS
    if conv > 50:
        return WARNING
    return DANGER


class ReactorWorkspace(ModuleShell):

    page_id = "reactor"
    endpoint = "reactor"
    meta = ModuleMeta(
        label="Screw Reactor",
        icon="⚗️",
        subtitle="Arrhenius kinetics · Damköhler number · ADM RTD correction",
        group="process",
    )
    empty_desc = (
        "Arrhenius kinetics with Damköhler and Peclet analysis. Axial "
        "dispersion model (ADM) Danckwerts RTD correction. Set Ea=0 to use "
        "k₀ as direct rate constant."
    )

    #: Posted but not exposed as a control — see module docstring.
    _T_PROC_DEFAULT = 150

    # ── inputs ────────────────────────────────────────────────────────────

    def build_inputs(self, layout: QVBoxLayout) -> None:
        layout.addWidget(Divider("Geometry"))
        self._diam = Field("Diameter", 0.3, 0.1, 1.2, 0.05, "m")
        self._Lr = Field("Length", 4.0, 1.0, 40.0, 0.5, "m")
        for f in (self._diam, self._Lr):
            layout.addWidget(f)

        layout.addWidget(Divider("Drive"))
        self._Nr = Field("Speed", 30, 2, 120, 1, "RPM")
        self._fillR = Field("Fill fraction", 0.35, 0.1, 0.6, 0.05)
        for f in (self._Nr, self._fillR):
            layout.addWidget(f)

        layout.addWidget(Divider("Feed"))
        self._feed = Field("Feed rate", 3.0, 0.1, 500.0, 1.0, "t/h")
        self._rho = Field("Bulk density", 1.2, 0.1, 3.0, 0.05, "t/m³")
        self._tIn = Field("Feed temperature", 20, 0, 500, 5, "°C")
        for f in (self._feed, self._rho, self._tIn):
            layout.addWidget(f)

        layout.addWidget(Divider("Kinetics"))
        self._rxn = Field(
            "Reaction type", "thermal",
            options=[
                ("thermal",     "Thermal decomposition"),
                ("chemical",    "Chemical reaction"),
                ("biological",  "Biological/enzymatic"),
                ("calcination", "Calcination"),
            ],
        )
        self._Ea = Field("Activation energy Ea", 0, 0, 200, 5, "kJ/mol")
        self._k0 = Field("Rate constant k₀ (Ea=0: use as k)",
                         0.08, 0.0001, 10.0, 0.001, "1/s", decimals=4)
        self._dHrxn = Field("Heat of reaction ΔH", 0, -500, 500, 10, "kJ/mol")
        self._CpR = Field("Cp solid", 1000, 200, 4000, 50, "J/kgK")
        for f in (self._rxn, self._Ea, self._k0, self._dHrxn, self._CpR):
            layout.addWidget(f)

        layout.addWidget(Divider("RTD"))
        self._D_ax = Field("Axial dispersion D_ax", 0.005, 0.0001, 0.1, 0.001,
                           "m²/s", decimals=4)
        self._resReq = Field("Min residence required", 15, 1, 300, 1, "min")
        for f in (self._D_ax, self._resReq):
            layout.addWidget(f)

    def collect_payload(self) -> dict:
        length = self._Lr.value()
        return {
            "diam":   self._diam.value(),
            "Lr":     length,
            "len":    length,      # both — see module docstring
            "Nr":     self._Nr.value(),
            "fillR":  self._fillR.value(),
            "feed":   self._feed.value(),
            "rho":    self._rho.value(),
            "tIn":    self._tIn.value(),
            "tProc":  self._T_PROC_DEFAULT,
            "rxn":    self._rxn.value(),
            "Ea_kJ":  self._Ea.value(),
            "k0":     self._k0.value(),
            "dHrxn":  self._dHrxn.value(),
            "CpR":    self._CpR.value(),
            "D_ax":   self._D_ax.value(),
            "resReq": self._resReq.value(),
        }

    # ── results ───────────────────────────────────────────────────────────

    def build_results(self, layout: QVBoxLayout) -> None:
        kpi_host = QWidget()
        grid = QGridLayout(kpi_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        self._kpi_conv = KpiCard("Conversion X", unit="%")
        self._kpi_da = KpiCard("Damköhler Da", sub="Da≥1 = reaction limited")
        self._kpi_pe = KpiCard("Peclet Pe", col=PURPLE, sub="Pe>10 = plug flow")
        self._kpi_tres = KpiCard("t_res", unit="min")
        for col, card in enumerate(
            (self._kpi_conv, self._kpi_da, self._kpi_pe, self._kpi_tres)
        ):
            grid.addWidget(card, 0, col)
            grid.setColumnStretch(col, 1)
        layout.addWidget(kpi_host)

        summary = Card("📊 Reactor Summary")
        self._r_conv = summary.add_row(ResultRow("Conversion X", unit="%"))
        self._r_da = summary.add_row(ResultRow("Damköhler Da"))
        self._r_pe = summary.add_row(ResultRow("Peclet number"))
        self._r_tres = summary.add_row(ResultRow("Residence time", unit="min"))
        self._r_req = summary.add_row(ResultRow("Required", unit="min"))
        self._r_tout = summary.add_row(ResultRow("T outlet", unit="°C"))
        self._r_vax = summary.add_row(ResultRow("Axial velocity", unit="m/s"))
        layout.addWidget(summary)

        self._chart_conv = AxialChart("Conversion X", "X_conv", "%", SUCCESS)
        self._chart_temp = AxialChart("Temperature", "T", "°C", DANGER)
        for c in (self._chart_conv, self._chart_temp):
            layout.addWidget(c)

    def apply_result(self, r: dict) -> None:
        summary = r.get("summary") or {}
        conv = r.get("conv")
        da = r.get("Da")
        ok = r.get("ok")
        da_ok = None if da is None else da >= 1

        self._kpi_conv.set_value(fmt(conv, 1), col=_conversion_color(conv))
        self._kpi_da.set_value(
            fmt(da, 2), ok=da_ok, sub="Da≥1 = reaction limited",
        )
        self._kpi_pe.set_value(
            fmt(r.get("Pe_r"), 1), col=PURPLE, sub="Pe>10 = plug flow",
        )
        self._kpi_tres.set_value(
            fmt(r.get("res_min"), 1), ok=ok,
            sub=f"req ≥{self._resReq.value():.0f}min",
        )

        self._r_conv.set_value(
            fmt(conv, 2), ok=None if conv is None else conv >= 80,
        )
        self._r_da.set_value(fmt(da, 3), ok=da_ok)
        self._r_pe.set_value(fmt(r.get("Pe_r"), 1))
        self._r_tres.set_value(fmt(r.get("res_min"), 2), ok=ok)
        self._r_req.set_value(f"≥{fmt(r.get('resReq'), 0)}")
        self._r_tout.set_value(fmt(summary.get("T_out"), 1))
        self._r_vax.set_value(fmt(summary.get("v_ax"), 4))

        history = r.get("history") or []
        for chart in (self._chart_conv, self._chart_temp):
            chart.set_history(history)