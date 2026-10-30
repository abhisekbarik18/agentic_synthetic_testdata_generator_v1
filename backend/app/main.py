"""
FastAPI application entry point.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.config import settings
from app.database import init_db
from app.utils.logging_config import get_logger, setup_logging

# Configure logging
setup_logging(debug=settings.DEBUG)
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger.info("Initializing %s backend...", settings.APP_NAME)

    # Ensure export directory exists
    Path(settings.EXPORT_DIR).mkdir(parents=True, exist_ok=True)

    # Initialize SQLite or Postgres tables
    init_db()
    logger.info("Database initialized successfully at %s", settings.DATABASE_URL)

    yield

    logger.info("Shutting down %s backend.", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Agentic LLM-Powered Test Data Simulator with LangGraph & Multi-Format Natural-Language Export",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "export_dir": settings.EXPORT_DIR,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
