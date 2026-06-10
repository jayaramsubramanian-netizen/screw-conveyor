"""
FastAPI application entry point.
Run: uvicorn backend.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router
from .db.database import engine, Base

# Create all tables on startup (idempotent)
Base.metadata.create_all(bind=engine)

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
