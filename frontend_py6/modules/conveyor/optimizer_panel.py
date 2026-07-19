"""
components/pages/optimizer_panel.py — VECTRIX™ Sequential Auto-Optimiser
═══════════════════════════════════════════════════════════════════════════
Faithful port of AutoOptModal from CalcPage.tsx, adapted to the already-
reserved "Optimizer ·AI" tab slot (theme.CALC_TABS) instead of a floating
modal overlay — this keeps swept results visible when switching tabs and
back, rather than losing them when a modal closes.

Method: grid sweep + weighted-sum scoring (matches the current backend
exactly — see OPTIMIZER_REVIEW_NOTE.md for the NSGA-II comparison flagged
for future review; swapping the method later only touches
_OptimizerWorker.run(), not this UI).

Three sequential phases, exactly as in the React version:
    Phase 1 — Geometry     : D × N × pitch-ratio        (up to 320 calls)
    Phase 2 — Pitch Pattern: inlet/outlet ratios × zones (up to 120 calls, optional)
    Phase 3 — Drive/Hangers: gearbox × bearing × hangers (up to 720 calls)

Each phase runs on a background QThread (via _OptimizerWorker) since a
full Phase 3 sweep is hundreds of sequential HTTP calls to
/api/v1/calculate — blocking the UI thread for that long would freeze
the whole application.

Hard constraints per candidate (must ALL pass to count as "feasible"):
    cap.ok  AND  tor.shOk  AND  deflection_ok  AND  gbx_r.tOk  AND  brg_r.ok

Weighted-sum score (equal weight among selected goals):
    efficiency → eff.score                      (0-100, higher better)
    energy     → 100 - min(100, kWh_t * 20)      (lower kWh/t → higher score)
    cost       → 100 - min(100, cost.total/500)  (lower cost → higher score)
    life       → min(100, wear.life_h/500)       (higher life → higher score)
"""

from __future__ import annotations

import math
from typing import Optional, Any, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, QObject, Signal

from core.theme import (
    BG, PANEL, PANEL2, BORDER, TEXT, TEXT2, TEXT3, MUTED,
    PRIMARY, SUCCESS, WARNING, DANGER, ACCENT, TEAL, PURPLE,
)
from core.api_client import fetch_design, fetch_gearboxes, fetch_bearings


# ── formatting helpers ────────────────────────────────────────────────────

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


# ── Goal / phase config ────────────────────────────────────────────────────

_GOAL_CFG = {
    "efficiency": {"icon": "📈", "label": "Efficiency"},
    "energy":     {"icon": "🔋", "label": "Min Energy"},
    "cost":       {"icon": "💰", "label": "Min Cost"},
    "life":       {"icon": "⏱️", "label": "Max Life"},
}

_PHASE_CFG = {
    "geometry": {"icon": "⭕", "label": "Phase 1", "title": "Geometry",         "sub": "D × N × Pitch"},
    "pitch":    {"icon": "🌀", "label": "Phase 2", "title": "Pitch Pattern",    "sub": "Inlet/Outlet (optional)"},
    "drive":    {"icon": "⚙️", "label": "Phase 3", "title": "Drive & Hangers",  "sub": "GBX × BRG × Hangers"},
}
_PHASE_ORDER = ["geometry", "pitch", "drive"]


def _score_candidate(result: dict, goals: list[str]) -> float:
    """Weighted-sum score — equal weight among selected goals. Matches
    scoreCandidate() in AutoOptModal exactly."""
    if not result or result.get("error"):
        return 0.0
    eff = result.get("eff", {}) or {}
    cost = result.get("cost", {}) or {}
    wear = result.get("wear", {}) or {}

    s_eff = eff.get("score", 0) or 0
    kwh_t = eff.get("kWh_t", 5) or 5
    s_energy = max(0.0, 100 - kwh_t * 20)
    cost_total = cost.get("total", 99999) or 99999
    s_cost = max(0.0, 100 - cost_total / 500)
    life_h = wear.get("life_h", 0) or 0
    s_life = min(100.0, life_h / 500)

    weights = {"efficiency": s_eff, "energy": s_energy, "cost": s_cost, "life": s_life}
    if not goals:
        goals = ["efficiency"]
    return sum(weights.get(g, 0.0) for g in goals) / len(goals)


def _is_feasible(result: dict) -> bool:
    if not result or result.get("error"):
        return False
    return bool(
        (result.get("cap", {}) or {}).get("ok")
        and (result.get("tor", {}) or {}).get("shOk")
        and result.get("deflection_ok")
        and (result.get("gbx_r", {}) or {}).get("tOk")
        and (result.get("brg_r", {}) or {}).get("ok")
    )


