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

# ══════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY SCALE — 16 px floor
# ══════════════════════════════════════════════════════════════════════════
# Every font-size in the application must come from this scale. 16 px (12 pt)
# is the MINIMUM readable size for this product: it is used on plant floors
# and in design offices on scaled displays, and the previous 8-11 px chrome
# was unreadable at normal viewing distance.
#
# Do not write a literal px size in a component. If a new size seems needed,
# add it here so the scale stays auditable — a regex sweep for
# `font-size: <n>px` should only ever find these constants.

FONT_FAMILY      = "Arial, 'Segoe UI', sans-serif"
FONT_FAMILY_MONO = "'JetBrains Mono', 'Consolas', monospace"

FS_CAPTION = 16   # smallest permitted — field captions, units, sub-labels
FS_BODY    = 16   # default body text, table cells, list rows
FS_LABEL   = 17   # row labels, form labels
FS_VALUE   = 18   # numeric results in tables/rows
FS_SUBHEAD = 18   # card titles, section headers
FS_HEAD    = 20   # panel/column headers
FS_KPI     = 26   # large KPI numerals
FS_TITLE   = 22   # module titles

# ══════════════════════════════════════════════════════════════════════════
# TEXT COLOUR DOCTRINE
# ══════════════════════════════════════════════════════════════════════════
# Readable text is TEXT (near-white). Full stop.
#
# TEXT2 / TEXT3 / MUTED exist for NON-TEXT roles only: hairlines, disabled
# states, chart gridlines, placeholder glyphs. They must not be used to
# de-emphasise words — grey-on-dark at small sizes was the single biggest
# legibility problem in the previous build.
#
# Colour on text carries STATUS and nothing else:
#     SUCCESS  pass / within limit
#     WARNING  advisory / approaching limit
#     DANGER   fail / exceeded
#     ACCENT   the one accented header per container
# A value that is merely "less important" stays TEXT and is de-emphasised by
# size or weight instead.

# ══════════════════════════════════════════════════════════════════════════
# BORDER DOCTRINE — one border per container
# ══════════════════════════════════════════════════════════════════════════
# A container draws at most ONE border. Children inside it draw none; group
# them with spacing or a background tint.
#
# CRITICAL Qt detail: a stylesheet set on a widget cascades to its children,
# and TYPE selectors match subclasses — QLabel inherits QFrame, so
# `QFrame {border: ...}` still borders every label inside. Scope container
# stylesheets by objectName:
#
#     self.setObjectName("myCard")
#     self.setStyleSheet(f"#myCard {{ border: 1px solid {BORDER}; }}")
#
# This is what produces "box in a box" when got wrong.

PROCESS_ACCENT = "#c8192e"  # Jayveecons crimson — matches ProcessPage.tsx C.accent.
                            # The six process modules accent crimson, not amber;
                            # the conveyor calc page keeps ACCENT. Added here rather
                            # than kept as a local copy per this module's docstring.
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
    {"id": "axial",      "label": "Axial Profile"},
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