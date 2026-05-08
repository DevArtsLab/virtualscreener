import { CheckCircle, XCircle, AlertTriangle, Atom } from "lucide-react";
import { cn, fmt, scoreColor, dockingColor } from "../lib/utils";
import type { MoleculeResult } from "../api/client";
import { DruglikenessRadar } from "./DruglikenessRadar";

interface MolCardProps {
  mol: MoleculeResult;
  onSelectPose?: () => void;
}

export function MolCard({ mol, onSelectPose }: MolCardProps) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-100 truncate">
            #{mol.rank} {mol.name}
          </h3>
          <p className="text-[11px] font-mono text-slate-500 truncate mt-0.5">
            {mol.smiles.length > 60 ? mol.smiles.slice(0, 60) + "…" : mol.smiles}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          {mol.lipinski?.passes_ro5 ? (
            <span className="flex items-center gap-1 text-emerald-400 text-xs">
              <CheckCircle size={12} /> Ro5 pass
            </span>
          ) : (
            <span className="flex items-center gap-1 text-red-400 text-xs">
              <XCircle size={12} /> Ro5 fail
            </span>
          )}
          {mol.lipinski && !mol.lipinski.passes_pains && (
            <span className="flex items-center gap-1 text-amber-400 text-xs">
              <AlertTriangle size={12} /> PAINS alert
            </span>
          )}
        </div>
      </div>

      {/* 2D Structure */}
      <div className="flex gap-4 flex-wrap">
        {mol.svg_2d ? (
          <div
            className="rounded-lg bg-white p-1 flex-shrink-0"
            style={{ width: 180, height: 120 }}
            dangerouslySetInnerHTML={{ __html: mol.svg_2d }}
          />
        ) : (
          <div className="flex items-center justify-center rounded-lg bg-slate-700 flex-shrink-0"
               style={{ width: 180, height: 120 }}>
            <Atom className="text-slate-500" size={32} />
          </div>
        )}

        {/* Scores */}
        <div className="flex flex-col gap-2 flex-1 min-w-0">
          <ScoreRow
            label="Ensemble Score"
            value={fmt(mol.ensemble_score, 3)}
            className={scoreColor(mol.ensemble_score)}
          />
          <ScoreRow
            label="Chemprop pIC50"
            value={
              mol.predicted_pic50 != null
                ? `${fmt(mol.predicted_pic50, 3)} ± ${fmt(mol.pic50_uncertainty, 3)}`
                : "—"
            }
            className={scoreColor(mol.predicted_pic50)}
          />
          <ScoreRow
            label="DeepChem pIC50"
            value={fmt(mol.deepchem_score, 3)}
            className={scoreColor(mol.deepchem_score)}
          />
          <ScoreRow
            label="Docking Score"
            value={mol.docking_score != null ? `${fmt(mol.docking_score, 2)} kcal/mol` : "—"}
            className={dockingColor(mol.docking_score)}
          />
        </div>
      </div>

      {/* Lipinski properties grid */}
      {mol.lipinski && (
        <div className="grid grid-cols-3 gap-2 text-xs">
          {[
            { label: "MW", val: `${mol.lipinski.mw.toFixed(1)} Da` },
            { label: "LogP", val: mol.lipinski.logp.toFixed(2) },
            { label: "TPSA", val: `${mol.lipinski.tpsa.toFixed(1)} Å²` },
            { label: "HBD", val: String(mol.lipinski.hbd) },
            { label: "HBA", val: String(mol.lipinski.hba) },
            { label: "RotBonds", val: String(mol.lipinski.rotatable_bonds) },
          ].map((p) => (
            <div key={p.label} className="rounded bg-slate-700/50 px-2 py-1">
              <p className="text-slate-500">{p.label}</p>
              <p className="font-mono font-semibold text-slate-200">{p.val}</p>
            </div>
          ))}
        </div>
      )}

      {/* Radar chart */}
      {mol.lipinski && <DruglikenessRadar lipinski={mol.lipinski} />}

      {/* View 3D pose button */}
      {mol.has_pose && onSelectPose && (
        <button
          onClick={onSelectPose}
          className="w-full py-2 rounded-lg bg-blue-600/20 border border-blue-600/50 text-blue-300 text-xs font-semibold hover:bg-blue-600/30 transition-colors"
        >
          View 3D Docking Pose
        </button>
      )}
    </div>
  );
}

function ScoreRow({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-xs text-slate-500">{label}</span>
      <span className={cn("text-xs font-mono font-bold", className)}>
        {value}
      </span>
    </div>
  );
}
