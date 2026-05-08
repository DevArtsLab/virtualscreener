from __future__ import annotations

from fastapi import APIRouter, HTTPException
from app.core.job_store import job_store
from app.schemas.models import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str) -> JobResponse:
    """Poll the status and progress of a screening job."""
    job = await job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job
