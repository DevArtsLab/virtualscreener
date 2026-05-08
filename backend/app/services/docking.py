"""
Tier 3: AutoDock Vina docking via the system `vina` binary (installed via apt).
Docks top-K molecules into the protein pocket extracted by protein_proc.py,
returns docking scores and best pose PDB strings for 3D visualization.
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app.schemas.models import PocketInfo

logger = logging.getLogger(__name__)


def _vina_binary() -> Optional[str]:
    """Return path to vina binary if available, else None."""
    for candidate in ["vina", "/usr/bin/vina", "/usr/local/bin/vina"]:
        try:
            r = subprocess.run([candidate, "--version"], capture_output=True, timeout=5)
            if r.returncode == 0:
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


_VINA_BIN = _vina_binary()
if _VINA_BIN:
    logger.info("AutoDock Vina binary found: %s", _VINA_BIN)
else:
    logger.warning("AutoDock Vina binary not found – docking will use heuristic fallback")


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
    if not _VINA_BIN:
        logger.info("Vina binary unavailable – using heuristic docking scores")
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
                lig_pdbqt_path = os.path.join(tmpdir, f"{mol_id}_lig.pdbqt")
                out_pdbqt_path = os.path.join(tmpdir, f"{mol_id}_out.pdbqt")
                with open(lig_pdbqt_path, "w") as f:
                    f.write(ligand_pdbqt)

                cmd = [
                    _VINA_BIN,
                    "--receptor", protein_pdbqt_path,
                    "--ligand", lig_pdbqt_path,
                    "--out", out_pdbqt_path,
                    "--center_x", str(pocket.center_x),
                    "--center_y", str(pocket.center_y),
                    "--center_z", str(pocket.center_z),
                    "--size_x", str(pocket.size_x),
                    "--size_y", str(pocket.size_y),
                    "--size_z", str(pocket.size_z),
                    "--exhaustiveness", str(exhaustiveness),
                    "--num_modes", str(n_poses),
                    "--cpu", "1",
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

                best_score = None
                pose_pdb = None
                if proc.returncode == 0 and os.path.exists(out_pdbqt_path):
                    with open(out_pdbqt_path) as f:
                        out_pdbqt = f.read()
                    pose_pdb = _pdbqt_to_pdb(out_pdbqt)
                    for line in proc.stdout.splitlines():
                        if line.strip().startswith("1 "):
                            parts = line.split()
                            if len(parts) >= 2:
                                try:
                                    best_score = float(parts[1])
                                except ValueError:
                                    pass
                            break
                else:
                    logger.debug("Vina stderr for %s: %s", mol_id, proc.stderr[:300])

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
