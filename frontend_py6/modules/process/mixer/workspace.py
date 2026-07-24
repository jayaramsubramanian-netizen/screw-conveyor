"""
components/pages/mixer_page.py — Screw Mixer module
═══════════════════════════════════════════════════════════════════════════
Direct port of frontend/src/components/pages/MixerPage.tsx.

Source-of-truth note: this page was ported from the React .tsx, NOT from
MixerForm/MixerResults in app-standalone.html. The two disagree, and the
disagreement matters:

    app-standalone.html  calcMixer() runs client-side and returns
                         mixing_index / froude_number / P_total_kW …
    MixerPage.tsx        POSTs /api/v1/process/mixer and reads
                         M_adm / Fr / P_mix_kW / Pe / k_eff …

backend/core/engine.py declares the backend the single source of truth for
physics, so the API-backed .tsx is canonical and the standalone HTML is a
superseded prototype. Every field name below was verified against the
literal return dict of calc_mixer() in backend/core/process_engine.py
(lines 628-648) rather than inferred from the .tsx — the .tsx optional-chains
every read, so a name drift there degrades to '—' silently instead of
raising, and would not show up as a bug in the React app.

One value is computed here rather than read from the backend: tip speed,
π·D·N/60. This is a kinematic restatement of two inputs the user just typed,
not a derived engineering conclusion — the same category as the ScrewViz2D
and deflection-profile renderers described in STRUCTURAL_REVIEW_NOTE.md, and
it is carried over because MixerPage.tsx displays it the same way. It is NOT
in the calc_mixer() result and must not be mistaken for backend-verified
output.
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
)
from PySide6.QtCore import Qt

from core.theme import (
    PANEL, BORDER, TEXT, TEXT3, MUTED,
    SUCCESS, WARNING, DANGER, TEAL, PURPLE, PRIMARY,
)
from modules.base import ModuleMeta
from modules.process.common import (
    ModuleShell, Field, Divider, KpiCard, ResultRow, Card, fmt,
)


# ── Lacey index banding — mirrors laceyColor/laceyLabel in the .tsx ───────

def _lacey_color(m: float) -> str:
    if m >= 0.90:
        return SUCCESS
    if m >= 0.75:
        return TEAL
    if m >= 0.50:
        return WARNING
    return DANGER


def _lacey_label(m: float) -> str:
    if m >= 0.90:
        return "Excellent"
    if m >= 0.75:
        return "Good"
    if m >= 0.50:
        return "Moderate"
    return "Poor"


def _regime_color(regime: str) -> str:
    if regime == "Rolling":
        return SUCCESS
    if regime == "Cascading":
        return WARNING
    return DANGER


# ── Quality band ──────────────────────────────────────────────────────────

class _QualityBand(QFrame):
    """Wide M-value strip with a colour-coded left edge. Port of the
    inline <div> quality band in MixerPage.tsx."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        self._m = QLabel("M = —")
        self._m.setStyleSheet(
            f"QFrame {{" "border: none;" f"}}"
        )
        layout.addWidget(self._m, 0, Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        self._quality = QLabel("—")
        self._quality.setStyleSheet(
            f"QFrame {{" "border: none;" f"}}"
        )
        self._detail = QLabel("")
        self._detail.setStyleSheet(
            f"QFrame {{" f"color: {MUTED}; font-size: 9px; border: none;" f"}}"
        )
        text_col.addWidget(self._quality)
        text_col.addWidget(self._detail)
        layout.addLayout(text_col)
        layout.addStretch()

        self._paint(DANGER)

    def _paint(self, colour: str) -> None:
        self.setStyleSheet(
            f"QFrame {{" f"background-color: {PANEL}; border: 1px solid {BORDER}; "
            f"border-radius: 8px; border-left: 4px solid {colour};" f"}}"
        )

    def set_data(self, r: dict) -> None:
        m = r.get("M_adm") or 0.0
        colour = _lacey_color(m)
        self._paint(colour)
        self._m.setText(
            f"<span style='font-size:20px;font-weight:800;color:{colour};"
            f"font-family:\"JetBrains Mono\",monospace;'>"
            f"M = {fmt(m * 100, 1)}%</span>"
        )
        self._m.setTextFormat(Qt.TextFormat.RichText)
        self._quality.setText(
            f"<span style='font-size:11px;font-weight:700;color:{colour};'>"
            f"{_lacey_label(m)} mixing quality</span>"
        )
        self._quality.setTextFormat(Qt.TextFormat.RichText)
        self._detail.setText(
            f"Lacey index via ADM correction · "
            f"Pe = {fmt(r.get('Pe'), 1)} · "
            f"k_eff = {fmt(r.get('k_eff'), 4)} 1/s"
        )


# ── MixerPage ─────────────────────────────────────────────────────────────

class MixerWorkspace(ModuleShell):

    page_id = "mixer"
    endpoint = "mixer"
    meta = ModuleMeta(
        label="Screw Mixer",
        icon="🌀",
        subtitle="Newton number · Lacey index · Axial Dispersion Model · Flow regime",
        group="process",
    )
    empty_desc = (
        "Newton number power model with Lacey mixing index and axial "
        "dispersion RTD correction. Supports ribbon, paddle, plough, and "
        "screw types. Single, twin, and triple shaft configurations."
    )

    # ── inputs ────────────────────────────────────────────────────────────

    def build_inputs(self, layout: QVBoxLayout) -> None:
        layout.addWidget(Divider("Geometry"))
        self._D = Field("Diameter", 0.4, 0.1, 1.5, 0.05, "m")
        self._L = Field("Length", 4.0, 0.5, 40.0, 0.5, "m")
        self._pr = Field("Pitch ratio P/D", 1.0, 0.3, 2.0, 0.1)
        for f in (self._D, self._L, self._pr):
            layout.addWidget(f)

        layout.addWidget(Divider("Drive"))
        self._N = Field("Speed", 40, 2, 200, 1, "RPM")
        self._fill = Field("Fill fraction", 0.45, 0.1, 0.9, 0.05)
        for f in (self._N, self._fill):
            layout.addWidget(f)

        layout.addWidget(Divider("Material"))
        self._rho = Field("Bulk density", 1.2, 0.1, 3.0, 0.05, "t/m³")
        self._psz = Field("Particle size 1", 1.0, 0.01, 50.0, 0.1, "mm")
        self._psz2 = Field("Particle size 2", 1.0, 0.01, 50.0, 0.1, "mm")
        for f in (self._rho, self._psz, self._psz2):
            layout.addWidget(f)

        layout.addWidget(Divider("Configuration"))
        self._mtype = Field(
            "Mixer type", "ribbon",
            options=[
                ("ribbon", "🎗️ Ribbon — axial transport"),
                ("paddle", "🏓 Paddle — radial mixing"),
                ("plough", "🔱 Plough/Shovel — intensive"),
                ("screw",  "🔩 Screw — conveying"),
            ],
        )
        self._mode = Field(
            "Operation mode", "continuous",
            options=[("continuous", "Continuous"), ("batch", "Batch")],
        )
        self._shaft_mode = Field(
            "Shaft configuration", "single",
            options=[
                ("single",       "Single shaft"),
                ("twin_co",      "Twin co-rotating"),
                ("twin_counter", "Twin counter-rotating"),
                ("multi_3",      "Triple shaft"),
            ],
        )
        for f in (self._mtype, self._mode, self._shaft_mode):
            layout.addWidget(f)

    def collect_payload(self) -> dict:
        # Key names match calc_mixer()'s inp.get() reads exactly.
        # `pr` is sent because MixerPage.tsx sends it, though calc_mixer()
        # does not currently read it — kept for parity so the desktop app
        # and the web app post an identical body.
        return {
            "D":          self._D.value(),
            "L":          self._L.value(),
            "N":          self._N.value(),
            "rho":        self._rho.value(),
            "fill":       self._fill.value(),
            "pr":         self._pr.value(),
            "mtype":      self._mtype.value(),
            "mode":       self._mode.value(),
            "shaft_mode": self._shaft_mode.value(),
            "psz":        self._psz.value(),
            "psz2":       self._psz2.value(),
        }

    # ── results ───────────────────────────────────────────────────────────

    def build_results(self, layout: QVBoxLayout) -> None:
        # KPI strip
        kpi_host = QWidget()
        kpi_grid = QGridLayout(kpi_host)
        kpi_grid.setContentsMargins(0, 0, 0, 0)
        kpi_grid.setSpacing(8)
        self._kpi_lacey = KpiCard("Lacey M", unit="%")
        self._kpi_regime = KpiCard("Flow Regime")
        self._kpi_power = KpiCard("Power", unit="kW", col=PURPLE)
        self._kpi_fr = KpiCard("Froude Fr", col=PRIMARY, sub="Fr<0.5 = rolling")
        for col, card in enumerate(
            (self._kpi_lacey, self._kpi_regime, self._kpi_power, self._kpi_fr)
        ):
            kpi_grid.addWidget(card, 0, col)
            kpi_grid.setColumnStretch(col, 1)
        layout.addWidget(kpi_host)

        # Quality band
        self._band = _QualityBand()
        layout.addWidget(self._band)

        # Two side-by-side cards
        pair = QWidget()
        pair_row = QHBoxLayout(pair)
        pair_row.setContentsMargins(0, 0, 0, 0)
        pair_row.setSpacing(10)

        kin = Card("⚙️ Mixing Kinetics")
        self._r_keff   = kin.add_row(ResultRow("k_eff (mixing rate)", unit="1/s"))
        self._r_lacey  = kin.add_row(ResultRow("Lacey M (classical)", unit="%"))
        self._r_adm    = kin.add_row(ResultRow("Lacey M (ADM)", unit="%"))
        self._r_pe     = kin.add_row(ResultRow("Peclet Pe"))
        self._r_tmix   = kin.add_row(ResultRow("t_mix 95%", unit="s"))
        self._r_tres   = kin.add_row(ResultRow("t_res", unit="s"))
        pair_row.addWidget(kin, 1)

        pwr = Card("💡 Power & Structure")
        self._r_power  = pwr.add_row(ResultRow("Power", unit="kW"))
        self._r_torque = pwr.add_row(ResultRow("Torque", unit="Nm"))
        self._r_ne     = pwr.add_row(ResultRow("Newton Ne"))
        self._r_fr     = pwr.add_row(ResultRow("Froude Fr"))
        self._r_shear  = pwr.add_row(ResultRow("Shear rate", unit="1/s"))
        self._r_tip    = pwr.add_row(ResultRow("Tip speed", unit="m/s"))
        pair_row.addWidget(pwr, 1)
        layout.addWidget(pair)

        # Design check
        chk = Card("📋 Design Check")
        self._r_fill    = chk.add_row(ResultRow("Fill vs max"))
        self._r_regime  = chk.add_row(ResultRow("Regime"))
        self._r_mode    = chk.add_row(ResultRow("Mode"))
        self._r_shafts  = chk.add_row(ResultRow("Shafts"))
        self._r_vaxial  = chk.add_row(ResultRow("v_axial", unit="m/s"))
        self._r_slip    = chk.add_row(ResultRow("Slip S"))
        layout.addWidget(chk)

    def apply_result(self, r: dict) -> None:
        m_adm = r.get("M_adm") or 0.0
        regime = r.get("regime") or "—"

        self._kpi_lacey.set_value(
            fmt(m_adm * 100, 1), col=_lacey_color(m_adm),
            sub=_lacey_label(m_adm),
        )
        self._kpi_regime.set_value(regime, col=_regime_color(regime))
        self._kpi_power.set_value(fmt(r.get("P_mix_kW"), 2), col=PURPLE)
        self._kpi_fr.set_value(
            fmt(r.get("Fr"), 4), col=PRIMARY, sub="Fr<0.5 = rolling",
        )

        self._band.set_data(r)

        self._r_keff.set_value(fmt(r.get("k_eff"), 5))
        self._r_lacey.set_value(fmt((r.get("M_lacey") or 0.0) * 100, 1))
        self._r_adm.set_value(fmt(m_adm * 100, 1), ok=m_adm >= 0.75)
        self._r_pe.set_value(fmt(r.get("Pe"), 2))
        self._r_tmix.set_value(fmt(r.get("t_mix_s"), 0))
        self._r_tres.set_value(fmt(r.get("t_res_s"), 0))

        self._r_power.set_value(fmt(r.get("P_mix_kW"), 3))
        self._r_torque.set_value(fmt(r.get("Tr_Nm"), 0))
        self._r_ne.set_value(fmt(r.get("Ne"), 2))
        self._r_fr.set_value(fmt(r.get("Fr"), 4))
        self._r_shear.set_value(fmt(r.get("shear_rate"), 1))

        # Tip speed — see module docstring. Read back from the backend echo
        # of D and N rather than the spinboxes, so the row always describes
        # the run that produced these results even if the user has since
        # edited an input.
        D = r.get("D")
        N = r.get("N")
        tip = (math.pi * D * N / 60) if (D is not None and N is not None) else None
        self._r_tip.set_value(fmt(tip, 3))

        fill = r.get("fill")
        fill_max = r.get("fill_max")
        if fill is not None and fill_max is not None:
            self._r_fill.set_value(
                f"{fmt(fill * 100, 0)}% / {fmt(fill_max * 100, 0)}% max",
                ok=r.get("fill_ok"),
            )
        else:
            self._r_fill.set_value(None)

        self._r_regime.set_value(regime, ok=r.get("regime_ok"))
        self._r_mode.set_value(r.get("mode"))
        self._r_shafts.set_value(r.get("ns"))
        self._r_vaxial.set_value(fmt(r.get("v_axial"), 4))
        self._r_slip.set_value(fmt(r.get("slip_S"), 3))