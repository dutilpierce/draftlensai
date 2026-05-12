from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from draftlens_api.config import get_settings
from draftlens_api.db import get_db_session, init_db
from draftlens_api.routes import access, billing, cloud_storage, disclaimers, health, jobs
from draftlens_api.services.paths import DataPaths
from draftlens_api.services.retention_service import RetentionService

logger = logging.getLogger(__name__)


async def _retention_sweep_loop() -> None:
    await asyncio.sleep(30)
    while True:
        settings = get_settings()
        interval = max(300, int(settings.retention_sweep_interval_seconds))
        try:
            paths = DataPaths.from_settings(settings)
            db = get_db_session()
            try:
                n = RetentionService(paths).cleanup_eligible_jobs(db)
                if n:
                    logger.info("retention sweep removed filesystem data for %s job(s)", n)
            finally:
                db.close()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("retention sweep failed")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    sweep = asyncio.create_task(_retention_sweep_loop())
    try:
        yield
    finally:
        sweep.cancel()
        try:
            await sweep
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="DraftLens API", version="0.1.0", lifespan=lifespan)

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(access.router, prefix="/api")
    app.include_router(disclaimers.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(cloud_storage.router, prefix="/api")
    app.include_router(billing.router, prefix="/api")
    return app


app = create_app()
