import React, { useCallback, useRef, useState } from "react";
import { Upload, FileText, FlaskConical, X } from "lucide-react";
import { cn } from "../lib/utils";

interface UploadZoneProps {
  label: string;
  accept: string;
  hint: string;
  icon: React.ReactNode;
  file: File | null;
  onFile: (f: File | null) => void;
}

function SingleDropZone({ label, accept, hint, icon, file, onFile }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) onFile(f);
    },
    [onFile]
  );

  return (
    <div
      className={cn(
        "relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-8 transition-all cursor-pointer select-none",
        dragging
          ? "border-blue-400 bg-blue-950/30"
          : file
          ? "border-emerald-500 bg-emerald-950/20"
          : "border-slate-600 bg-slate-800/40 hover:border-slate-400"
      )}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => onFile(e.target.files?.[0] ?? null)}
      />

      {file ? (
        <>
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
            {icon}
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-emerald-300">{file.name}</p>
            <p className="text-xs text-slate-400 mt-1">
              {(file.size / 1024).toFixed(1)} KB
            </p>
          </div>
          <button
            className="absolute top-3 right-3 text-slate-500 hover:text-red-400 transition-colors"
            onClick={(e) => { e.stopPropagation(); onFile(null); }}
          >
            <X size={16} />
          </button>
        </>
      ) : (
        <>
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-700 text-slate-400">
            {icon}
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-slate-300">{label}</p>
            <p className="text-xs text-slate-500 mt-1">{hint}</p>
          </div>
          <Upload size={14} className="text-slate-600" />
        </>
      )}
    </div>
  );
}

interface UploadFormProps {
  onSubmit: (protein: File, library: File, topK: number) => void;
  loading: boolean;
}

export function UploadForm({ onSubmit, loading }: UploadFormProps) {
  const [protein, setProtein] = useState<File | null>(null);
  const [library, setLibrary] = useState<File | null>(null);
  const [topK, setTopK] = useState(10);

  const canSubmit = protein && library && !loading;

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SingleDropZone
          label="Protein Target"
          accept=".pdb"
          hint="Drop a PDB file here"
          icon={<FlaskConical size={24} />}
          file={protein}
          onFile={setProtein}
        />
        <SingleDropZone
          label="Compound Library"
          accept=".smi,.txt,.csv,.sdf"
          hint="SMILES (.smi / .txt / .csv) or SDF"
          icon={<FileText size={24} />}
          file={library}
          onFile={setLibrary}
        />
      </div>

      <div className="flex items-center gap-4">
        <label className="text-sm text-slate-400 whitespace-nowrap">
          Dock top
        </label>
        <input
          type="range"
          min={1}
          max={50}
          value={topK}
          onChange={(e) => setTopK(Number(e.target.value))}
          className="flex-1 accent-blue-500"
        />
        <span className="w-8 text-center text-sm font-mono font-bold text-blue-400">
          {topK}
        </span>
        <label className="text-sm text-slate-400">molecules (Vina)</label>
      </div>

      <button
        disabled={!canSubmit}
        onClick={() => protein && library && onSubmit(protein, library, topK)}
        className={cn(
          "w-full py-3 rounded-xl font-semibold text-sm transition-all",
          canSubmit
            ? "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/40"
            : "bg-slate-700 text-slate-500 cursor-not-allowed"
        )}
      >
        {loading ? "Submitting…" : "Run Virtual Screening"}
      </button>
    </div>
  );
}
