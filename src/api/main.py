"""
FastAPI application for Editorial Scripts
RESTful API with async support
"""

from contextlib import asynccontextmanager
import logging
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from ..infrastructure.config import get_settings
from ..infrastructure.database.engine import init_db, close_db
from ..infrastructure.browser_pool import get_browser_pool, shutdown_browser_pool
from ..infrastructure.cache.redis_cache import get_cache, close_cache

from .routers import manuscripts, referees, extractions, analytics

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Editorial Scripts API")
    
    # Initialize services
    await init_db()
    await get_browser_pool()
    await get_cache()
    
    logger.info("All services initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Editorial Scripts API")
    await close_db()
    await shutdown_browser_pool()
    await close_cache()
    

# Create FastAPI app
app = FastAPI(
    title="Editorial Scripts API",
    description="API for managing academic journal editorial workflows",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# Include routers
app.include_router(
    manuscripts.router,
    prefix=f"{settings.api_prefix}/manuscripts",
    tags=["manuscripts"]
)

app.include_router(
    referees.router,
    prefix=f"{settings.api_prefix}/referees",
    tags=["referees"]
)

app.include_router(
    extractions.router,
    prefix=f"{settings.api_prefix}/extractions",
    tags=["extractions"]
)

app.include_router(
    analytics.router,
    prefix=f"{settings.api_prefix}/analytics",
    tags=["analytics"]
)


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
    try:
        # Check database
        from ..infrastructure.database.engine import engine
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
            
        # Check cache
        cache = await get_cache()
        await cache.set("health_check", "ok", ttl=10)
        
        # Check browser pool
        pool = await get_browser_pool()
        pool_health = await pool.health_check()
        
        return {
            "status": "healthy",
            "services": {
                "database": "connected",
                "cache": "connected",
                "browser_pool": pool_health
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/info")
async def info() -> Dict[str, Any]:
    """System information endpoint"""
    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "api_prefix": settings.api_prefix,
        "supported_journals": [
            "SICON", "SIFIN", "MF", "MOR", 
            "JOTA", "MAFE", "FS", "NACO"
        ]
    }