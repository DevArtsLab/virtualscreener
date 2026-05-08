"""
Protein processing with BioPython.
Parses PDB files, extracts binding pocket residues,
computes pocket centroid and box dimensions for AutoDock Vina.
"""
from __future__ import annotations

import io
import logging
from typing import Optional

import numpy as np
from Bio import PDB
from Bio.PDB import PDBParser, PDBIO, Select
from Bio.PDB.Structure import Structure

from app.schemas.models import PocketInfo

logger = logging.getLogger(__name__)

_HYDROPHOBIC = {"ALA", "VAL", "LEU", "ILE", "PHE", "TRP", "MET", "PRO"}
_POLAR = {"SER", "THR", "CYS", "TYR", "ASN", "GLN"}
_CHARGED_POS = {"ARG", "LYS", "HIS"}
_CHARGED_NEG = {"ASP", "GLU"}


def parse_pdb(pdb_bytes: bytes, structure_id: str = "protein") -> Structure:
    parser = PDBParser(QUIET=True)
    handle = io.StringIO(pdb_bytes.decode("utf-8", errors="replace"))
    return parser.get_structure(structure_id, handle)


def extract_pocket_residues(
    structure: Structure,
    ligand_residue_names: Optional[list[str]] = None,
    cutoff_angstrom: float = 6.5,
) -> list[PDB.Residue.Residue]:
    """
    If ligand residue names are provided, find protein residues within
    `cutoff_angstrom` of any ligand atom.
    Otherwise, fall back to selecting the top-10 surface-exposed residues
    by B-factor (a coarse proxy for flexibility / binding site).
    """
    model = structure[0]
    residues = list(model.get_residues())
    protein_residues = [
        r for r in residues
        if r.get_id()[0] == " " and r.resname not in ("HOH", "WAT")
    ]

    # --- ligand-guided pocket detection ---
    if ligand_residue_names:
        ligand_atoms = [
            atom
            for r in residues
            if r.resname in ligand_residue_names
            for atom in r.get_atoms()
        ]
        if ligand_atoms:
            pocket = []
            for res in protein_residues:
                for res_atom in res.get_atoms():
                    for lig_atom in ligand_atoms:
                        if res_atom - lig_atom < cutoff_angstrom:
                            pocket.append(res)
                            break
                    else:
                        continue
                    break
            if pocket:
                return pocket

    # --- fallback: top B-factor residues (surface-exposed proxy) ---
    def mean_bfactor(res):
        bfs = [a.get_bfactor() for a in res.get_atoms()]
        return float(np.mean(bfs)) if bfs else 0.0

    protein_residues_sorted = sorted(
        protein_residues, key=mean_bfactor, reverse=True
    )
    return protein_residues_sorted[:30]


def compute_pocket_box(
    pocket_residues: list[PDB.Residue.Residue],
    padding: float = 5.0,
) -> PocketInfo:
    coords = np.array(
        [atom.get_coord() for r in pocket_residues for atom in r.get_atoms()]
    )
    center = coords.mean(axis=0)
    span = coords.max(axis=0) - coords.min(axis=0) + 2 * padding

    residue_list = [
        f"{r.resname}{r.get_id()[1]}" for r in pocket_residues
    ]

    return PocketInfo(
        center_x=float(round(center[0], 3)),
        center_y=float(round(center[1], 3)),
        center_z=float(round(center[2], 3)),
        size_x=float(round(max(span[0], 15.0), 3)),
        size_y=float(round(max(span[1], 15.0), 3)),
        size_z=float(round(max(span[2], 15.0), 3)),
        n_residues=len(pocket_residues),
        residue_list=residue_list,
    )


def pocket_feature_vector(
    pocket_residues: list[PDB.Residue.Residue],
) -> list[float]:
    """
    Returns a 6-element pocket descriptor used as global context for Chemprop:
    [n_residues, frac_hydrophobic, frac_polar, frac_pos_charged,
     frac_neg_charged, mean_bfactor_norm]
    """
    names = [r.resname for r in pocket_residues]
    n = len(names) or 1
    frac_hydrophobic = sum(1 for x in names if x in _HYDROPHOBIC) / n
    frac_polar = sum(1 for x in names if x in _POLAR) / n
    frac_pos = sum(1 for x in names if x in _CHARGED_POS) / n
    frac_neg = sum(1 for x in names if x in _CHARGED_NEG) / n

    all_bfactors = [
        a.get_bfactor()
        for r in pocket_residues
        for a in r.get_atoms()
    ]
    mean_bf = float(np.mean(all_bfactors)) / 100.0 if all_bfactors else 0.0

    return [float(n) / 100.0, frac_hydrophobic, frac_polar, frac_pos, frac_neg, mean_bf]


def write_clean_pdb(structure: Structure) -> str:
    """Return PDB string with HETATM (ligands/solvent) removed."""

    class ProteinOnly(Select):
        def accept_residue(self, residue):
            return residue.get_id()[0] == " "

    buf = io.StringIO()
    io_writer = PDBIO()
    io_writer.set_structure(structure)
    io_writer.save(buf, ProteinOnly())
    return buf.getvalue()
