"""
FastAPI application entry point.
Run:
- From project root: uvicorn backend.main:app --reload --port 8000
- From backend folder: uvicorn main:app --reload --port 8000
"""
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if __package__ in {None, ""}:
    from backend.api.routes import router
    from backend.db.database import engine, Base, initialize_db
else:
    from .api.routes import router
    from .db.database import engine, Base, initialize_db

# Create all tables on startup (idempotent) and seed data if needed
Base.metadata.create_all(bind=engine)
initialize_db()

app = FastAPI(
    title       = "Screw Conveyor Designer API",
    description = "Engineering calculation API for screw conveyor sizing. "
                  "All physics in core/engine.py — validated against CEMA 7th Ed.",
    version     = "2.5.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:5173", "http://localhost:3000"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/")
def root():
    return {"app": "Screw Conveyor Designer", "version": "2.5.0", "docs": "/docs"}
