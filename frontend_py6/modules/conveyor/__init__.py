"""
modules/conveyor/ — Screw Conveyor calculator (VECTRIX™ flagship module).

Canonical source: frontend/src/components/pages/CalcPage.tsx, against the
backend calc_engine() in backend/core/engine.py.

  sidebar.py            InputSidebarPanel — all EngineInput fields
  results_panel.py      Results tab (cards, checks, StdTabs, basis)
  optimizer_panel.py    3-phase grid-sweep Auto-Optimiser
  axial_panel.py        Axial profile charts
  calc_basis_panel.py   Calculation basis + parameter sweep
  standards_widgets.py  CEMA / KWS / DIN comparison
  status_panel.py       Design-health KPI column
  screw_viz.py          2D helix / cross-section renderer (QPainter)
  model_number.py       VM-series model string builder

Note: these were previously scattered across components/pages/ and
components/, as siblings of actual pages. They are conveyor internals, not
pages, and nothing outside this package should import them once
ConveyorWorkspace lands.
"""
