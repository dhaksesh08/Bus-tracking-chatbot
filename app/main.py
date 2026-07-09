"""
Main FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000

Then visit http://127.0.0.1:8000/docs for interactive Swagger API docs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.database import init_db
from app.routers import gps, admin, broadcast

app = FastAPI(
    title="Bus Tracker Chatbot API",
    description="GPS-based school/college bus tracking with chatbot integration.",
    version="1.0.0",
)

# Allow the bots (and any future admin web dashboard) to call this API freely.
# Lock this down to specific origins in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gps.router)
app.include_router(admin.router)
app.include_router(broadcast.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {
        "status": "running",
        "service": "Bus Tracker Chatbot API",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
