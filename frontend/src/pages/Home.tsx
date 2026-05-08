import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FlaskConical, Dna, Brain, Atom } from "lucide-react";
import { api } from "../api/client";
import { UploadForm } from "../components/UploadZone";

export function HomePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(protein: File, library: File, topK: number) {
    setLoading(true);
    setError(null);
    try {
      const job = await api.submitScreening(protein, library, topK);
      navigate(`/results/${job.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Hero */}
      <div className="relative overflow-hidden border-b border-slate-800">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-purple-500/5 rounded-full blur-3xl" />
        </div>
        <div className="relative max-w-5xl mx-auto px-6 py-16 text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-950/60 border border-blue-800/60 text-blue-300 text-xs font-medium mb-2">
            <FlaskConical size={12} /> AI-Powered Drug Discovery
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
            Virtual Screening
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">
              Binding Affinity Prediction
            </span>
          </h1>
          <p className="text-slate-400 max-w-2xl mx-auto text-base leading-relaxed">
            Upload a protein target and compound library. Our 3-tier ML + physics pipeline
            predicts binding affinities using{" "}
            <span className="text-blue-300">Chemprop D-MPNN</span>,{" "}
            <span className="text-purple-300">DeepChem AttentiveFP</span>, and{" "}
            <span className="text-teal-300">AutoDock Vina</span>.
          </p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-12 space-y-10">
        {/* Pipeline overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            {
              icon: <Atom size={20} className="text-blue-400" />,
              tier: "Tier 1",
              name: "Molecular Filter",
              tools: "RDKit",
              desc: "Lipinski Ro5 + PAINS filter. Removes drug-unlikeness and pan-assay interference.",
              color: "border-blue-800/50 bg-blue-950/20",
            },
            {
              icon: <Brain size={20} className="text-purple-400" />,
              tier: "Tier 2",
              name: "ML Ensemble",
              tools: "Chemprop + DeepChem",
              desc: "Directed MPNN + AttentiveFP ensemble. Predicts pIC50 with MC-Dropout uncertainty.",
              color: "border-purple-800/50 bg-purple-950/20",
            },
            {
              icon: <Dna size={20} className="text-teal-400" />,
              tier: "Tier 3",
              name: "Docking",
              tools: "AutoDock Vina",
              desc: "Physics-based docking of top-K candidates. Returns 3D poses for visualization.",
              color: "border-teal-800/50 bg-teal-950/20",
            },
          ].map((t) => (
            <div
              key={t.tier}
              className={`rounded-xl border p-5 space-y-2 ${t.color}`}
            >
              <div className="flex items-center gap-2">
                {t.icon}
                <div>
                  <span className="text-xs font-mono text-slate-500">{t.tier}</span>
                  <h3 className="font-semibold text-sm text-slate-200 leading-none">
                    {t.name}
                  </h3>
                </div>
              </div>
              <p className="text-xs font-mono text-slate-500">{t.tools}</p>
              <p className="text-xs text-slate-400 leading-relaxed">{t.desc}</p>
            </div>
          ))}
        </div>

        {/* Upload form */}
        <div className="rounded-2xl border border-slate-700 bg-slate-900/60 p-8 space-y-2">
          <h2 className="text-lg font-semibold text-slate-100">Start a Screening Run</h2>
          <p className="text-sm text-slate-500 mb-4">
            Supports PDB proteins · SMILES (.smi / .txt / .csv) or SDF compound libraries
          </p>
          <UploadForm onSubmit={handleSubmit} loading={loading} />
          {error && (
            <div className="mt-3 rounded-lg bg-red-950/40 border border-red-800 p-3">
              <p className="text-xs text-red-300">{error}</p>
            </div>
          )}
        </div>

        {/* Example inputs note */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-2">Quick start</h3>
          <p className="text-xs text-slate-500 leading-relaxed">
            Download example files from the{" "}
            <span className="text-blue-400">RCSB PDB</span> (any <code className="text-slate-300">.pdb</code> file)
            and a SMILES library from{" "}
            <span className="text-blue-400">ChEMBL</span> or{" "}
            <span className="text-blue-400">ZINC</span>.
            The SMILES file should have one molecule per line: <code className="text-slate-300">SMILES name</code>.
          </p>
        </div>
      </div>
    </div>
  );
}
