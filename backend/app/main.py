from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import jobs, molecules, screening

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
