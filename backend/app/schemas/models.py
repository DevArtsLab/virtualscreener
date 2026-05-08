from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    tier1 = "tier1"
    tier2 = "tier2"
    tier3 = "tier3"
    done = "done"
    error = "error"


class LipinskiResult(BaseModel):
    mw: float = Field(..., description="Molecular weight (Da)")
    logp: float = Field(..., description="Calculated LogP")
    hbd: int = Field(..., description="H-bond donors")
    hba: int = Field(..., description="H-bond acceptors")
    tpsa: float = Field(..., description="Topological polar surface area (Å²)")
    rotatable_bonds: int
    passes_ro5: bool
    passes_pains: bool


class MoleculeResult(BaseModel):
    mol_id: str
    name: str
    smiles: str
    rank: int
    predicted_pic50: Optional[float] = None
    pic50_uncertainty: Optional[float] = None
    deepchem_score: Optional[float] = None
    ensemble_score: Optional[float] = None
    docking_score: Optional[float] = None
    has_pose: bool = False
    lipinski: Optional[LipinskiResult] = None
    svg_2d: Optional[str] = None
    filtered_out: bool = False
    filter_reason: Optional[str] = None


class JobCreate(BaseModel):
    protein_filename: str
    library_filename: str
    top_k: int = Field(default=10, ge=1, le=100)


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    current_stage: str = ""
    molecules_total: int = 0
    molecules_processed: int = 0
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


class ScreeningResults(BaseModel):
    job_id: str
    total_molecules: int
    passed_tier1: int
    passed_tier2: int
    docked_molecules: int
    results: list[MoleculeResult]
    page: int
    page_size: int
    total_pages: int


class PocketInfo(BaseModel):
    center_x: float
    center_y: float
    center_z: float
    size_x: float
    size_y: float
    size_z: float
    n_residues: int
    residue_list: list[str]
