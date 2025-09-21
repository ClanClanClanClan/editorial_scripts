"""FastAPI application for Editorial Command Center."""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from passlib.context import CryptContext
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from src.ecc.infrastructure.database.connection import close_database, initialize_database
from src.ecc.infrastructure.monitoring.middleware import ObservabilityMiddleware
from src.ecc.infrastructure.monitoring.telemetry import ECCObservability, ObservabilityConfig
from src.ecc.interfaces.api import ai_analysis, auth, journals, manuscripts

# Metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"]
)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: float
    checks: dict[str, bool]


# Global observability instance
observability: ECCObservability | None = None
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    global observability

    # Startup
    logger.info("🚀 Starting Editorial Command Center API")
    # Production secret sanity check (hard-fail in production)
    env_name = os.getenv("ECC_ENV", "development").lower()
    if env_name == "production":
        if os.getenv("ECC_SECRET_KEY", "devsecret_change_me") == "devsecret_change_me":
            raise RuntimeError(
                "ECC_SECRET_KEY must be set to a strong value in production (not the default)."
            )

    # Initialize observability stack
    try:
        observability_config = ObservabilityConfig(
            service_name="ecc-api",
            service_version="2.0.0",
            environment="development",
            jaeger_endpoint="http://localhost:14268/api/traces",
        )
        observability = ECCObservability(observability_config)
        await observability.initialize()
        logger.info("✅ Observability stack initialized")
    except Exception as e:
        logger.warning("⚠️  Observability initialization failed: %s", e)
        logger.info("Continuing without observability features")
        observability = None

    # Initialize database connection
    try:
        from src.ecc.infrastructure.secrets.provider import get_secret_with_vault

        host = get_secret_with_vault("DB_HOST")
        name = get_secret_with_vault("DB_NAME")
        user = get_secret_with_vault("DB_USER")
        password = get_secret_with_vault("DB_PASSWORD")
        port = get_secret_with_vault("DB_PORT") or "5433"
        if all([host, name, user, password]):
            database_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"
        else:
            database_url = get_secret_with_vault("DATABASE_URL") or os.getenv(
                "DATABASE_URL", "postgresql+asyncpg://localhost:5433/ecc_db"
            )
    except Exception:
        database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost:5433/ecc_db")
    try:
        await initialize_database(database_url, echo=False)
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.warning("⚠️  Database initialization failed: %s", e)
        logger.info("Continuing; /health will report degraded state")
    else:
        # Seed admin in development if no users
        try:
            if os.getenv("ECC_ENV", "development").lower() == "development":
                from sqlalchemy import select

                from src.ecc.infrastructure.database.connection import get_database_manager
                from src.ecc.infrastructure.database.models import UserModel

                dbm = await get_database_manager()
                async with dbm.get_session() as session:
                    res = await session.execute(select(UserModel))
                    if res.first() is None:
                        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                        password = os.getenv("ECC_DEFAULT_ADMIN_PASSWORD", "admin")
                        user = UserModel(
                            username="admin",
                            email="admin@ecc.local",
                            password_hash=pwd_context.hash(password),
                            roles=["admin", "editor"],
                        )
                        session.add(user)
                        await session.flush()
                        logger.info("✅ Seeded default admin user (development)")
        except Exception as e:
            logger.warning("⚠️  Admin seeding failed: %s", e)

    # TODO: Initialize cache connection
    # TODO: Initialize journal adapters
    yield

    # Shutdown
    logger.info("🛑 Shutting down Editorial Command Center API")

    # Close observability
    if observability:
        await observability.shutdown()
        logger.info("✅ Observability stack closed")

    # Close database connections
    await close_database()
    logger.info("✅ Database connections closed")

    # TODO: Close cache connections
    # TODO: Cleanup browser instances


app = FastAPI(
    title="Editorial Command Center",
    description="AI-enhanced editorial management system for academic journals",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Middleware


# Security headers
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        # Minimal CSP suitable for API only
        response.headers.setdefault(
            "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; sandbox"
        )
        return response


# Simple in-memory rate limiting (per-IP per-path)
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_per_minute: int = 180):
        super().__init__(app)
        self.max_per_minute = max_per_minute
        self._counters: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        from time import time

        client = request.client.host if request.client else "unknown"
        key = f"{client}:{request.url.path}"
        now = time()
        window = 60.0
        bucket = self._counters.get(key, [])
        bucket = [t for t in bucket if now - t < window]
        if len(bucket) >= self.max_per_minute:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        bucket.append(now)
        self._counters[key] = bucket
        return await call_next(request)


# CORS configuration — strict in production, permissive in dev
env_name = os.getenv("ECC_ENV", "development").lower()
default_origins = "http://localhost:3000,http://127.0.0.1:3000" if env_name != "production" else ""
cors_origins_env = os.getenv("ECC_CORS_ORIGINS", default_origins)
allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Observability middleware and security/rate limiting
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
rate_limit = int(os.getenv("ECC_RATE_LIMIT_PER_MINUTE", "180"))
app.add_middleware(RateLimitMiddleware, max_per_minute=rate_limit)

# Additional middleware will be added later


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for Kubernetes probes."""
    checks = {
        "database": await _check_database_health(),
        "cache": await _check_cache_health(),
        "ai_service": await _check_ai_service_health(),
        "observability": observability is not None and observability.tracer is not None,
    }

    status = "healthy" if all(checks.values()) else "degraded"

    return HealthResponse(status=status, version="2.0.0", timestamp=time.time(), checks=checks)


@app.get("/ready")
async def readiness_check() -> dict[str, bool]:
    """Readiness check for Kubernetes."""
    database_ready = await _check_database_health()
    return {"ready": database_ready}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8"
    )


# Include API routers with error handling
try:
    from src.ecc.interfaces.api import ai_analysis, auth, journals, manuscripts, tasks, users

    # Public auth routes
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

    # Require authentication for all other API routes
    require_auth = [Depends(auth.get_current_user)]
    app.include_router(
        manuscripts.router,
        prefix="/api/manuscripts",
        tags=["Manuscripts"],
        dependencies=require_auth,
    )
    # Journals metadata is safe to expose read-only without auth (used by UI bootstrap/tests)
    app.include_router(journals.router, prefix="/api/journals", tags=["Journals"])
    app.include_router(
        ai_analysis.router,
        prefix="/api/ai",
        tags=["AI Analysis"],
        dependencies=require_auth,
    )
    app.include_router(
        users.router,
        prefix="/api/users",
        tags=["Users"],
        dependencies=require_auth,
    )
    app.include_router(
        tasks.router,
        prefix="/api/tasks",
        tags=["Tasks"],
        dependencies=require_auth,
    )

except ImportError as e:
    logger.warning("Could not import API routers: %s", e)
    # Create placeholder routers
    auth = manuscripts = journals = ai_analysis = None


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(status_code=404, content={"detail": "Resource not found"})


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


async def _check_database_health() -> bool:
    """Check database connection health."""
    try:
        from src.ecc.infrastructure.database.connection import get_database_manager

        db = await get_database_manager()
        return await db.health_check()
    except Exception:
        return False


async def _check_cache_health() -> bool:
    """Check Redis cache health."""
    try:
        # TODO: Implement actual cache health check (ping Redis)
        return True
    except Exception:
        return False


async def _check_ai_service_health() -> bool:
    """Check AI service availability."""
    try:
        # TODO: Implement actual AI service health check
        return True
    except Exception:
        return False


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "ecc.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True,
    )