# ══════════════════════════════════════════════════════════════════════════
# Background sweep worker
# ══════════════════════════════════════════════════════════════════════════

class _OptimizerWorker(QObject):
    """
    Runs one phase's grid sweep on a background thread. Emits progress
    as it goes and a final result dict when done.

    result dict shape:
        {"top": [...], "partial": {...} | None,
         "total_swept": int, "feasible": int}
    each candidate: {**phase_params, "score": float, "kWh": float,
                      "cost": float, "life": float, "defl_mm": float,
                      "L10": float, "motor": float, "r": <full result dict>}
    """

    progress = Signal(int, int)     # swept, total
    finished = Signal(dict)

    def __init__(
        self,
        phase: str,
        base_payload: dict,
        goals: list[str],
        gearbox_models: list[str],
        bearing_names: list[str],
    ):
        super().__init__()
        self._phase = phase
        self._base = base_payload
        self._goals = goals
        self._gbx_list = gearbox_models
        self._brg_list = bearing_names
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        if self._phase == "geometry":
            self._run_geometry()
        elif self._phase == "pitch":
            self._run_pitch()
        else:
            self._run_drive()

    # ── Phase 1 — Geometry ───────────────────────────────────────────────
    def _run_geometry(self) -> None:
        Ds = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60]
        Ns = [20, 30, 40, 50, 60, 80, 100, 120]
        PRs = [0.75, 0.875, 1.0, 1.125, 1.25]
        total = len(Ds) * len(Ns) * len(PRs)
        swept = 0
        candidates, trials = [], []

        for D in Ds:
            for N in Ns:
                for pr in PRs:
                    if self._stop:
                        return
                    P = min(D * pr, 1.5)
                    payload = {**self._base, "D": D, "N": N, "P": P,
                               "use_multipitch": False, "lam_factor": 1.0}
                    r = fetch_design(payload)
                    swept += 1
                    self.progress.emit(swept, total)
                    if r.get("error"):
                        continue
                    sc = _score_candidate(r, self._goals)
                    c = {
                        "D": D, "N": N, "P": P, "pr": pr, "score": sc,
                        "kWh": (r.get("eff", {}) or {}).get("kWh_t", 9),
                        "cost": (r.get("cost", {}) or {}).get("total", 0),
                        "life": (r.get("wear", {}) or {}).get("life_h", 0),
                        "defl_mm": (r.get("deflection", 0) or 0) * 1000,
                        "L10": (r.get("brg_r", {}) or {}).get("L10", 0),
                        "motor": (r.get("pwr", {}) or {}).get("motor", 0),
                        "r": r,
                    }
                    trials.append(c)
                    if _is_feasible(r):
                        candidates.append(c)

        self._emit_result(candidates, trials, total)

    # ── Phase 2 — Pitch Pattern ───────────────────────────────────────────
    def _run_pitch(self) -> None:
        inlet_ratios = [0.5, 0.6, 0.667, 0.75, 0.8, 0.875]
        outlet_ratios = [0.667, 0.75, 0.875, 1.0]
        pct_pairs = [(10, 10), (15, 15), (20, 20), (10, 15), (15, 10)]
        total = len(inlet_ratios) * len(outlet_ratios) * len(pct_pairs)
        swept = 0
        candidates, trials = [], []

        P_body = self._base.get("P") or self._base.get("D", 0.3)

        for ir in inlet_ratios:
            for outr in outlet_ratios:
                for pi, po in pct_pairs:
                    if self._stop:
                        return
                    P_in = P_body * ir
                    P_out = P_body * outr
                    payload = {**self._base, "P_in": P_in, "P_out": P_out,
                               "pct_in": pi, "pct_out": po,
                               "use_multipitch": True, "lam_factor": 1.0}
                    r = fetch_design(payload)
                    swept += 1
                    self.progress.emit(swept, total)
                    if r.get("error"):
                        continue
                    sc = _score_candidate(r, self._goals)
                    c = {
                        "P_in": P_in, "P_out": P_out, "pct_in": pi, "pct_out": po,
                        "ir": ir, "or_": outr, "score": sc,
                        "kWh": (r.get("eff", {}) or {}).get("kWh_t", 9),
                        "cost": (r.get("cost", {}) or {}).get("total", 0),
                        "life": (r.get("wear", {}) or {}).get("life_h", 0),
                        "defl_mm": (r.get("deflection", 0) or 0) * 1000,
                        "L10": (r.get("brg_r", {}) or {}).get("L10", 0),
                        "motor": (r.get("pwr", {}) or {}).get("motor", 0),
                        "r": r,
                    }
                    trials.append(c)
                    if _is_feasible(r):
                        candidates.append(c)

        self._emit_result(candidates, trials, total, skip_ok=True)

    # ── Phase 3 — Drive & Hangers ─────────────────────────────────────────
    def _run_drive(self) -> None:
        gbx_list = self._gbx_list[:12] or [self._base.get("gbx", "GB-40k")]
        brg_list = self._brg_list[:10] or [self._base.get("brg", "UC210")]
        hangers_opts = [0, 1, 2, 3, 4, 6]
        total = len(gbx_list) * len(brg_list) * len(hangers_opts)
        swept = 0
        candidates, trials = [], []

        for gbx in gbx_list:
            for brg in brg_list:
                for hangers in hangers_opts:
                    if self._stop:
                        return
                    payload = {**self._base, "gbx": gbx, "brg": brg,
                               "hangers": hangers or None, "lam_factor": 1.0}
                    r = fetch_design(payload)
                    swept += 1
                    self.progress.emit(swept, total)
                    if r.get("error"):
                        continue
                    sc = _score_candidate(r, self._goals)
                    c = {
                        "gbx": gbx, "brg": brg, "hangers": hangers, "score": sc,
                        "kWh": (r.get("eff", {}) or {}).get("kWh_t", 9),
                        "cost": (r.get("cost", {}) or {}).get("total", 0),
                        "life": (r.get("wear", {}) or {}).get("life_h", 0),
                        "defl_mm": (r.get("deflection", 0) or 0) * 1000,
                        "L10": (r.get("brg_r", {}) or {}).get("L10", 0),
                        "motor": (r.get("pwr", {}) or {}).get("motor", 0),
                        "r": r,
                    }
                    trials.append(c)
                    if _is_feasible(r):
                        candidates.append(c)

        self._emit_result(candidates, trials, total)

    def _emit_result(
        self, candidates: list[dict], trials: list[dict],
        total: int, skip_ok: bool = False,
    ) -> None:
        sorted_c = sorted(candidates, key=lambda c: -c["score"])
        partial = None
        if not candidates and trials:
            partial = sorted(trials, key=lambda c: -c["score"])[0]
        top_n = 6 if self._phase == "geometry" else 5
        self.finished.emit({
            "top": sorted_c[:top_n],
            "partial": partial,
            "total_swept": total,
            "feasible": len(candidates),
            "skip_ok": skip_ok,
        })


