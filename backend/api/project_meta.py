"""
project_meta.py
===============
Pydantic schema for project header information that prints on equipment reports.
Stored per-session; no DB persistence required.
"""
from pydantic import BaseModel
from typing import Optional

class ProjectMeta(BaseModel):
    project:  Optional[str] = None   # Project name
    tag_no:   Optional[str] = None   # Equipment tag number
    client:   Optional[str] = None   # Client / company
    engineer: Optional[str] = None   # Responsible engineer
    approved: Optional[str] = None   # Approved by
    rev:      Optional[str] = "A"    # Document revision
    doc_no:   Optional[str] = None   # Document number
    site:     Optional[str] = None   # Site / location
    notes:    Optional[str] = None   # Design notes / scope
