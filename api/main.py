"""FastAPI application main module."""

import logging
import threading
import tomllib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import entries, search, classifications, stats, pipeline, files, summarize, sources, admin, icd11, references, pubmed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _startup_reconcile() -> None:
    """Run a full reconcile after boot (background thread, non-blocking)."""
    import time

    time.sleep(2.0)  # let the API finish serving first
    from api.database import SessionLocal
    from api.services.file_sync import FileSyncService

    db = SessionLocal()
    try:
        result = FileSyncService(db).run_sync(dry_run=False)
        logger.info(
            f"Startup reconcile done — imported: {result.imported}, "
            f"updated: {result.updated}, deleted: {result.deleted}, "
            f"errors: {len(result.errors)}"
        )
    except Exception as e:
        logger.error(f"Startup reconcile failed: {e}", exc_info=True)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start/stop the SourceWatcher and reconcile."""
    # Startup
    watcher = None
    try:
        from api.services.source_watcher import SourceWatcher

        watcher = SourceWatcher()
        watcher.start()
        logger.info("SourceWatcher started — monitoring source folders for changes")
    except Exception as e:
        logger.warning(f"SourceWatcher failed to start: {e}. Manual sync still available.")

    threading.Thread(
        target=_startup_reconcile, name="startup-reconcile", daemon=True
    ).start()

    yield

    # Shutdown
    if watcher:
        watcher.stop()
        logger.info("SourceWatcher stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Medizinische Wissensdatenbank API",
        version=settings.api_version,
        description="REST-API für die medizinische Wissensdatenbank",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(entries.router, prefix=f"/api/{settings.api_version}")
    app.include_router(search.router, prefix=f"/api/{settings.api_version}")
    app.include_router(classifications.router, prefix=f"/api/{settings.api_version}")
    app.include_router(stats.router, prefix=f"/api/{settings.api_version}")
    app.include_router(pipeline.router, prefix=f"/api/{settings.api_version}")
    app.include_router(files.router, prefix=f"/api/{settings.api_version}")
    app.include_router(summarize.router, prefix=f"/api/{settings.api_version}")
    app.include_router(sources.router, prefix=f"/api/{settings.api_version}")
    app.include_router(admin.router, prefix=f"/api/{settings.api_version}")
    app.include_router(icd11.router, prefix=f"/api/{settings.api_version}")
    app.include_router(references.router, prefix=f"/api/{settings.api_version}")
    app.include_router(pubmed.router, prefix=f"/api/{settings.api_version}")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get(f"/api/{settings.api_version}/version")
    async def version_info():
        """Release version (single source: pyproject.toml [project].version)."""
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        version = tomllib.loads(pyproject.read_text())["project"]["version"]
        return {"project": "medwiss-db", "version": version}

    return app


app = create_app()
