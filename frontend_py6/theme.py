"""
theme.py — VECTRIX™ Screw Conveyor Designer
═══════════════════════════════════════════════════════════════════════════
Identical palette to the Bucket Elevator app (same source of truth).
Import from here in every component — never keep a local copy.
"""

# ── App-wide UI ───────────────────────────────────────────────────────────
BG        = "#0a1628"
PANEL     = "#0d1c2e"
PANEL2    = "#0f2138"
BORDER    = "#1c3050"
TEXT      = "#e8f0fa"
TEXT2     = "#b0c4d8"
TEXT3     = "#5a7a9a"
MUTED     = "#5a7a9a"
PRIMARY   = "#4a9eff"
SUCCESS   = "#1fb86e"
WARNING   = "#d98e00"
DANGER    = "#e05252"
NONE_C    = "#5a7a9a"

# ── Screw conveyor specific ───────────────────────────────────────────────
ACCENT    = "#e8a000"       # amber — matches HTML app C.accent
PURPLE    = "#a78bfa"       # process module results
TEAL      = "#2dd4bf"       # shaft B / twin-screw colour
BRAND_RED = "#b5362f"       # VECTRIX platform icon background

STATUS_COLOR = {"ok": SUCCESS, "warn": WARNING, "fail": DANGER, "none": NONE_C}

# ── Page metadata — mirrors App.tsx PAGE_META ─────────────────────────────
PAGE_META = {
    "calc":      {"icon": "🔩", "label": "Screw Conveyor",    "group": "conveyor"},
    "family":    {"icon": "📊", "label": "Family Designer",   "group": "conveyor"},
    "feeder":    {"icon": "🎚️", "label": "Feeder / Doser",    "group": "conveyor"},
    "mixer":     {"icon": "🌀", "label": "Screw Mixer",       "group": "process"},
    "dryer":     {"icon": "🌡️", "label": "Screw Dryer",       "group": "process"},
    "cooler":    {"icon": "❄️", "label": "Screw Cooler",      "group": "process"},
    "separator": {"icon": "🔀", "label": "Separator",          "group": "process"},
    "reactor":   {"icon": "⚗️", "label": "Screw Reactor",     "group": "process"},
    "compactor": {"icon": "🗜️", "label": "Compactor",          "group": "process"},
    "db":        {"icon": "🗄️", "label": "Material Database", "group": "reference"},
    "help":      {"icon": "📘", "label": "User Manual",       "group": "reference"},
}

PAGE_GROUPS = {
    "conveyor":  {"label": "Conveyor",  "pages": ["calc", "family", "feeder"]},
    "process":   {"label": "Process",   "pages": ["mixer", "dryer", "cooler",
                                                   "separator", "reactor", "compactor"]},
    "reference": {"label": "Reference", "pages": ["db", "help"]},
}

# ── Calc page tab definitions ─────────────────────────────────────────────
CALC_TABS = [
    {"id": "design",     "label": "Results"},
    {"id": "optimizer",  "label": "Optimizer",  "badge": "AI"},
    {"id": "checks",     "label": "Checks",     "failBadge": True},
    {"id": "components", "label": "Components"},
    {"id": "wear",       "label": "Wear & Life"},
    {"id": "structural", "label": "Structural"},
    {"id": "materials",  "label": "Materials"},
]

# ── Default calculation payload sent on startup ───────────────────────────
DEFAULT_PAYLOAD = {
    "mat":        "Cement",
    "D":          0.3,
    "L":          10.0,
    "N":          60,
    "P":          0.3,
    "P_in":       0.15,
    "P_out":      0.3,
    "pct_in":     10,
    "pct_out":    10,
    "ang":        0,
    "cap":        30.0,
    "surge":      1.2,
    "type":       "screw",
    "shaft_mode": "auto",
    "sallow":     40,
    "ft":         0.006,
    "wa":         0.003,
    "bload":      5.0,
    "brg":        "UC210",
    "gbx":        "GB-20k",
    "hangers":    0,
    "temp_c":     20,
}

# ── Pill geometry ─────────────────────────────────────────────────────────
TAB_PILL_HEIGHT    = 34
TAB_PILL_RADIUS    = TAB_PILL_HEIGHT // 2
MODULE_PILL_HEIGHT = 30
MODULE_PILL_RADIUS = MODULE_PILL_HEIGHT // 2