import { CheckCircle, Circle, Loader2, AlertCircle } from "lucide-react";
import { cn } from "../lib/utils";
import type { JobResponse, JobStatus } from "../api/client";

const STAGES: { key: JobStatus | "queued"; label: string; sub: string }[] = [
  { key: "tier1", label: "Tier 1", sub: "Lipinski + PAINS filter (RDKit)" },
  { key: "tier2", label: "Tier 2", sub: "ML scoring — Chemprop + DeepChem" },
  { key: "tier3", label: "Tier 3", sub: "AutoDock Vina docking (top-K)" },
  { key: "done", label: "Complete", sub: "Results ready" },
];

const STAGE_ORDER: JobStatus[] = ["queued", "tier1", "tier2", "tier3", "done"];

function stageIndex(status: JobStatus): number {
  return STAGE_ORDER.indexOf(status);
}

interface StageIconProps {
  state: "done" | "active" | "pending" | "error";
}

function StageIcon({ state }: StageIconProps) {
  if (state === "done") return <CheckCircle size={20} className="text-emerald-400" />;
  if (state === "active") return <Loader2 size={20} className="animate-spin text-blue-400" />;
  if (state === "error") return <AlertCircle size={20} className="text-red-400" />;
  return <Circle size={20} className="text-slate-600" />;
}

interface ProgressTrackerProps {
  job: JobResponse;
}

export function ProgressTracker({ job }: ProgressTrackerProps) {
  const currentIdx = stageIndex(job.status);

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-6 space-y-5">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-slate-400">
          <span>{job.current_stage}</span>
          <span>{job.progress.toFixed(0)}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-slate-700">
          <div
            className={cn(
              "h-2 rounded-full transition-all duration-500",
              job.status === "error"
                ? "bg-red-500"
                : job.status === "done"
                ? "bg-emerald-500"
                : "bg-blue-500"
            )}
            style={{ width: `${job.progress}%` }}
          />
        </div>
        {job.molecules_total > 0 && (
          <p className="text-xs text-slate-500">
            {job.molecules_processed.toLocaleString()} /{" "}
            {job.molecules_total.toLocaleString()} molecules processed
          </p>
        )}
      </div>

      {/* Stage steps */}
      <div className="flex items-start gap-0">
        {STAGES.map((stage, i) => {
          const idx = STAGE_ORDER.indexOf(stage.key as JobStatus);
          const isDone = currentIdx > idx || job.status === "done";
          const isActive =
            currentIdx === idx && job.status !== "done" && job.status !== "error";
          const isError = job.status === "error" && currentIdx === idx;
          const state = isError
            ? "error"
            : isDone
            ? "done"
            : isActive
            ? "active"
            : "pending";

          return (
            <div key={stage.key} className="flex flex-1 flex-col items-center">
              <div className="flex w-full items-center">
                {i > 0 && (
                  <div
                    className={cn(
                      "h-0.5 flex-1",
                      isDone ? "bg-emerald-500" : "bg-slate-700"
                    )}
                  />
                )}
                <StageIcon state={state} />
                {i < STAGES.length - 1 && (
                  <div
                    className={cn(
                      "h-0.5 flex-1",
                      isDone && !isActive ? "bg-emerald-500" : "bg-slate-700"
                    )}
                  />
                )}
              </div>
              <div className="mt-2 text-center px-1">
                <p
                  className={cn(
                    "text-xs font-semibold",
                    isActive
                      ? "text-blue-300"
                      : isDone
                      ? "text-emerald-300"
                      : "text-slate-500"
                  )}
                >
                  {stage.label}
                </p>
                <p className="text-[10px] text-slate-600 leading-tight mt-0.5 hidden sm:block">
                  {stage.sub}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {job.error_message && (
        <div className="rounded-lg bg-red-950/40 border border-red-800 p-3">
          <p className="text-xs text-red-300 font-mono">{job.error_message}</p>
        </div>
      )}
    </div>
  );
}