# ══════════════════════════════════════════════════════════════════════════
# UI primitives
# ══════════════════════════════════════════════════════════════════════════

def _goal_pill(key: str, active: bool) -> QPushButton:
    cfg = _GOAL_CFG[key]
    btn = QPushButton(f"{cfg['icon']} {cfg['label']}")
    btn.setCheckable(True)
    btn.setChecked(active)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(26)
    _style_goal_pill(btn, active)
    return btn


def _style_goal_pill(btn: QPushButton, active: bool) -> None:
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {'rgba(232,160,0,.12)' if active else 'transparent'};
            color: {ACCENT if active else TEXT3};
            border: 1px solid {ACCENT if active else BORDER};
            border-radius: 13px; padding: 0px 14px; font-size: 10.5px; font-weight: 700;
        }}
    """)


class _CandidateCard(QFrame):
    """One candidate row — label + stat row + Apply button."""

    def __init__(self, is_top: bool, parent: Optional[QWidget] = None):
        super().__init__(parent)
        border = TEAL if is_top else BORDER
        bg = "rgba(45,212,191,.05)" if is_top else "rgba(0,0,0,.15)"
        self.setStyleSheet(
            f"background-color: {bg}; border: 1px solid {border}44; border-radius: 8px;"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 10, 8)
        lay.setSpacing(8)

        text_box = QVBoxLayout()
        text_box.setSpacing(3)

        self._label_lbl = QLabel("")
        self._label_lbl.setStyleSheet(
            f"color: {TEAL if is_top else TEXT}; font-size: 10.5px; font-weight: 700; "
            f"font-family: 'Consolas', monospace;"
        )
        text_box.addWidget(self._label_lbl)

        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 9px;")
        self._stats_lbl.setWordWrap(True)
        text_box.addWidget(self._stats_lbl)

        lay.addLayout(text_box, 1)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_btn.setFixedHeight(26)
        self.apply_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEAL};
                border: 1px solid {TEAL}44; border-radius: 6px;
                padding: 0px 14px; font-size: 10px; font-weight: 700;
            }}
            QPushButton:hover {{ background: rgba(45,212,191,.1); }}
        """)
        lay.addWidget(self.apply_btn)

    def set_content(self, label: str, stats_html: str) -> None:
        self._label_lbl.setText(label)
        self._stats_lbl.setText(stats_html)


