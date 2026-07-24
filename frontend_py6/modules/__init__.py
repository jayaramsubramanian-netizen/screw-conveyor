"""
modules/ — one package per main-menu application
═══════════════════════════════════════════════════════════════════════════
Each module is a self-contained application that owns its complete
workspace: inputs, results, visualisations, status. The shell renders only
chrome and hands the whole body to the active module.

Layout
──────
    frontend_py6/
    ├── app/                    (step 4) entry point + workspace host
    │   ├── main.py                 startup only
    │   ├── shell.py                title bar, menu bar, nav, host
    │   └── registry.py             MODULES = {page_id: WorkspaceClass}
    ├── core/                   module-agnostic; imported by everyone
    │   ├── theme.py                colour/type tokens — never copied locally
    │   ├── api_client.py           HTTP transport to FastAPI
    │   └── widgets.py              ColHeader, Placeholder, KpiChip, …
    └── modules/
        ├── base.py             the ModuleWorkspace contract
        ├── conveyor/           Screw Conveyor calculator
        │   ├── sidebar.py          InputSidebarPanel (all EngineInput fields)
        │   ├── results_panel.py    Results tab
        │   ├── optimizer_panel.py  3-phase grid-sweep Auto-Optimiser
        │   ├── axial_panel.py      axial profile charts
        │   ├── calc_basis_panel.py basis text + parameter sweep
        │   ├── standards_widgets.py CEMA / KWS / DIN comparison
        │   ├── status_panel.py     design-health KPI column
        │   ├── screw_viz.py        2D helix renderer (QPainter)
        │   └── model_number.py     VM-series model string
        ├── process/            the six process-equipment modules
        │   ├── common.py           ModuleShell + Field/KpiCard/ResultRow/…
        │   ├── mixer/workspace.py  ✅ done
        │   ├── dryer/  cooler/  reactor/       ← each also needs axial_chart
        │   └── separator/  compactor/
        ├── family/             Family Designer
        ├── database/           Material / equipment database browser
        └── manual/             Reference manual viewer

    All eleven modules are now real implementations; modules/stubs.py has
    been deleted.

Import rule (one-way, and the reason this layout exists)
────────────────────────────────────────────────────────
    core/     imports nothing from modules/ or app/
    modules/  import from core/ and from their own package only
    app/      imports from modules/ and core/

A module never reaches into another module's internals. Behaviour shared
by everything is promoted into core/; behaviour shared by one family lives
in that family's package (see modules/process/common.py). Before the
restructure these all sat flat in components/pages/, where any panel could
import any other and a backend field-name change could propagate sideways
with nothing to stop it.
"""