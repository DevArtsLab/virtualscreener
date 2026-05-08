import { useEffect, useRef, useState } from "react";
import { X, Eye, EyeOff, RotateCcw } from "lucide-react";
import { cn } from "../lib/utils";

declare global {
  interface Window {
    NGL: typeof import("ngl");
  }
}

interface MolViewerProps {
  jobId: string;
  molId: string;
  molName: string;
  onClose: () => void;
}

type RepType = "cartoon" | "surface" | "ball+stick";

export function MolViewer({ jobId, molId, molName, onClose }: MolViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<import("ngl").Stage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [protRep, setProtRep] = useState<RepType>("cartoon");
  const [showLigand, setShowLigand] = useState(true);

  useEffect(() => {
    if (!containerRef.current) return;

    let stage: import("ngl").Stage;

    async function init() {
      try {
        const { Stage } = await import("ngl");
        stage = new Stage(containerRef.current!, {
          backgroundColor: "#0f172a",
          quality: "medium",
        });
        stageRef.current = stage;

        // Load pose PDB
        const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";
        const poseUrl = `${BASE}/molecules/${jobId}/${molId}/pose`;
        const res = await fetch(poseUrl);
        if (!res.ok) throw new Error("Pose not available");
        const pdbText = await res.text();

        const blob = new Blob([pdbText], { type: "text/plain" });
        const comp = await stage.loadFile(blob, { ext: "pdb", name: "ligand" });
        if (!comp) throw new Error("Failed to load pose");

        comp.addRepresentation("ball+stick", {
          colorScheme: "element",
          radius: 0.2,
        });
        comp.autoView();
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        setLoading(false);
      }
    }

    init();

    const handleResize = () => stageRef.current?.handleResize();
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      stage?.dispose();
    };
  }, [jobId, molId]);

  function handleReset() {
    stageRef.current?.autoView();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-3xl rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-700">
          <div>
            <p className="font-semibold text-slate-100 text-sm">{molName}</p>
            <p className="text-xs text-slate-500">Docking pose — NGL Viewer</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleReset}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-colors"
              title="Reset view"
            >
              <RotateCcw size={15} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-700 transition-colors"
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Viewer canvas */}
        <div className="relative" style={{ height: 460 }}>
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-900 z-10">
              <div className="flex flex-col items-center gap-3">
                <div className="h-8 w-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
                <p className="text-sm text-slate-400">Loading 3D structure…</p>
              </div>
            </div>
          )}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-900 z-10">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
          <div ref={containerRef} className="w-full h-full" />
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3 px-5 py-3 border-t border-slate-700 bg-slate-800/50">
          <span className="text-xs text-slate-500 mr-1">Protein:</span>
          {(["cartoon", "surface", "ball+stick"] as RepType[]).map((r) => (
            <button
              key={r}
              onClick={() => setProtRep(r)}
              className={cn(
                "px-2 py-1 rounded text-xs transition-colors",
                protRep === r
                  ? "bg-blue-600 text-white"
                  : "bg-slate-700 text-slate-400 hover:bg-slate-600"
              )}
            >
              {r}
            </button>
          ))}
          <div className="ml-auto">
            <button
              onClick={() => setShowLigand((v) => !v)}
              className="flex items-center gap-1.5 px-2 py-1 rounded text-xs bg-slate-700 text-slate-400 hover:bg-slate-600 transition-colors"
            >
              {showLigand ? <Eye size={12} /> : <EyeOff size={12} />}
              Ligand
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
