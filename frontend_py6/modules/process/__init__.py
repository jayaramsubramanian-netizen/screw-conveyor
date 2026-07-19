"""
modules/process/ — the six process-equipment applications.

Mixer, Dryer, Cooler, Separator, Reactor, Compactor. They share a body
shape (input rail + result column) and a backend route shape
(/api/v1/process/<module>), so common.py holds the shell and primitives
they all use. That sharing lives here rather than in core/ because it is
specific to this family — the conveyor and database modules have neither.

Canonical source for all six: frontend/src/components/pages/<X>Page.tsx,
NOT the same-named components in app-standalone.html. The standalone
prototype computes physics client-side under different field names and is
superseded; backend/core/process_engine.py is authoritative.
"""