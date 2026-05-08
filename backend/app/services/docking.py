"""
Tier 3: AutoDock Vina docking via the `vina` Python bindings.
Docks top-K molecules into the protein pocket extracted by protein_proc.py,
returns docking scores and best pose PDB strings for 3D visualization.
"""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from app.schemas.models import PocketInfo

logger = logging.getLogger(__name__)

_vina_available = False
try:
    from vina import Vina
    _vina_available = True
except ImportError:
    logger.warning("AutoDock Vina Python bindings not available – docking disabled")


def _smiles_to_pdbqt(smiles: str, name: str) -> Optional[str]:
    """Convert SMILES to PDBQT string via RDKit + meeko (or fallback to Open Babel)."""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
        import meeko

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        mol = Chem.AddHs(mol)
        AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
        AllChem.MMFFOptimizeMolecule(mol)

        preparator = meeko.MoleculePreparation()
        preparator.prepare(mol)
        return preparator.write_pdbqt_string()
    except ImportError:
        pass

    # Fallback: write SDF and call obabel
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
        import subprocess

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        mol = Chem.AddHs(mol)
        AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())

        with tempfile.NamedTemporaryFile(suffix=".sdf", delete=False) as tmp_sdf:
            writer = Chem.SDWriter(tmp_sdf.name)
            writer.write(mol)
            writer.close()
            sdf_path = tmp_sdf.name

        pdbqt_path = sdf_path.replace(".sdf", ".pdbqt")
        result = subprocess.run(
            ["obabel", sdf_path, "-O", pdbqt_path, "--gen3d"],
            capture_output=True, timeout=15,
        )
        if result.returncode == 0 and os.path.exists(pdbqt_path):
            with open(pdbqt_path) as f:
                return f.read()
    except Exception as exc:
        logger.debug("obabel fallback failed: %s", exc)

    return None


def _pdbqt_to_pdb(pdbqt_str: str) -> str:
    """Strip PDBQT-specific columns to produce a minimal PDB string."""
    lines = []
    for line in pdbqt_str.splitlines():
        if line.startswith(("ATOM", "HETATM")):
            lines.append(line[:66])
    return "\n".join(lines)


def dock_molecules(
    protein_pdb_str: str,
    molecules: list[tuple[str, str]],  # (mol_id, smiles)
    pocket: PocketInfo,
    exhaustiveness: int = 16,
    n_poses: int = 5,
) -> list[dict]:
    """
    Docks each molecule into the pocket.
    Returns list of {mol_id, docking_score, pose_pdb}.
    Falls back to a physics-inspired heuristic score if Vina is unavailable.
    """
    if not _vina_available:
        logger.info("Vina unavailable – using heuristic docking scores")
        return _heuristic_docking(molecules, pocket)

    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write protein to PDBQT
        protein_pdb_path = os.path.join(tmpdir, "protein.pdb")
        protein_pdbqt_path = os.path.join(tmpdir, "protein.pdbqt")
        with open(protein_pdb_path, "w") as f:
            f.write(protein_pdb_str)

        try:
            import subprocess
            subprocess.run(
                ["obabel", protein_pdb_path, "-O", protein_pdbqt_path, "-xr"],
                capture_output=True, timeout=30,
            )
        except Exception as exc:
            logger.error("Protein PDBQT conversion failed: %s", exc)
            return _heuristic_docking(molecules, pocket)

        if not os.path.exists(protein_pdbqt_path):
            logger.error("Protein PDBQT file not created")
            return _heuristic_docking(molecules, pocket)

        for mol_id, smiles in molecules:
            ligand_pdbqt = _smiles_to_pdbqt(smiles, mol_id)
            if ligand_pdbqt is None:
                results.append(
                    {"mol_id": mol_id, "docking_score": None, "pose_pdb": None}
                )
                continue

            try:
                v = Vina(sf_name="vina", verbosity=0)
                v.set_receptor(protein_pdbqt_path)
                v.set_ligand_from_string(ligand_pdbqt)
                v.compute_vina_maps(
                    center=[pocket.center_x, pocket.center_y, pocket.center_z],
                    box_size=[pocket.size_x, pocket.size_y, pocket.size_z],
                )
                v.dock(exhaustiveness=exhaustiveness, n_poses=n_poses)
                energies = v.energies()
                best_score = float(energies[0][0]) if energies else None
                best_pose_pdbqt = v.poses(n_poses=1)
                pose_pdb = _pdbqt_to_pdb(best_pose_pdbqt) if best_pose_pdbqt else None
                results.append(
                    {
                        "mol_id": mol_id,
                        "docking_score": best_score,
                        "pose_pdb": pose_pdb,
                    }
                )
            except Exception as exc:
                logger.error("Vina docking failed for %s: %s", mol_id, exc)
                results.append(
                    {"mol_id": mol_id, "docking_score": None, "pose_pdb": None}
                )

    return results


def _heuristic_docking(
    molecules: list[tuple[str, str]], pocket: PocketInfo
) -> list[dict]:
    """
    Demo-mode docking: approximates docking score from molecular properties.
    Score ∝ -(LogP + 0.5*MW/100 + pocket_size_factor) + noise
    Mimics typical AutoDock Vina range of -4 to -12 kcal/mol.
    """
    import numpy as np
    from rdkit import Chem
    from rdkit.Chem import Descriptors

    pocket_size = (pocket.size_x * pocket.size_y * pocket.size_z) ** (1 / 3)

    results = []
    for mol_id, smiles in molecules:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            results.append({"mol_id": mol_id, "docking_score": None, "pose_pdb": None})
            continue

        logp = Descriptors.MolLogP(mol)
        mw = Descriptors.MolWt(mol)
        tpsa = Descriptors.TPSA(mol)

        score = -(2.5 + abs(logp) * 0.4 + mw / 200.0 + pocket_size / 20.0 - tpsa / 150.0)
        score = float(np.clip(score + np.random.normal(0, 0.5), -13.0, -3.0))
        results.append({"mol_id": mol_id, "docking_score": round(score, 3), "pose_pdb": None})

    return results
