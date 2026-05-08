from __future__ import annotations

import csv
import io
import math
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from app.core.job_store import job_store
from app.schemas.models import MoleculeResult, ScreeningResults

router = APIRouter(prefix="/molecules", tags=["molecules"])


@router.get("/{job_id}", response_model=ScreeningResults)
async def get_results(
    job_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    only_passed: bool = Query(default=True),
    sort_by: str = Query(default="rank"),
    sort_asc: bool = Query(default=True),
) -> ScreeningResults:
    """
    Retrieve paginated results for a completed screening job.
    Set only_passed=false to also include filtered-out molecules.
    """
    job = await job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    results = await job_store.get_results(job_id)
    if results is None:
        raise HTTPException(
            status_code=404,
            detail="Results not yet available. Check job status.",
        )

    # Filter
    if only_passed:
        display = [m for m in results if not m.filtered_out]
    else:
        display = list(results)

    # Sort
    sort_fields = {
        "rank": lambda m: m.rank,
        "ensemble_score": lambda m: m.ensemble_score or 0.0,
        "docking_score": lambda m: m.docking_score or 0.0,
        "predicted_pic50": lambda m: m.predicted_pic50 or 0.0,
        "mw": lambda m: (m.lipinski.mw if m.lipinski else 0.0),
        "logp": lambda m: (m.lipinski.logp if m.lipinski else 0.0),
    }
    key_fn = sort_fields.get(sort_by, sort_fields["rank"])
    display.sort(key=key_fn, reverse=not sort_asc)

    # Paginate
    total = len(display)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    end = start + page_size
    page_items = display[start:end]

    passed = [m for m in results if not m.filtered_out]
    docked = [m for m in results if m.docking_score is not None]

    return ScreeningResults(
        job_id=job_id,
        total_molecules=len(results),
        passed_tier1=len(passed),
        passed_tier2=len([m for m in passed if m.ensemble_score is not None]),
        docked_molecules=len(docked),
        results=page_items,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{job_id}/{mol_id}/pose")
async def get_pose(job_id: str, mol_id: str) -> Response:
    """Return docking pose PDB string for NGL viewer."""
    pose = await job_store.get_pose(job_id, mol_id)
    if pose is None:
        raise HTTPException(
            status_code=404, detail="No docking pose available for this molecule"
        )
    return Response(content=pose, media_type="chemical/x-pdb")


@router.get("/{job_id}/export/csv")
async def export_csv(job_id: str) -> StreamingResponse:
    """Download all results as CSV."""
    results = await job_store.get_results(job_id)
    if results is None:
        raise HTTPException(status_code=404, detail="No results for this job")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "rank", "mol_id", "name", "smiles",
            "predicted_pic50", "pic50_uncertainty", "deepchem_score",
            "ensemble_score", "docking_score",
            "mw", "logp", "hbd", "hba", "tpsa", "rotatable_bonds",
            "passes_ro5", "passes_pains", "filtered_out", "filter_reason",
        ]
    )
    for m in sorted(results, key=lambda x: x.rank):
        lip = m.lipinski
        writer.writerow(
            [
                m.rank, m.mol_id, m.name, m.smiles,
                m.predicted_pic50, m.pic50_uncertainty, m.deepchem_score,
                m.ensemble_score, m.docking_score,
                lip.mw if lip else "", lip.logp if lip else "",
                lip.hbd if lip else "", lip.hba if lip else "",
                lip.tpsa if lip else "", lip.rotatable_bonds if lip else "",
                lip.passes_ro5 if lip else "", lip.passes_pains if lip else "",
                m.filtered_out, m.filter_reason,
            ]
        )

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="results_{job_id}.csv"'},
    )
