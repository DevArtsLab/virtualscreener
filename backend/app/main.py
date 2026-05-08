from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.config import settings
from app.routers import jobs, molecules, screening
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VirtualScreener API starting up")
    # Warm up ML scorer at startup
    from app.services.ml_scoring import get_scorer

    get_scorer(
        chemprop_checkpoint=settings.chemprop_checkpoint,
        deepchem_model_dir=settings.deepchem_model_dir,
    )
    yield
    logger.info("VirtualScreener API shutting down")


app = FastAPI(
    title="VirtualScreener API",
    description=(
        "AI-powered virtual screening platform: "
        "3-tier pipeline (RDKit Tier1 → Chemprop+DeepChem Tier2 → AutoDock Vina Tier3)"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(screening.router, prefix=settings.api_prefix)
app.include_router(jobs.router, prefix=settings.api_prefix)
app.include_router(molecules.router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


# ── Hugging Face Spaces: serve built React app as static files ────────────────
_static_dir = Path("/app/static")
if os.getenv("HF_STATIC"):
    if _static_dir.exists():
        app.mount(
            "/assets", StaticFiles(directory=str(_static_dir / "assets")), name="assets"
        )

        @app.get("/", include_in_schema=False)
        async def spa_root():
            return FileResponse(str(_static_dir / "index.html"))

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            candidate = _static_dir / full_path
            if candidate.is_file():
                return FileResponse(str(candidate))
            return FileResponse(str(_static_dir / "index.html"))

    else:
        logger.warning("HF_STATIC set but static dir not found at %s", _static_dir)
