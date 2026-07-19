"""
core/ — module-agnostic foundation.

Everything here is imported by every module and must never import from
modules/ or app/. That one-way rule is what keeps a module's internals from
leaking sideways into another module.

  theme.py       colour/typography tokens — the single source, never copied
  api_client.py  HTTP transport to the FastAPI backend
  widgets.py     shared primitives (ColHeader, Placeholder, KpiChip, …)
"""
