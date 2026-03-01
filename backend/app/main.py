from fastapi import FastAPI
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.limiter import limiter
from app.config import settings
from app.auth.router import router as auth_router
from app.auth.reset_router import router as reset_router
from app.logs_router import router as logs_router
from app.auth.google_router import router as google_router
from app.auth.totp_router import router as totp_router
from app.admin.router import router as admin_router
from app.hosts.router import router as hosts_router
from app.views.router import router as views_router

app = FastAPI(
    title="HomeMatrix API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(reset_router, prefix="/api/auth", tags=["reset"])
app.include_router(google_router, prefix="/api/auth", tags=["google"])
app.include_router(totp_router, prefix="/api/auth/2fa", tags=["2fa"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(hosts_router, prefix="/api/hosts", tags=["hosts"])
app.include_router(views_router, prefix="/api", tags=["views"])
app.include_router(logs_router, prefix="/api", tags=["logs"])

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
