"""
Voiquyr Core Orchestrator - FastAPI Application
Task 2.1: Basic FastAPI application
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import uvicorn
import os
from contextlib import asynccontextmanager

from app.core.database import init_db
from app.routers import auth, sip_trunks, calls, health

security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Voiquyr Core Orchestrator",
    description="EU-focused Voice AI Platform with Data Sovereignty",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(sip_trunks.router, prefix="/api/sip-trunks", tags=["sip-trunks"])
app.include_router(calls.router, prefix="/api/calls", tags=["calls"])

@app.get("/")
async def root():
    return {
        "message": "Voiquyr Core Orchestrator",
        "region": "EU-Frankfurt",
        "status": "operational"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )