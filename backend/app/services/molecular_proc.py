"""
Tier 1: Molecular processing with RDKit.
Validates SMILES/SDF, applies Lipinski + PAINS filters,
generates Morgan fingerprints, and renders 2D SVGs.
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Optional

from rdkit import Chem
from rdkit.Chem import (
    AllChem,
    Descriptors,
    Draw,
    FilterCatalog,
    rdMolDescriptors,
)
from rdkit.Chem.Draw import rdMolDraw2D
from rdkit.Chem.FilterCatalog import FilterCatalogParams

from app.schemas.models import LipinskiResult, MoleculeResult

logger = logging.getLogger(__name__)

# Build PAINS filter catalog once at module load
_pains_params = FilterCatalogParams()
_pains_params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
PAINS_CATALOG = FilterCatalog.FilterCatalog(_pains_params)


def _mol_from_smiles(smiles: str) -> Optional[Chem.Mol]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
    mol = Chem.RemoveHs(mol)
    return mol


def compute_lipinski(mol: Chem.Mol) -> LipinskiResult:
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    hbd = rdMolDescriptors.CalcNumHBD(mol)
    hba = rdMolDescriptors.CalcNumHBA(mol)
    tpsa = Descriptors.TPSA(mol)
    rot = rdMolDescriptors.CalcNumRotatableBonds(mol)
    passes_ro5 = mw <= 500 and logp <= 5 and hbd <= 5 and hba <= 10
    passes_pains = not bool(PAINS_CATALOG.GetMatches(mol))
    return LipinskiResult(
        mw=round(mw, 2),
        logp=round(logp, 3),
        hbd=hbd,
        hba=hba,
        tpsa=round(tpsa, 2),
        rotatable_bonds=rot,
        passes_ro5=passes_ro5,
        passes_pains=passes_pains,
    )


def render_svg_2d(mol: Chem.Mol, width: int = 300, height: int = 200) -> str:
    """Returns an SVG string for the molecule's 2D depiction."""
    mol_2d = Chem.RWMol(mol)
    AllChem.Compute2DCoords(mol_2d)
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    drawer.drawOptions().addStereoAnnotation = True
    drawer.DrawMolecule(mol_2d)
    drawer.FinishDrawing()
    return drawer.GetDrawingText()


def morgan_fingerprint(mol: Chem.Mol, radius: int = 2, n_bits: int = 2048) -> list[int]:
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
    return list(fp.ToBitString())


def parse_smiles_input(content: str) -> list[tuple[str, str]]:
    """
    Parse newline-delimited SMILES content.
    Accepts:
      - bare SMILES: one per line
      - SMILES<tab|space>name format
    Returns list of (smiles, name).
    """
    entries: list[tuple[str, str]] = []
    for i, line in enumerate(content.splitlines()):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        smiles = parts[0]
        name = parts[1] if len(parts) > 1 else f"mol_{i:05d}"
        entries.append((smiles, name))
    return entries


def parse_sdf_input(content: bytes) -> list[tuple[str, str]]:
    """Parse SDF bytes, return list of (smiles, name)."""
    supplier = Chem.ForwardSDMolSupplier(io.BytesIO(content), removeHs=False)
    entries: list[tuple[str, str]] = []
    for i, mol in enumerate(supplier):
        if mol is None:
            continue
        smiles = Chem.MolToSmiles(mol)
        name = mol.GetProp("_Name") if mol.HasProp("_Name") else f"mol_{i:05d}"
        entries.append((smiles, name.strip() or f"mol_{i:05d}"))
    return entries


def run_tier1(
    entries: list[tuple[str, str]],
) -> tuple[list[MoleculeResult], list[MoleculeResult]]:
    """
    Returns (passed, filtered_out) lists of MoleculeResult.
    Passed molecules have lipinski, svg_2d populated.
    """
    passed: list[MoleculeResult] = []
    filtered: list[MoleculeResult] = []

    for idx, (smiles, name) in enumerate(entries):
        mol_id = f"mol_{idx:06d}"
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            filtered.append(
                MoleculeResult(
                    mol_id=mol_id,
                    name=name,
                    smiles=smiles,
                    rank=0,
                    filtered_out=True,
                    filter_reason="Invalid SMILES",
                )
            )
            continue

        lip = compute_lipinski(mol)
        svg = render_svg_2d(mol)

        if not lip.passes_ro5:
            filtered.append(
                MoleculeResult(
                    mol_id=mol_id,
                    name=name,
                    smiles=smiles,
                    rank=0,
                    lipinski=lip,
                    svg_2d=svg,
                    filtered_out=True,
                    filter_reason="Failed Lipinski Ro5",
                )
            )
            continue

        if not lip.passes_pains:
            filtered.append(
                MoleculeResult(
                    mol_id=mol_id,
                    name=name,
                    smiles=smiles,
                    rank=0,
                    lipinski=lip,
                    svg_2d=svg,
                    filtered_out=True,
                    filter_reason="PAINS alert",
                )
            )
            continue

        passed.append(
            MoleculeResult(
                mol_id=mol_id,
                name=name,
                smiles=smiles,
                rank=0,
                lipinski=lip,
                svg_2d=svg,
            )
        )

    return passed, filtered
