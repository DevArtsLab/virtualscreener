from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.core.job_store import job_store
from app.schemas.models import JobResponse
from app.services.pipeline import run_screening_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/screen", tags=["screening"])


@router.post("", response_model=JobResponse, status_code=202)
async def submit_screening_job(
    background_tasks: BackgroundTasks,
    protein_file: UploadFile = File(..., description="Protein structure in PDB format"),
    library_file: UploadFile = File(
        ..., description="Compound library as SMILES (.smi/.txt) or SDF (.sdf)"
    ),
    top_k: int = Form(default=10, ge=1, le=100),
) -> JobResponse:
    """
    Submit a virtual screening job.
    Returns immediately with a job_id; poll /api/jobs/{job_id} for status.
    """
    # Validate file extensions
    pdb_name = protein_file.filename or "protein.pdb"
    lib_name = library_file.filename or "library.smi"

    if not pdb_name.lower().endswith(".pdb"):
        raise HTTPException(
            status_code=400,
            detail="Protein file must be in PDB format (.pdb)",
        )

    allowed_lib_exts = {".smi", ".txt", ".csv", ".sdf"}
    lib_ext = Path(lib_name).suffix.lower()
    if lib_ext not in allowed_lib_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Library file must be one of: {', '.join(allowed_lib_exts)}",
        )

    protein_bytes = await protein_file.read()
    library_bytes = await library_file.read()

    if len(protein_bytes) == 0:
        raise HTTPException(status_code=400, detail="Protein file is empty")
    if len(library_bytes) == 0:
        raise HTTPException(status_code=400, detail="Library file is empty")

    job_id = await job_store.create(pdb_name, lib_name, top_k)

    background_tasks.add_task(
        run_screening_pipeline,
        job_id=job_id,
        protein_bytes=protein_bytes,
        library_bytes=library_bytes,
        library_filename=lib_name,
        top_k=top_k,
    )

    job = await job_store.get(job_id)
    return job
