"""Main FastAPI application entry point for FreshRoute AI.

Configures CORS, lifespan events, API routers, and global error handlers.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle management."""
    init_db()
    yield


app = FastAPI(
    title="FreshRoute AI - Perishable Produce Allocation Engine",
    description=(
        "Production-grade constraint-aware decision-support backend for perishable "
        "agricultural produce distribution across Indian wholesale mandis."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration for Frontend (Vite on localhost, Netlify, and custom domains)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.netlify\.app|https://.*\.vercel\.app|http://localhost:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pathlib import Path
from fastapi.staticfiles import StaticFiles

# Mount API routers
app.include_router(api_router, prefix=settings.API_V1_STR)

dist_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if dist_path.exists():
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="frontend")
else:
    @app.get("/", tags=["System"])
    def root():
        """Root entry point providing service metadata and documentation links."""
        return {
            "service": "FreshRoute AI Decision-Support Platform",
            "status": "online",
            "version": settings.VERSION,
            "docs_url": "/docs",
            "api_v1_base": settings.API_V1_STR,
        }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Fallback handler for unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": str(exc),
            "path": str(request.url),
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
