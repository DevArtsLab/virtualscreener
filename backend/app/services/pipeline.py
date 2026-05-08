"""
Main screening pipeline orchestrator.
Coordinates Tier 1 → Tier 2 → Tier 3 and writes progress to the job store.
Designed to run in a background asyncio task.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.core.config import settings
from app.core.job_store import job_store
from app.schemas.models import JobStatus, MoleculeResult
from app.services.docking import dock_molecules
from app.services.ml_scoring import get_scorer
from app.services.molecular_proc import (
    parse_sdf_input,
    parse_smiles_input,
    run_tier1,
)
from app.services.protein_proc import (
    compute_pocket_box,
    extract_pocket_residues,
    parse_pdb,
    pocket_feature_vector,
    write_clean_pdb,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 256  # Tier 2 batch size for ML scoring


async def run_screening_pipeline(
    job_id: str,
    protein_bytes: bytes,
    library_bytes: bytes,
    library_filename: str,
    top_k: int,
) -> None:
    """
    Full 3-tier pipeline. Updates job_store throughout.
    """
    try:
        await _pipeline(
            job_id, protein_bytes, library_bytes, library_filename, top_k
        )
    except Exception as exc:
        logger.exception("Pipeline failed for job %s", job_id)
        await job_store.update(
            job_id,
            status=JobStatus.error,
            error_message=str(exc),
            progress=0.0,
        )


async def _pipeline(
    job_id: str,
    protein_bytes: bytes,
    library_bytes: bytes,
    library_filename: str,
    top_k: int,
) -> None:

    # ── Parse protein ────────────────────────────────────────────────────────
    await job_store.update(
        job_id,
        status=JobStatus.tier1,
        current_stage="Parsing protein structure",
        progress=2.0,
    )
    structure = await asyncio.get_event_loop().run_in_executor(
        None, parse_pdb, protein_bytes
    )
    pocket_residues = await asyncio.get_event_loop().run_in_executor(
        None, extract_pocket_residues, structure
    )
    pocket_info = await asyncio.get_event_loop().run_in_executor(
        None, compute_pocket_box, pocket_residues
    )
    pocket_features = pocket_feature_vector(pocket_residues)
    clean_protein_pdb = write_clean_pdb(structure)

    # ── Parse compound library ───────────────────────────────────────────────
    await job_store.update(
        job_id,
        current_stage="Parsing compound library",
        progress=6.0,
    )
    if library_filename.lower().endswith(".sdf"):
        entries = await asyncio.get_event_loop().run_in_executor(
            None, parse_sdf_input, library_bytes
        )
    else:
        content = library_bytes.decode("utf-8", errors="replace")
        entries = await asyncio.get_event_loop().run_in_executor(
            None, parse_smiles_input, content
        )

    total = len(entries)
    if total == 0:
        raise ValueError("No valid molecules found in compound library")
    if total > settings.max_molecules:
        entries = entries[: settings.max_molecules]
        total = settings.max_molecules

    await job_store.update(
        job_id,
        molecules_total=total,
        current_stage=f"Tier 1: filtering {total} molecules",
        progress=10.0,
    )

    # ── Tier 1: Lipinski + PAINS ─────────────────────────────────────────────
    passed, filtered_out = await asyncio.get_event_loop().run_in_executor(
        None, run_tier1, entries
    )

    await job_store.update(
        job_id,
        molecules_processed=len(passed) + len(filtered_out),
        current_stage=f"Tier 1 done: {len(passed)} passed / {len(filtered_out)} filtered",
        progress=35.0,
    )

    if not passed:
        all_results = sorted(
            filtered_out, key=lambda m: m.mol_id
        )
        await job_store.set_results(job_id, all_results)
        await job_store.update(
            job_id,
            status=JobStatus.done,
            progress=100.0,
            current_stage="Done (all molecules filtered by Tier 1)",
        )
        return

    # ── Tier 2: ML ensemble scoring ──────────────────────────────────────────
    await job_store.update(
        job_id,
        status=JobStatus.tier2,
        current_stage=f"Tier 2: ML scoring {len(passed)} molecules",
        progress=38.0,
    )

    scorer = get_scorer(
        chemprop_checkpoint=settings.chemprop_checkpoint,
        deepchem_model_dir=settings.deepchem_model_dir,
    )

    smiles_batch = [m.smiles for m in passed]
    scores_batch = []

    # Process in batches to allow progress updates
    for batch_start in range(0, len(smiles_batch), BATCH_SIZE):
        batch = smiles_batch[batch_start: batch_start + BATCH_SIZE]
        batch_scores = await asyncio.get_event_loop().run_in_executor(
            None, scorer.score, batch, pocket_features
        )
        scores_batch.extend(batch_scores)
        progress = 38.0 + 42.0 * (batch_start + len(batch)) / len(smiles_batch)
        await job_store.update(
            job_id,
            molecules_processed=batch_start + len(batch),
            progress=round(progress, 1),
        )

    # Attach scores to passed molecules
    for mol, score_dict in zip(passed, scores_batch):
        mol.predicted_pic50 = score_dict["chemprop_pic50"]
        mol.pic50_uncertainty = score_dict["chemprop_uncertainty"]
        mol.deepchem_score = score_dict["deepchem_pic50"]
        mol.ensemble_score = score_dict["ensemble_score"]

    # Rank by ensemble score descending
    passed.sort(key=lambda m: m.ensemble_score or 0.0, reverse=True)
    for rank, mol in enumerate(passed, start=1):
        mol.rank = rank

    # ── Tier 3: AutoDock Vina docking (top-K only) ───────────────────────────
    top_for_docking = passed[:top_k]

    await job_store.update(
        job_id,
        status=JobStatus.tier3,
        current_stage=f"Tier 3: docking top {len(top_for_docking)} molecules",
        progress=82.0,
    )

    docking_inputs = [(m.mol_id, m.smiles) for m in top_for_docking]
    docking_results = await asyncio.get_event_loop().run_in_executor(
        None,
        dock_molecules,
        clean_protein_pdb,
        docking_inputs,
        pocket_info,
        settings.vina_exhaustiveness,
        settings.vina_n_poses,
    )

    docking_map = {r["mol_id"]: r for r in docking_results}

    for mol in top_for_docking:
        dr = docking_map.get(mol.mol_id, {})
        mol.docking_score = dr.get("docking_score")
        pose_pdb = dr.get("pose_pdb")
        if pose_pdb:
            mol.has_pose = True
            await job_store.set_pose(job_id, mol.mol_id, pose_pdb)

    # Re-rank: primary sort by docking score (lower = better) for docked mols,
    # then by ensemble score for the rest
    docked = [m for m in passed if m.docking_score is not None]
    undocked = [m for m in passed if m.docking_score is None]
    docked.sort(key=lambda m: m.docking_score)
    undocked.sort(key=lambda m: m.ensemble_score or 0.0, reverse=True)
    final_ranked = docked + undocked

    for rank, mol in enumerate(final_ranked, start=1):
        mol.rank = rank

    all_results = final_ranked + filtered_out

    await job_store.set_results(job_id, all_results)
    await job_store.update(
        job_id,
        status=JobStatus.done,
        progress=100.0,
        current_stage=(
            f"Complete — {len(docked)} docked, {len(passed)} scored, "
            f"{len(filtered_out)} filtered"
        ),
    )
    logger.info("Job %s completed successfully", job_id)
