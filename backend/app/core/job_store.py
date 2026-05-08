"""
In-memory job store with thread-safe access.
Stores job metadata, results, and pose data.
Upgradeable to Redis by replacing this module.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.schemas.models import JobResponse, JobStatus, MoleculeResult


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self) -> None:
        self._jobs: Dict[str, dict] = {}
        self._results: Dict[str, list[MoleculeResult]] = {}
        self._poses: Dict[str, Dict[str, str]] = {}  # job_id -> mol_id -> pdb string
        self._lock = asyncio.Lock()

    async def create(
        self, protein_filename: str, library_filename: str, top_k: int
    ) -> str:
        job_id = str(uuid.uuid4())
        async with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": JobStatus.queued,
                "progress": 0.0,
                "current_stage": "Queued",
                "molecules_total": 0,
                "molecules_processed": 0,
                "error_message": None,
                "protein_filename": protein_filename,
                "library_filename": library_filename,
                "top_k": top_k,
                "created_at": _now(),
                "updated_at": _now(),
            }
        return job_id

    async def update(self, job_id: str, **kwargs: Any) -> None:
        async with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Job {job_id} not found")
            self._jobs[job_id].update(kwargs)
            self._jobs[job_id]["updated_at"] = _now()

    async def get(self, job_id: str) -> Optional[JobResponse]:
        async with self._lock:
            data = self._jobs.get(job_id)
        if data is None:
            return None
        return JobResponse(**data)

    async def set_results(
        self, job_id: str, results: list[MoleculeResult]
    ) -> None:
        async with self._lock:
            self._results[job_id] = results

    async def get_results(self, job_id: str) -> Optional[list[MoleculeResult]]:
        async with self._lock:
            return self._results.get(job_id)

    async def set_pose(self, job_id: str, mol_id: str, pdb_str: str) -> None:
        async with self._lock:
            if job_id not in self._poses:
                self._poses[job_id] = {}
            self._poses[job_id][mol_id] = pdb_str

    async def get_pose(self, job_id: str, mol_id: str) -> Optional[str]:
        async with self._lock:
            return self._poses.get(job_id, {}).get(mol_id)

    def get_job_meta(self, job_id: str) -> Optional[dict]:
        """Synchronous read for pipeline workers."""
        return self._jobs.get(job_id)


job_store = JobStore()
