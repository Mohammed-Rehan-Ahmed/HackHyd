"""
Rural Healthcare Referral & Journey Management System
Main FastAPI Application
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import json
import asyncio
from datetime import datetime

from database.db import engine, get_db, Base
from services.websocket_manager import ConnectionManager
from api import patients, referrals, hospitals, triage, asha_workers, memory
from services.memory_service import init_memory
from database.seed_data import seed_database

# WebSocket connection manager (shared across routes)
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    # Seed initial data
    from database.db import SessionLocal
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    print("✅ Database initialized and seeded.")
    # Init Hindsight persistent memory
    init_memory()
    yield
    print("🛑 Shutting down.")


app = FastAPI(
    title="Rural Healthcare Referral System",
    description="Intelligent automation workflow for referrals and patient journey management in rural healthcare settings.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inject the shared manager into routers
app.state.manager = manager

# Register API routers
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(referrals.router, prefix="/api/referrals", tags=["Referrals"])
app.include_router(hospitals.router, prefix="/api/hospitals", tags=["Hospitals"])
app.include_router(triage.router, prefix="/api/triage", tags=["Triage"])
app.include_router(asha_workers.router, prefix="/api/asha", tags=["ASHA Workers"])
app.include_router(memory.router, prefix="/api/memory", tags=["Memory"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Rural Healthcare Referral System",
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ─────────────────────────────────────────────
# WebSocket – Hospital Dashboard
# ─────────────────────────────────────────────
@app.websocket("/ws/hospital/{hospital_id}")
async def hospital_dashboard_ws(websocket: WebSocket, hospital_id: str):
    """Real-time WebSocket endpoint for hospital dashboards.
    Pushes incoming referral alerts and bed-availability updates."""
    await manager.connect(websocket, room=f"hospital_{hospital_id}")
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            # Echo acknowledgment back
            await manager.send_personal(
                {"type": "ack", "received": msg},
                websocket,
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket, room=f"hospital_{hospital_id}")


# ─────────────────────────────────────────────
# WebSocket – ASHA Worker App
# ─────────────────────────────────────────────
@app.websocket("/ws/asha/{worker_id}")
async def asha_worker_ws(websocket: WebSocket, worker_id: str):
    """Real-time WebSocket endpoint for ASHA worker mobile app.
    Sends referral confirmation, ticket number, and transport guidance."""
    await manager.connect(websocket, room=f"asha_{worker_id}")
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            await manager.send_personal(
                {"type": "ack", "received": msg},
                websocket,
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket, room=f"asha_{worker_id}")


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
