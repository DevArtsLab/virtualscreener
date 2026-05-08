"""
Tier 2: ML-based binding affinity scoring.
Chemprop D-MPNN + DeepChem AttentiveFP ensemble.
Outputs predicted pIC50 with MC-Dropout uncertainty.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── lazy imports so the app starts even if GPU packages aren't installed ──────
_chemprop_available = False
_deepchem_available = False

try:
    import chemprop
    from chemprop.data import MoleculeDatapoint, MoleculeDataset, build_dataloader
    from chemprop.models import MPNN
    import torch
    _chemprop_available = True
except ImportError:
    logger.warning("chemprop not available – Chemprop scoring disabled")

try:
    import deepchem as dc
    from deepchem.models import AttentiveFPModel
    _deepchem_available = True
except ImportError:
    logger.warning("deepchem not available – DeepChem scoring disabled")


# ── Chemprop scorer ───────────────────────────────────────────────────────────

class ChempropScorer:
    """Wraps a Chemprop MPNN checkpoint for pIC50 prediction."""

    def __init__(self, checkpoint_path: Optional[Path] = None) -> None:
        self._model: Optional["MPNN"] = None
        self._ready = False
        if checkpoint_path and checkpoint_path.exists() and _chemprop_available:
            self._load(checkpoint_path)

    def _load(self, path: Path) -> None:
        try:
            self._model = MPNN.load_from_file(str(path))
            self._model.eval()
            self._ready = True
            logger.info("Chemprop model loaded from %s", path)
        except Exception as exc:
            logger.error("Failed to load Chemprop model: %s", exc)

    @property
    def ready(self) -> bool:
        return self._ready and _chemprop_available

    def predict(
        self,
        smiles_list: list[str],
        pocket_features: Optional[list[float]] = None,
        n_mc_samples: int = 10,
    ) -> list[tuple[float, float]]:
        """
        Returns list of (predicted_pic50, uncertainty) per SMILES.
        Uses MC-Dropout for uncertainty estimation.
        Falls back to fingerprint-based heuristic if model not ready.
        """
        if not self.ready:
            return self._heuristic_fallback(smiles_list)

        import torch
        from chemprop.data import MoleculeDatapoint, MoleculeDataset, build_dataloader

        datapoints = [MoleculeDatapoint.from_smi(smi) for smi in smiles_list]
        dataset = MoleculeDataset(datapoints)
        loader = build_dataloader(dataset, shuffle=False)

        # MC-Dropout: enable dropout at inference
        self._model.train()
        all_preds = []
        with torch.no_grad():
            for _ in range(n_mc_samples):
                preds = []
                for batch in loader:
                    out = self._model(batch).squeeze(-1).cpu().numpy()
                    preds.extend(out.tolist())
                all_preds.append(preds)

        all_preds_arr = np.array(all_preds)  # (n_mc, n_mols)
        means = all_preds_arr.mean(axis=0)
        stds = all_preds_arr.std(axis=0)
        return [(float(m), float(s)) for m, s in zip(means, stds)]

    def _heuristic_fallback(
        self, smiles_list: list[str]
    ) -> list[tuple[float, float]]:
        """
        Fingerprint-similarity-based pIC50 heuristic used when no model checkpoint
        is available (demo mode). Returns plausible scores with high uncertainty.
        """
        from rdkit import Chem
        from rdkit.Chem import AllChem, DataStructs

        results = []
        for smi in smiles_list:
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                results.append((5.0, 1.5))
                continue
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
            # Heuristic: use bit density + MW proxy for rough score
            bit_density = fp.GetNumOnBits() / 2048.0
            from rdkit.Chem import Descriptors
            mw = Descriptors.MolWt(mol)
            score = 4.0 + 4.0 * bit_density + (500 - mw) / 1000.0
            score = float(np.clip(score + np.random.normal(0, 0.3), 3.0, 11.0))
            results.append((score, 1.2))
        return results


# ── DeepChem AttentiveFP scorer ───────────────────────────────────────────────

class DeepChemScorer:
    """Wraps a DeepChem AttentiveFPModel for binding affinity prediction."""

    def __init__(self, model_dir: Optional[Path] = None) -> None:
        self._model: Optional["AttentiveFPModel"] = None
        self._featurizer = None
        self._ready = False
        if _deepchem_available:
            self._init_model(model_dir)

    def _init_model(self, model_dir: Optional[Path]) -> None:
        try:
            self._featurizer = dc.feat.MolGraphConvFeaturizer(use_edges=True)
            model_dir_str = str(model_dir) if model_dir else None
            self._model = AttentiveFPModel(
                n_tasks=1,
                mode="regression",
                model_dir=model_dir_str,
                num_layers=3,
                num_timesteps=3,
                graph_feat_size=200,
                dropout=0.2,
            )
            if model_dir and Path(model_dir).exists():
                checkpoint_files = list(Path(model_dir).glob("*.index"))
                if checkpoint_files:
                    self._model.restore()
                    logger.info("DeepChem AttentiveFP model restored from %s", model_dir)
            self._ready = True
        except Exception as exc:
            logger.error("DeepChem model init failed: %s", exc)

    @property
    def ready(self) -> bool:
        return self._ready and _deepchem_available

    def predict(self, smiles_list: list[str]) -> list[float]:
        """Returns predicted pIC50 per SMILES. Falls back to heuristic if not ready."""
        if not self.ready:
            return self._heuristic_fallback(smiles_list)

        try:
            dataset = dc.data.NumpyDataset(
                X=self._featurizer.featurize(smiles_list),
                y=None,
            )
            preds = self._model.predict(dataset)
            return [float(p[0]) for p in preds]
        except Exception as exc:
            logger.error("DeepChem prediction error: %s", exc)
            return self._heuristic_fallback(smiles_list)

    def _heuristic_fallback(self, smiles_list: list[str]) -> list[float]:
        from rdkit import Chem
        from rdkit.Chem import AllChem, Descriptors

        results = []
        for smi in smiles_list:
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                results.append(5.0)
                continue
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, 3, nBits=2048)
            density = fp.GetNumOnBits() / 2048.0
            mw = Descriptors.MolWt(mol)
            score = 3.5 + 3.5 * density + (500 - mw) / 1200.0
            score = float(np.clip(score + np.random.normal(0, 0.25), 3.0, 10.5))
            results.append(score)
        return results


# ── Ensemble scorer ───────────────────────────────────────────────────────────

class EnsembleScorer:
    """
    Combines Chemprop + DeepChem scores into a single ensemble score.
    Weights: 0.6 Chemprop (uncertainty-adjusted) + 0.4 DeepChem.
    """

    def __init__(
        self,
        chemprop_checkpoint: Optional[Path] = None,
        deepchem_model_dir: Optional[Path] = None,
    ) -> None:
        self.chemprop = ChempropScorer(chemprop_checkpoint)
        self.deepchem = DeepChemScorer(deepchem_model_dir)
        logger.info(
            "EnsembleScorer ready | Chemprop=%s | DeepChem=%s",
            self.chemprop.ready,
            self.deepchem.ready,
        )

    def score(
        self,
        smiles_list: list[str],
        pocket_features: Optional[list[float]] = None,
    ) -> list[dict]:
        """
        Returns list of dicts per molecule:
          {chemprop_pic50, chemprop_uncertainty, deepchem_pic50, ensemble_score}
        """
        cp_results = self.chemprop.predict(smiles_list, pocket_features)
        dc_results = self.deepchem.predict(smiles_list)

        output = []
        for (cp_val, cp_unc), dc_val in zip(cp_results, dc_results):
            # Down-weight Chemprop if uncertainty is very high
            cp_weight = 0.6 * max(0.0, 1.0 - cp_unc / 3.0)
            dc_weight = 0.4
            total_weight = cp_weight + dc_weight
            ensemble = (cp_weight * cp_val + dc_weight * dc_val) / total_weight
            output.append(
                {
                    "chemprop_pic50": round(cp_val, 4),
                    "chemprop_uncertainty": round(cp_unc, 4),
                    "deepchem_pic50": round(dc_val, 4),
                    "ensemble_score": round(ensemble, 4),
                }
            )
        return output


# ── Module-level singleton (loaded once at startup) ──────────────────────────
_scorer: Optional[EnsembleScorer] = None


def get_scorer(
    chemprop_checkpoint: Optional[Path] = None,
    deepchem_model_dir: Optional[Path] = None,
) -> EnsembleScorer:
    global _scorer
    if _scorer is None:
        _scorer = EnsembleScorer(chemprop_checkpoint, deepchem_model_dir)
    return _scorer