# ══════════════════════════════════════════════════════════════════════════
# AutoOptimizerPanel
# ══════════════════════════════════════════════════════════════════════════

class AutoOptimizerPanel(QWidget):
    """
    Optimizer tab content.

    Constructor args:
        get_base_payload  Callable[[], dict] — reads current sidebar state
        apply_overrides   Callable[[dict], None] — writes overrides back
                           into the sidebar and triggers recalculation
    """

    def __init__(
        self,
        get_base_payload: Callable[[], dict],
        apply_overrides: Callable[[dict], None],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._get_base_payload = get_base_payload
        self._apply_overrides = apply_overrides

        self._goals: set[str] = {"efficiency"}
        self._phase: str = "geometry"
        self._applied: dict[str, dict] = {}          # phase -> overrides dict
        self._phase_results: dict[str, dict] = {}     # phase -> sweep result
        self._gbx_list: list[str] = []
        self._brg_list: list[str] = []

        self._thread: Optional[QThread] = None
        self._worker: Optional[_OptimizerWorker] = None

        self._build_ui()
        self._load_drive_lists()

    # ── UI construction ───────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setStyleSheet(f"background-color: {BG};")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: {BG}; }}"
            f"QScrollBar:vertical {{ background: {BG}; width: 5px; }}"
            f"QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 2px; }}"
        )

        body = QWidget()
        body.setStyleSheet(f"background-color: {BG};")
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(14, 12, 14, 14)
        self._body_layout.setSpacing(10)

        # Header
        title = QLabel("✨ Sequential Auto-Optimiser")
        title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 800;")
        self._body_layout.addWidget(title)

        subtitle = QLabel(
            "Three phases — run each, apply preferred result, continue. "
            "Changes update the live design immediately."
        )
        subtitle.setStyleSheet(f"color: {TEXT3}; font-size: 10px;")
        subtitle.setWordWrap(True)
        self._body_layout.addWidget(subtitle)

        # Goals row
        goals_hdr = QLabel("OPTIMISATION GOALS (multi-select)")
        goals_hdr.setStyleSheet(
            f"color: {TEXT3}; font-size: 9px; font-weight: 700; letter-spacing: .6px;"
        )
        self._body_layout.addWidget(goals_hdr)

        goals_row = QHBoxLayout()
        goals_row.setSpacing(6)
        self._goal_btns: dict[str, QPushButton] = {}
        for key in _GOAL_CFG:
            btn = _goal_pill(key, key in self._goals)
            btn.clicked.connect(lambda checked, k=key: self._toggle_goal(k))
            goals_row.addWidget(btn)
            self._goal_btns[key] = btn
        goals_row.addStretch()
        self._body_layout.addLayout(goals_row)

        # Phase tabs
        phase_row = QHBoxLayout()
        phase_row.setSpacing(4)
        self._phase_btns: dict[str, QPushButton] = {}
        for key in _PHASE_ORDER:
            cfg = _PHASE_CFG[key]
            btn = QPushButton(f"{cfg['icon']} {cfg['label']}: {cfg['title']}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda checked, k=key: self._select_phase(k))
            phase_row.addWidget(btn)
            self._phase_btns[key] = btn
        phase_row.addStretch()
        self._body_layout.addLayout(phase_row)
        self._style_phase_buttons()

        # Effective design summary bar
        self._summary_lbl = QLabel("")
        self._summary_lbl.setStyleSheet(
            f"background-color: #081321; border-radius: 6px; padding: 7px 12px; "
            f"color: {TEXT3}; font-size: 9.5px; font-family: 'Consolas', monospace;"
        )
        self._summary_lbl.setWordWrap(True)
        self._body_layout.addWidget(self._summary_lbl)

        # Phase content area
        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(6)
        self._body_layout.addLayout(self._content_layout)

        self._empty_lbl = QLabel("")
        self._empty_lbl.setStyleSheet(f"color: {MUTED}; font-size: 10.5px; padding: 20px;")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setWordWrap(True)
        self._content_layout.addWidget(self._empty_lbl)

        self._body_layout.addStretch()

        # Footer — status + run button
        footer = QHBoxLayout()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color: {PRIMARY}; font-size: 10px;")
        footer.addWidget(self._status_lbl)
        footer.addStretch()

        self._run_btn = QPushButton("▶ Run Phase 1")
        self._run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_btn.setFixedHeight(32)
        self._run_btn.clicked.connect(self._run_current_phase)
        footer.addWidget(self._run_btn)
        self._body_layout.addLayout(footer)
        self._style_run_button()

        scroll.setWidget(body)
        outer.addWidget(scroll)

        self._update_summary()
        self._render_phase_content()

    # ── Goal / phase selection ────────────────────────────────────────────

    def _toggle_goal(self, key: str) -> None:
        if key in self._goals:
            if len(self._goals) > 1:
                self._goals.discard(key)
        else:
            self._goals.add(key)
        for k, btn in self._goal_btns.items():
            btn.setChecked(k in self._goals)
            _style_goal_pill(btn, k in self._goals)

    def _select_phase(self, phase: str) -> None:
        self._phase = phase
        self._style_phase_buttons()
        self._render_phase_content()
        self._run_btn.setText(f"▶ Run {_PHASE_CFG[phase]['label']}")

    def _style_phase_buttons(self) -> None:
        for key, btn in self._phase_btns.items():
            active = (key == self._phase)
            ran = key in self._phase_results
            applied = key in self._applied
            suffix = ""
            if ran:
                suffix += "  ✓"
            if applied:
                suffix += "  ●Applied"
            btn.setText(f"{_PHASE_CFG[key]['icon']} {_PHASE_CFG[key]['label']}: "
                        f"{_PHASE_CFG[key]['title']}{suffix}")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'rgba(232,160,0,.10)' if active else 'transparent'};
                    color: {ACCENT if active else TEXT3};
                    border: none; border-bottom: 2px solid {ACCENT if active else 'transparent'};
                    padding: 0px 12px; font-size: 10.5px; font-weight: 700; text-align: left;
                }}
            """)

    def _style_run_button(self) -> None:
        running = self._thread is not None
        self._run_btn.setEnabled(not running)
        self._run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {'transparent' if running else 'rgba(45,212,191,.12)'};
                color: {MUTED if running else TEAL};
                border: 1px solid {TEAL if not running else BORDER};
                border-radius: 6px; padding: 0px 20px; font-size: 11px; font-weight: 700;
            }}
        """)

    # ── Effective design summary ─────────────────────────────────────────

    def _effective_payload(self) -> dict:
        base = dict(self._get_base_payload())
        for ph in _PHASE_ORDER:
            base.update(self._applied.get(ph, {}))
        return base

    def _update_summary(self) -> None:
        eff = self._effective_payload()
        D_mm = (eff.get("D", 0.3) or 0.3) * 1000
        P_mm = (eff.get("P", 0.3) or 0.3) * 1000
        self._summary_lbl.setText(
            f"Effective design:  D={D_mm:.0f}mm  ·  N={eff.get('N', 0):g}RPM  ·  "
            f"P={P_mm:.0f}mm  ·  L={eff.get('L', 0):g}m  ·  "
            f"{eff.get('mat', '—')}"
        )

    # ── Drive lists (for Phase 3) ─────────────────────────────────────────

    def _load_drive_lists(self) -> None:
        gbx_result = fetch_gearboxes()
        if not gbx_result.get("error"):
            self._gbx_list = [
                g.get("model") for g in gbx_result.get("items", []) if g.get("model")
            ]
        brg_result = fetch_bearings()
        if not brg_result.get("error"):
            self._brg_list = [
                b.get("name") for b in brg_result.get("items", []) if b.get("name")
            ]

    # ── Run sweep ─────────────────────────────────────────────────────────

    def _run_current_phase(self) -> None:
        if self._thread is not None:
            return  # already running

        base_payload = self._effective_payload()
        phase = self._phase

        self._thread = QThread()
        self._worker = _OptimizerWorker(
            phase, base_payload, list(self._goals),
            self._gbx_list, self._brg_list,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_phase_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

        self._style_run_button()
        self._status_lbl.setText(f"⏳ Sweeping {_PHASE_CFG[phase]['title']}…")

    def _on_progress(self, swept: int, total: int) -> None:
        phase_title = _PHASE_CFG[self._phase]["title"]
        self._status_lbl.setText(f"⏳ Sweeping {phase_title}… {swept}/{total}")

    def _on_phase_finished(self, result: dict) -> None:
        self._phase_results[self._phase] = result
        self._status_lbl.setText("")
        self._style_phase_buttons()
        self._render_phase_content()

    def _cleanup_thread(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self._style_run_button()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._worker is not None:
            self._worker.request_stop()
        super().closeEvent(event)

    # ── Render phase content ─────────────────────────────────────────────

    def _clear_content(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _render_phase_content(self) -> None:
        self._clear_content()
        pr = self._phase_results.get(self._phase)

        if pr is None:
            hint = {
                "geometry": "Run Phase 1 to sweep D × N × Pitch combinations",
                "pitch": "Run Phase 1 first, then Phase 2 to optimise inlet/outlet pitch (optional)",
                "drive": "Run Phase 3 to sweep gearbox and bearing combinations",
            }[self._phase]
            lbl = QLabel(hint)
            lbl.setStyleSheet(f"color: {MUTED}; font-size: 10.5px; padding: 24px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setWordWrap(True)
            self._content_layout.addWidget(lbl)
            return

        feasible = pr.get("feasible", 0)
        total_swept = pr.get("total_swept", 0)
        status_color = SUCCESS if feasible > 0 else WARNING
        status_text = (
            f"✓ {feasible}/{total_swept} feasible designs found" if feasible > 0
            else f"⚠ 0/{total_swept} — no fully feasible design"
        )
        status_lbl = QLabel(status_text)
        status_lbl.setStyleSheet(
            f"color: {status_color}; font-size: 10.5px; font-weight: 700;"
        )
        self._content_layout.addWidget(status_lbl)

        if feasible == 0 and pr.get("skip_ok"):
            note = QLabel("Phase 2 is optional — skip or adjust pitch manually")
            note.setStyleSheet(f"color: {TEXT3}; font-size: 9.5px;")
            self._content_layout.addWidget(note)

        if feasible == 0 and pr.get("partial"):
            partial_hdr = QLabel("🔍 Best Partial — apply as starting point, refine manually:")
            partial_hdr.setStyleSheet(
                f"color: {WARNING}; font-size: 10px; font-weight: 700; padding-top: 4px;"
            )
            self._content_layout.addWidget(partial_hdr)
            self._add_candidate_card(pr["partial"], 0, is_top=False)

        for i, c in enumerate(pr.get("top", [])):
            self._add_candidate_card(c, i, is_top=(i == 0))

    def _add_candidate_card(self, c: dict, index: int, is_top: bool) -> None:
        card = _CandidateCard(is_top)
        label, stats = self._format_candidate(c)
        card.set_content(label, stats)
        card.apply_btn.clicked.connect(lambda: self._apply_candidate(c))
        self._content_layout.addWidget(card)

    def _format_candidate(self, c: dict) -> tuple[str, str]:
        phase = self._phase
        if phase == "geometry":
            label = f"Ø{c['D']*1000:.0f}mm · {c['N']:g} RPM · P={c['P']*1000:.0f}mm"
        elif phase == "pitch":
            label = (
                f"Inlet {c['ir']*100:.0f}%D · Outlet {c['or_']*100:.0f}%D · "
                f"Zones {c['pct_in']}%/{c['pct_out']}%"
            )
        else:
            label = f"{c['gbx']} · {c['brg']} · {c['hangers']} hangers"

        stats = (
            f"Score: {_f(c.get('score'), 1)}   ·   "
            f"kWh/t: {_f(c.get('kWh'), 3)}   ·   "
            f"Motor: {c.get('motor', '—')} kW   ·   "
            f"Defl: {_f(c.get('defl_mm'), 2)}mm   ·   "
            f"L10: {_fi((c.get('L10') or 0) / 1000)}kh"
        )
        return label, stats

    def _apply_candidate(self, c: dict) -> None:
        phase = self._phase
        if phase == "geometry":
            overrides = {"D": c["D"], "N": c["N"], "P": c["P"]}
        elif phase == "pitch":
            overrides = {
                "P_in": c["P_in"], "P_out": c["P_out"],
                "pct_in": c["pct_in"], "pct_out": c["pct_out"],
                "use_multipitch": True,
            }
        else:
            overrides = {"gbx": c["gbx"], "brg": c["brg"], "hangers": c["hangers"]}

        self._applied[phase] = overrides
        self._style_phase_buttons()
        self._update_summary()
        self._apply_overrides(overrides)