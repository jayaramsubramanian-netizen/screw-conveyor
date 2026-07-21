"""
theme.py — VECTRIX™ Screw Conveyor Designer
═══════════════════════════════════════════════════════════════════════════
Identical palette to the Bucket Elevator app (same source of truth).
Import from here in every component — never keep a local copy.

TYPOGRAPHY & TEXT-COLOR RULES (binding for all frontend files, added per
explicit design correction — apply these to every new/edited file):

  1. FONT FLOOR: no text anywhere may render smaller than FS_MIN (16px,
     equivalent to 12pt). Use the FS_* constants below rather than
     hardcoding pixel sizes — every one of them already respects the
     floor. If a one-off size is ever needed, it must still be >= FS_MIN.

  2. FONT FAMILY: FONT_FAMILY (Arial) for all general UI text. Numeric
     values that benefit from column alignment (tables, KPI values) may
     use FONT_FAMILY_MONO instead — but the 16px floor still applies to
     monospace text exactly the same as everything else.

  3. TEXT COLOR: default to TEXT (near-white, #e8f0fa) for ALL text —
     labels, values, headers, body copy. Do NOT use TEXT2 / TEXT3 / MUTED
     for anything a user needs to read normally; those three are being
     phased out of general use because a dim blue-grey on a dark panel
     reads as invisible. The ONLY colors that should differ from TEXT are
     the semantic status colors (SUCCESS / WARNING / DANGER / ACCENT)
     used specifically to flag pass/warn/fail or a highlighted value —
     never for plain descriptive text.
     TEXT2 / TEXT3 / MUTED remain defined below only for genuinely
     inert chrome (disabled-control backgrounds, hairline dividers) —
     not for anything containing readable text.

  4. ONE BORDER PER CONTAINER: don't put a border on every row, field,
     or sub-element inside an already-bordered card/section. A card has
     exactly one outer border; internal structure is separated with
     background-shade contrast and spacing, not nested boxes. This is
     why input fields no longer carry individual borders (see
     calc_page.py) and why KPI tiles no longer carry a border per tile
     (see status_panel.py) — the containing grid/section already has one.
"""

# ── Typography ────────────────────────────────────────────────────────────
FONT_FAMILY       = "Arial"
FONT_FAMILY_MONO   = "Consolas"   # numeric alignment only — same 16px floor

FS_MIN     = 16   # absolute floor — nothing anywhere may be smaller than this
FS_UNIT    = 16   # inline units, captions, timestamps, section eyebrow text
FS_LABEL   = 16   # field labels
FS_BODY    = 17   # default body / row text
FS_VALUE   = 18   # emphasized values inside cards
FS_SUBHEAD = 19   # card sub-headers
FS_HEAD    = 21   # panel / card headers
FS_TITLE   = 24   # page / app titles
FS_DISPLAY = 30   # hero KPI numbers

# ── App-wide UI ───────────────────────────────────────────────────────────
BG        = "#0a1628"
PANEL     = "#0d1c2e"
PANEL2    = "#0f2138"
BORDER    = "#1c3050"
TEXT      = "#e8f0fa"      # default for ALL readable text — see rule 3 above
TEXT2     = "#b0c4d8"      # chrome only — not for readable text (deprecated for text use)
TEXT3     = "#5a7a9a"      # chrome only — not for readable text (deprecated for text use)
MUTED     = "#5a7a9a"      # chrome only — not for readable text (deprecated for text use)
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

STATUS_COLOR = {"ok": SUCCESS, "warn": WARNING, "fail": DANGER, "none": TEXT}

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
# Bumped from the original 30/34px to comfortably fit >=16px text with
# proper vertical padding.
TAB_PILL_HEIGHT    = 42
TAB_PILL_RADIUS    = TAB_PILL_HEIGHT // 2
MODULE_PILL_HEIGHT = 38
MODULE_PILL_RADIUS = MODULE_PILL_HEIGHT // 2