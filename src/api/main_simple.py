"""
Simplified FastAPI application for Editorial Scripts
"""

import logging
import os
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Editorial Scripts API",
    description="API for managing academic journal editorial workflows",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
try:
    from .routers import referees
    app.include_router(
        referees.router,
        prefix="/api/v1/referees",
        tags=["referees"]
    )
    logger.info("✅ Referee router loaded")
except Exception as e:
    logger.error(f"❌ Failed to load referee router: {e}")


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {
        "name": "Editorial Scripts API",
        "version": "2.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "database": "check /api/v1/referees/stats for DB status"
        }
    }


@app.get("/info")
async def info() -> Dict[str, Any]:
    """System information endpoint"""
    return {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug": os.getenv("DEBUG", "true").lower() == "true",
        "api_prefix": "/api/v1",
        "supported_endpoints": [
            "GET /",
            "GET /health",
            "GET /info",
            "POST /api/v1/referees/",
            "GET /api/v1/referees/{referee_id}",
            "GET /api/v1/referees/by-email/{email}",
            "GET /api/v1/referees/top-performers",
            "GET /api/v1/referees/stats"
        ]
    }