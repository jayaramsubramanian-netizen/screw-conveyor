"""
theme.py — VECTRIX™ Screw Conveyor Designer
═══════════════════════════════════════════════════════════════════════════
Identical palette to the Bucket Elevator app (same source of truth).
Added: ACCENT_AMBER for the screw conveyor's own brand colour, and
TEAL / PURPLE which are already used in the process-module results.
Import from here in every component — never keep a local copy.
"""

# ── App-wide UI (panels, text, borders) ─────────────────────────────────
BG       = "#0a1628"
PANEL    = "#0d1c2e"
PANEL2   = "#0f2138"
BORDER   = "#1c3050"
TEXT     = "#e8f0fa"
TEXT2    = "#b0c4d8"
TEXT3    = "#5a7a9a"
MUTED    = "#5a7a9a"
PRIMARY  = "#4a9eff"
SUCCESS  = "#1fb86e"
WARNING  = "#d98e00"
DANGER   = "#e05252"
NONE_C   = "#5a7a9a"

# ── Screw conveyor specific ──────────────────────────────────────────────
ACCENT   = "#e8a000"       # amber — matches the HTML app's C.accent
PURPLE   = "#a78bfa"       # process module results
TEAL     = "#2dd4bf"       # shaft B / twin-screw colour
BRAND_RED = "#b5362f"      # VECTRIX platform icon background

STATUS_COLOR = {"ok": SUCCESS, "warn": WARNING, "fail": DANGER, "none": NONE_C}

# ── Page metadata — mirrors App.tsx PAGE_META ────────────────────────────
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

# Tab definitions for the Screw Conveyor main calc page
CALC_TABS = [
    {"id": "design",      "label": "Results"},
    {"id": "optimizer",   "label": "Optimizer",   "badge": "AI"},
    {"id": "checks",      "label": "Checks",      "failBadge": True},
    {"id": "components",  "label": "Components"},
    {"id": "wear",        "label": "Wear & Life"},
    {"id": "structural",  "label": "Structural"},
    {"id": "materials",   "label": "Materials"},
]

# Pill geometry — same constants as bucket elevator for visual consistency
TAB_PILL_HEIGHT   = 34
TAB_PILL_RADIUS   = TAB_PILL_HEIGHT // 2
MODULE_PILL_HEIGHT = 30
MODULE_PILL_RADIUS = MODULE_PILL_HEIGHT // 2